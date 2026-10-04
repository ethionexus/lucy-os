"""Auto-healing system daemon for Lucy OS.

v0.3.0 enhancement: beyond resource thresholds, the daemon now watches the
systemd journal for driver/service failures and boot loops, creates instant
Btrfs snapshots before risky operations, and arms sub-second rollbacks to
prevent black screens.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Optional

from .snapshot import SnapshotManager, BootGuard

# Import Rust module
try:
    import lucy_core
except ImportError:
    lucy_core = None
    logging.warning("lucy_core Rust module not available, running in degraded mode")

# Journal patterns that indicate a fault worth healing.
JOURNAL_FAULT_PATTERNS = [
    re.compile(r"\bsegfault\b", re.I),
    re.compile(r"\bSIGSEGV\b", re.I),
    re.compile(r"\bSIGBUS\b", re.I),
    re.compile(r"failed to (start|load)", re.I),
    re.compile(r"GPU hang", re.I),
    re.compile(r"drm.*error", re.I),
    re.compile(r"kernel panic", re.I),
    re.compile(r"entered failed state", re.I),
]


class AutoHealDaemon:
    """Auto-healing daemon for system resource management and rollback."""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.monitor = None
        self.running = False
        self.logger = logging.getLogger("lucy.autoheal")

        # v0.3.0 rollback engine
        self.snapshots = SnapshotManager()
        self.boot_guard = BootGuard(
            fail_threshold=self.config.get("rollback_fail_threshold", 3)
        )
        self._last_journal_cursor: Optional[str] = None
        self._snapshot_taken = False

        if lucy_core:
            self.monitor = lucy_core.SystemMonitor()
            lucy_core.init_logging(self.config.get("log_dir", "/var/log/lucy"))

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from file.

        Supports both JSON and the INI-style ``/etc/lucy/agent.conf``
        (``key = value`` pairs, ``#`` comments, ``[section]`` headers).
        """
        defaults = {
            "log_dir": "/var/log/lucy",
            "memory_threshold": 85,
            "disk_threshold": 90,
            "clear_cache": True,
            "rotate_logs": True,
            "max_log_size": "100M",
            "check_interval": 300,
            "rollback_enabled": True,
            "snapshot_on_boot": True,
            "journal_scan_interval": 60,
            "rollback_fail_threshold": 3,
        }
        if not (config_path and Path(config_path).exists()):
            return defaults
        try:
            text = Path(config_path).read_text()
        except OSError:
            return defaults

        # Try JSON first.
        text_stripped = text.strip()
        if text_stripped.startswith("{"):
            try:
                data = json.loads(text_stripped)
                merged = dict(defaults)
                merged.update(data)
                return merged
            except json.JSONDecodeError:
                pass

        # INI-style parsing.
        data: dict = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", ";", "[")):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            low = value.lower()
            if low in ("true", "yes", "on"):
                data[key] = True
            elif low in ("false", "no", "off"):
                data[key] = False
            else:
                try:
                    data[key] = int(value)
                except ValueError:
                    data[key] = value
        merged = dict(defaults)
        merged.update(data)
        return merged

    # ------------------------------------------------------------------
    # Resource checks (v0.2.0)
    # ------------------------------------------------------------------
    async def check_memory(self) -> bool:
        """Check if memory usage exceeds threshold"""
        if not self.monitor:
            return False

        threshold = self.config.get("memory_threshold", 85)
        exceeds = self.monitor.check_memory_threshold(threshold)

        if exceeds:
            self.logger.warning(f"Memory usage exceeds {threshold}% threshold")
            return True
        return False

    async def check_disk(self) -> bool:
        """Check if disk usage exceeds threshold"""
        if not self.monitor:
            return False

        threshold = self.config.get("disk_threshold", 90)
        exceeds = self.monitor.check_disk_threshold(threshold)

        if exceeds:
            self.logger.warning(f"Disk usage exceeds {threshold}% threshold")
            return True
        return False

    async def perform_healing(self):
        """Perform auto-healing actions"""
        actions_taken = []

        if self.config.get("clear_cache", True):
            try:
                if self.monitor:
                    result = self.monitor.clear_system_cache()
                    self.logger.info(f"Cache cleared: {result}")
                    actions_taken.append("cache_cleared")
            except Exception as e:
                self.logger.error(f"Failed to clear cache: {e}")

        if self.config.get("rotate_logs", True):
            try:
                if self.monitor:
                    log_dir = self.config.get("log_dir", "/var/log/lucy")
                    max_size = self._parse_size(self.config.get("max_log_size", "100M"))
                    result = self.monitor.rotate_logs(log_dir, max_size)
                    self.logger.info(f"Logs rotated: {result}")
                    actions_taken.append("logs_rotated")
            except Exception as e:
                self.logger.error(f"Failed to rotate logs: {e}")

        return actions_taken

    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '100M' to bytes"""
        size_str = size_str.upper()
        multipliers = {
            "B": 1,
            "K": 1024,
            "M": 1024 * 1024,
            "G": 1024 * 1024 * 1024,
        }

        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                value = int(size_str[:-1])
                return value * multiplier

        return int(size_str)

    # ------------------------------------------------------------------
    # Journal + boot failure monitoring (v0.3.0)
    # ------------------------------------------------------------------
    def _journalctl(self, args: list[str], timeout: int = 20) -> Optional[str]:
        """Run journalctl, returning stdout or None when unavailable."""
        import shutil
        import subprocess
        if not shutil.which("journalctl"):
            return None
        try:
            p = subprocess.run(
                ["journalctl"] + args,
                capture_output=True, text=True, timeout=timeout,
            )
            if p.returncode == 0:
                return p.stdout
        except (OSError, subprocess.TimeoutExpired):
            pass
        return None

    def scan_journal_for_faults(self, since: str = "-5min") -> list[str]:
        """Scan recent journal entries for fault signatures."""
        out = self._journalctl([
            "--no-pager", "-p", "err", "--since", since, "-o", "cat",
        ])
        if not out:
            return []
        faults = []
        for line in out.splitlines():
            for pat in JOURNAL_FAULT_PATTERNS:
                if pat.search(line):
                    faults.append(line.strip())
                    break
        return faults

    def handle_faults(self, faults: list[str]) -> list[str]:
        """React to detected journal faults (snapshot + arm rollback)."""
        actions = []
        if not faults:
            return actions

        if self.config.get("rollback_enabled", True):
            # Snapshot the *current* state before any further change so the
            # user has a recovery point, then arm a rollback if the boot
            # guard says we are looping.
            snap = self.snapshots.create(f"lucy-fault-{len(faults)}f")
            if snap:
                actions.append(f"snapshot:{snap.name}")

            if self.boot_guard.should_rollback():
                ok, msg = self.snapshots.rollback()
                actions.append(f"rollback:{'ok' if ok else 'fail'}:{msg}")
                self.logger.warning("Boot failure threshold reached — %s", msg)
        return actions

    def record_boot(self) -> None:
        """Record a boot and snapshot early for a safe recovery point."""
        state = self.boot_guard.record_boot()
        self.logger.info(
            "boot #%s recorded (consecutive failures: %s)",
            state.get("boot_count"), state.get("consecutive_failures"),
        )
        if self.config.get("snapshot_on_boot", True) and not self._snapshot_taken:
            snap = self.snapshots.create("lucy-boot-baseline")
            if snap:
                self.logger.info("baseline snapshot created: %s", snap.name)
            self._snapshot_taken = True

    def mark_healthy(self) -> None:
        """Mark the current boot healthy once core services are up."""
        self.boot_guard.mark_healthy()
        self.logger.info("boot marked healthy")

    def get_boot_status(self) -> dict:
        status = self.boot_guard.get_status()
        status["snapshot_backend"] = self.snapshots.backend
        status["snapshot_count"] = len(self.snapshots.list())
        return status

    # ------------------------------------------------------------------
    # Loops
    # ------------------------------------------------------------------
    async def monitor_loop(self):
        """Resource monitoring loop (memory/disk thresholds)."""
        check_interval = self.config.get("check_interval", 300)

        while self.running:
            try:
                self.logger.info("Running auto-healing check")
                memory_exceeded = await self.check_memory()
                disk_exceeded = await self.check_disk()

                if memory_exceeded or disk_exceeded:
                    self.logger.info("Thresholds exceeded, performing healing actions")
                    actions = await self.perform_healing()
                    self.logger.info(f"Auto-healing actions taken: {actions}")
            except Exception as e:
                self.logger.error(f"Auto-healing check failed: {e}")

            await asyncio.sleep(check_interval)

    async def journal_loop(self):
        """Journal fault watchdog loop."""
        interval = self.config.get("journal_scan_interval", 60)
        while self.running:
            try:
                faults = self.scan_journal_for_faults()
                actions = self.handle_faults(faults)
                if actions:
                    self.logger.info("journal watchdog actions: %s", actions)
            except Exception as e:
                self.logger.error("journal watchdog failed: %s", e)
            await asyncio.sleep(interval)

    async def start(self):
        """Start the auto-healing daemon"""
        self.running = True
        self.record_boot()
        self.logger.info("Auto-healing daemon started")

    async def stop(self):
        """Stop the auto-healing daemon"""
        self.running = False
        self.logger.info("Auto-healing daemon stopped")

    async def run(self):
        """Run the auto-healing daemon (resource + journal loops)"""
        await self.start()
        # Mark healthy after a short grace period, once services have settled.
        async def _health_marker():
            await asyncio.sleep(30)
            if self.running:
                self.mark_healthy()
        await asyncio.gather(
            self.monitor_loop(),
            self.journal_loop(),
            _health_marker(),
        )


async def main():
    """Main entry point"""
    daemon = AutoHealDaemon(config_path="/etc/lucy/agent.conf")
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
