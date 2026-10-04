"""Btrfs snapshot and instant-rollback engine for Lucy OS.

Provides sub-second, copy-on-write snapshots of the root subvolume and a
guarded rollback that prevents black-screen boot loops. Falls back to
``timeshift`` when available, and degrades to a no-op when neither the
filesystem nor the tools support snapshots (so the daemon never crashes).

All privileged operations require root; the ``lucy-autoheal`` system service
runs as root, so it can invoke these directly.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SNAPSHOT_DIR = Path("/.snapshots")
BOOT_STATE_PATH = Path("/var/lib/lucy/boot_status.json")

# Number of consecutive failed boots before an automatic rollback fires.
DEFAULT_FAIL_THRESHOLD = 3
# Boots younger than this (seconds) are treated as "still in progress".
BOOT_PROBE_SECONDS = 90


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a command, returning (returncode, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


# ---------------------------------------------------------------------------
# Snapshot manager
# ---------------------------------------------------------------------------
@dataclass
class Snapshot:
    name: str
    path: str
    created: float
    read_only: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "created": self.created,
            "read_only": self.read_only,
        }


class SnapshotManager:
    """Manages Btrfs snapshots of the root subvolume."""

    def __init__(self, root: str = "/", snapshot_dir: Path = SNAPSHOT_DIR):
        self.root = root
        self.snapshot_dir = snapshot_dir
        self._backend: Optional[str] = None  # "btrfs" | "timeshift" | None

    # -- capability detection ---------------------------------------------
    @property
    def backend(self) -> Optional[str]:
        if self._backend is None:
            self._backend = self._detect_backend()
        return self._backend

    def _detect_backend(self) -> Optional[str]:
        if shutil.which("btrfs"):
            rc, _out, _err = _run(["btrfs", "filesystem", "usage", self.root])
            if rc == 0:
                return "btrfs"
        if shutil.which("timeshift"):
            return "timeshift"
        return None

    def available(self) -> bool:
        return self.backend is not None

    # -- snapshot creation -------------------------------------------------
    def create(self, name: Optional[str] = None, read_only: bool = True) -> Optional[Snapshot]:
        """Create a snapshot. Returns the Snapshot or None on failure.

        The Btrfs operation is O(1) (copy-on-write) so it completes in
        well under a second.
        """
        if not name:
            name = f"lucy-{time.strftime('%Y%m%d-%H%M%S')}"
        backend = self.backend
        if backend == "btrfs":
            return self._create_btrfs(name, read_only)
        if backend == "timeshift":
            return self._create_timeshift(name)
        return None

    def _create_btrfs(self, name: str, read_only: bool) -> Optional[Snapshot]:
        try:
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        dest = self.snapshot_dir / name
        if dest.exists():
            return Snapshot(name=name, path=str(dest), created=time.time(), read_only=read_only)
        flags = ["-r"] if read_only else []
        rc, _out, _err = _run(
            ["btrfs", "subvolume", "snapshot"] + flags + [self.root, str(dest)]
        )
        if rc != 0:
            return None
        return Snapshot(name=name, path=str(dest), created=time.time(), read_only=read_only)

    def _create_timeshift(self, name: str) -> Optional[Snapshot]:
        rc, out, _err = _run(
            ["timeshift", "--create", "--comments", name, "--scripted"],
            timeout=120,
        )
        if rc != 0:
            return None
        return Snapshot(name=name, path=out or "timeshift", created=time.time())

    # -- listing -----------------------------------------------------------
    def list(self) -> list[Snapshot]:
        if self.snapshot_dir.exists():
            snaps = []
            for p in sorted(self.snapshot_dir.iterdir()):
                if p.is_dir():
                    try:
                        snaps.append(Snapshot(
                            name=p.name,
                            path=str(p),
                            created=p.stat().st_mtime,
                        ))
                    except OSError:
                        continue
            return snaps
        if self.backend == "timeshift":
            rc, out, _err = _run(["timeshift", "--list", "--scripted"])
            if rc == 0:
                snaps = []
                for line in out.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 3:
                        snaps.append(Snapshot(
                            name=parts[-1], path=parts[-1], created=time.time()
                        ))
                return snaps
        return []

    # -- rollback ----------------------------------------------------------
    def rollback(self, name: Optional[str] = None) -> tuple[bool, str]:
        """Roll the root back to a snapshot.

        For Btrfs this schedules a swap of the root subvolume with the
        snapshot; the change takes effect on the next boot. Returns
        (success, message).
        """
        backend = self.backend
        if backend is None:
            return False, "no snapshot backend available"

        if backend == "timeshift":
            target = name or "latest"
            rc, _out, err = _run(
                ["timeshift", "--restore", "--snapshot", target,
                 "--target", "/", "--scripted", "--yes"],
                timeout=600,
            )
            return (rc == 0, err or "timeshift restore requested")

        # Btrfs: resolve the target snapshot.
        snaps = {s.name: s for s in self.list()}
        if not snaps:
            return False, "no snapshots available"
        if name is None:
            snap = max(snaps.values(), key=lambda s: s.created)
        else:
            snap = snaps.get(name)
            if snap is None:
                return False, f"snapshot not found: {name}"

        # Write a one-shot rollback request consumed by lucy-rollback.service
        # at the next boot (a live root cannot be swapped in place).
        try:
            req = Path("/var/lib/lucy/rollback.request")
            req.parent.mkdir(parents=True, exist_ok=True)
            req.write_text(json.dumps({
                "snapshot": snap.path,
                "requested": time.time(),
                "reason": "auto-heal",
            }))
        except OSError as e:
            return False, f"could not write rollback request: {e}"
        return True, f"rollback to {snap.name} armed"

    # -- status ------------------------------------------------------------
    def usage(self) -> dict:
        """Return basic filesystem/snapshot usage info."""
        info = {
            "available": self.available(),
            "backend": self.backend,
            "snapshot_count": len(self.list()),
        }
        if self.backend == "btrfs":
            rc, out, _err = _run(["btrfs", "filesystem", "usage", "-b", self.root])
            if rc == 0:
                info["usage"] = out
        return info


# ---------------------------------------------------------------------------
# Boot guard: detects boot loops and arms rollbacks
# ---------------------------------------------------------------------------
class BootGuard:
    """Tracks consecutive boot failures and decides when to roll back."""

    def __init__(
        self,
        state_path: Path = BOOT_STATE_PATH,
        fail_threshold: int = DEFAULT_FAIL_THRESHOLD,
    ):
        self.state_path = state_path
        self.fail_threshold = fail_threshold

    def _load(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text())
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "boot_count": 0,
            "consecutive_failures": 0,
            "last_good_boot": None,
            "last_boot_start": None,
            "healthy": False,
        }

    def _save(self, state: dict) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps(state, indent=2))
        except OSError:
            pass

    def record_boot(self) -> dict:
        """Record that a boot has started. Returns the updated state.

        If the previous boot never reached a healthy state, it counts as a
        failure.
        """
        state = self._load()
        if state.get("last_boot_start") and not state.get("healthy"):
            state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        state["boot_count"] = state.get("boot_count", 0) + 1
        state["last_boot_start"] = time.time()
        state["healthy"] = False
        self._save(state)
        return state

    def mark_healthy(self) -> None:
        """Mark the current boot as healthy (resets the failure counter)."""
        state = self._load()
        state["healthy"] = True
        state["consecutive_failures"] = 0
        state["last_good_boot"] = time.time()
        self._save(state)

    def get_status(self) -> dict:
        state = self._load()
        return {
            "boot_count": state.get("boot_count", 0),
            "consecutive_failures": state.get("consecutive_failures", 0),
            "healthy": state.get("healthy", False),
            "last_good_boot": state.get("last_good_boot"),
            "fail_threshold": self.fail_threshold,
            "rollback_recommended": state.get("consecutive_failures", 0) >= self.fail_threshold,
        }

    def should_rollback(self) -> bool:
        return self.get_status()["rollback_recommended"]


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------
_manager: Optional[SnapshotManager] = None
_guard: Optional[BootGuard] = None


def get_manager() -> SnapshotManager:
    global _manager
    if _manager is None:
        _manager = SnapshotManager()
    return _manager


def get_guard() -> BootGuard:
    global _guard
    if _guard is None:
        _guard = BootGuard()
    return _guard


def create_snapshot(name: Optional[str] = None) -> Optional[dict]:
    snap = get_manager().create(name)
    return snap.to_dict() if snap else None


def trigger_rollback(name: Optional[str] = None) -> dict:
    ok, msg = get_manager().rollback(name)
    return {"success": ok, "message": msg}


def get_boot_status() -> dict:
    return get_guard().get_status()
