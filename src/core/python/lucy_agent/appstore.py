"""Lucy OS App Manager — curated catalog + Flatpak/Flathub integration.

Phase 1 of v0.4.0: essential pre-installed apps and Flatpak support.

Design notes
------------
* Standard library only. The module must import cleanly on a build host with
  no Flatpak and no third-party packages installed, so tests can run anywhere.
* Every call that touches the system goes through an injectable ``runner``.
  The default shells out with :mod:`subprocess`; tests pass a fake runner and
  assert on the exact command lines without executing anything.
* The catalog is data, not code: ``/etc/lucy/apps.json`` on a live system,
  falling back to the copy in the repository, then to a small built-in default.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

# --- Constants -------------------------------------------------------------

FLATHUB_REMOTE_NAME = "flathub"
FLATHUB_REPO_URL = "https://dl.flathub.org/repo/flathub.flatpakrepo"

#: Where the catalog may live, in priority order.
CATALOG_SEARCH_PATHS: Tuple[str, ...] = (
    "/etc/lucy/apps.json",
    "/usr/share/lucy/apps.json",
)

#: Exit codes/messages returned by the helpers below.
RunnerResult = Tuple[int, str, str]
Runner = Callable[[Sequence[str]], RunnerResult]


class AppManagerError(RuntimeError):
    """Raised when an operation cannot proceed (e.g. Flatpak is missing)."""


# --- Runner ----------------------------------------------------------------


def default_runner(args: Sequence[str], timeout: int = 300) -> RunnerResult:
    """Execute a command and return ``(returncode, stdout, stderr)``.

    Never raises for a non-zero exit; callers inspect the code. A missing
    binary is reported as return code 127 rather than an exception so the
    calling code has one uniform shape to deal with.
    """
    try:
        proc = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except FileNotFoundError:
        return 127, "", f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s: {' '.join(args)}"
    except OSError as exc:  # pragma: no cover - defensive
        return 126, "", str(exc)


# --- Catalog ---------------------------------------------------------------


@dataclass(frozen=True)
class AppEntry:
    """A single application known to the Lucy app manager."""

    id: str
    name: str
    category: str
    description: str = ""
    kind: str = "flatpak"  # "flatpak" | "native"
    core: bool = False
    native_package: Optional[str] = None
    homepage: Optional[str] = None

    @property
    def is_flatpak(self) -> bool:
        return self.kind == "flatpak"

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "kind": self.kind,
            "core": self.core,
            "native_package": self.native_package,
            "homepage": self.homepage,
        }


@dataclass
class Catalog:
    """The parsed ``apps.json`` catalog."""

    version: int
    remote_name: str = FLATHUB_REMOTE_NAME
    remote_url: str = FLATHUB_REPO_URL
    apps: List[AppEntry] = field(default_factory=list)

    def core_apps(self) -> List[AppEntry]:
        return [a for a in self.apps if a.core]

    def categories(self) -> List[str]:
        seen: List[str] = []
        for a in self.apps:
            if a.category not in seen:
                seen.append(a.category)
        return seen

    def get(self, app_id: str) -> Optional[AppEntry]:
        for a in self.apps:
            if a.id == app_id:
                return a
        return None

    def find(self, query: str) -> List[AppEntry]:
        """Case-insensitive substring match over id, name and category."""
        q = (query or "").strip().lower()
        if not q:
            return list(self.apps)
        hits = []
        for a in self.apps:
            haystack = " ".join(
                filter(None, (a.id, a.name, a.category, a.description))
            ).lower()
            if q in haystack:
                hits.append(a)
        return hits

    def to_dict(self) -> Dict[str, object]:
        return {
            "version": self.version,
            "remote_name": self.remote_name,
            "remote_url": self.remote_url,
            "apps": [a.to_dict() for a in self.apps],
        }


#: Minimal fallback so the module is useful even without the JSON file.
DEFAULT_CATALOG: Dict[str, object] = {
    "version": 1,
    "remote_name": FLATHUB_REMOTE_NAME,
    "remote_url": FLATHUB_REPO_URL,
    "apps": [
        {
            "id": "org.mozilla.firefox",
            "name": "Firefox",
            "category": "browser",
            "description": "Fast, private web browser with hardware acceleration.",
            "kind": "flatpak",
            "core": True,
        },
        {
            "id": "com.github.taiko2k.tauonmb",
            "name": "Tauon Music Box",
            "category": "media",
            "description": "Sleek music player for local libraries.",
            "kind": "flatpak",
            "core": False,
        },
    ],
}


def _parse_app(raw: Dict[str, object]) -> AppEntry:
    app_id = str(raw.get("id", "")).strip()
    if not app_id:
        raise ValueError("app entry is missing 'id'")
    kind = str(raw.get("kind", "flatpak")).strip() or "flatpak"
    if kind not in ("flatpak", "native"):
        raise ValueError(f"app '{app_id}': unknown kind '{kind}'")
    native_package = raw.get("native_package")
    if kind == "native" and not native_package:
        # A native app is useless without the pacman package it maps to.
        raise ValueError(f"app '{app_id}': native apps need 'native_package'")
    return AppEntry(
        id=app_id,
        name=str(raw.get("name", app_id)).strip(),
        category=str(raw.get("category", "uncategorized")).strip(),
        description=str(raw.get("description", "")).strip(),
        kind=kind,
        core=bool(raw.get("core", False)),
        native_package=str(native_package).strip() if native_package else None,
        homepage=(str(raw["homepage"]).strip() if raw.get("homepage") else None),
    )


def parse_catalog(data: Dict[str, object]) -> Catalog:
    """Validate and convert a decoded ``apps.json`` mapping into a Catalog."""
    if not isinstance(data, dict):
        raise ValueError("catalog root must be a JSON object")
    raw_apps = data.get("apps", [])
    if not isinstance(raw_apps, list):
        raise ValueError("catalog 'apps' must be a list")

    apps: List[AppEntry] = []
    seen: set = set()
    for raw in raw_apps:
        if not isinstance(raw, dict):
            raise ValueError("each app entry must be a JSON object")
        entry = _parse_app(raw)
        if entry.id in seen:
            raise ValueError(f"duplicate app id: {entry.id}")
        seen.add(entry.id)
        apps.append(entry)

    return Catalog(
        version=int(data.get("version", 1)),
        remote_name=str(data.get("remote_name", FLATHUB_REMOTE_NAME)),
        remote_url=str(data.get("remote_url", FLATHUB_REPO_URL)),
        apps=apps,
    )


def _repo_catalog_candidates() -> Iterable[Path]:
    """Repo-relative copies of the catalog, for development and tests."""
    here = Path(__file__).resolve()
    # src/core/python/lucy_agent/appstore.py -> repo root is 4 parents up.
    for parent in here.parents:
        candidate = parent / "src" / "configs" / "airootfs" / "etc" / "lucy" / "apps.json"
        yield candidate


def find_catalog_path() -> Optional[Path]:
    """Return the first catalog file that exists, or None."""
    override = os.environ.get("LUCY_APPS_JSON")
    if override:
        p = Path(override)
        return p if p.is_file() else None
    for raw in CATALOG_SEARCH_PATHS:
        p = Path(raw)
        if p.is_file():
            return p
    for p in _repo_catalog_candidates():
        if p.is_file():
            return p
    return None


def load_catalog(path: Optional[os.PathLike] = None) -> Catalog:
    """Load the catalog, falling back to the built-in default.

    A malformed catalog raises :class:`ValueError` rather than being silently
    ignored, so a bad edit is caught by the verification script.
    """
    if path is not None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return parse_catalog(data)
    found = find_catalog_path()
    if found is None:
        return parse_catalog(DEFAULT_CATALOG)
    data = json.loads(found.read_text(encoding="utf-8"))
    return parse_catalog(data)


# --- Flatpak operations ----------------------------------------------------


def flatpak_available(runner: Optional[Runner] = None) -> bool:
    """True when a usable ``flatpak`` binary is on PATH."""
    if runner is None and shutil.which("flatpak") is None:
        return False
    run = runner or default_runner
    code, _, _ = run(["flatpak", "--version"])
    return code == 0


def list_remotes(runner: Optional[Runner] = None) -> List[str]:
    """Return the names of configured Flatpak remotes."""
    run = runner or default_runner
    code, out, _ = run(["flatpak", "remotes", "--columns=name"])
    if code != 0:
        return []
    names = []
    for line in out.splitlines():
        name = line.strip()
        if not name or name.lower() == "name":
            continue
        names.append(name)
    return names


def flathub_configured(runner: Optional[Runner] = None) -> bool:
    return FLATHUB_REMOTE_NAME in list_remotes(runner)


def add_flathub(
    remote_name: str = FLATHUB_REMOTE_NAME,
    url: str = FLATHUB_REPO_URL,
    runner: Optional[Runner] = None,
    system: bool = True,
) -> RunnerResult:
    """Add the Flathub remote if it is not already present.

    The ``--if-not-exists`` flag makes this idempotent, which matters because
    the first-boot service may run more than once.
    """
    run = runner or default_runner
    args = ["flatpak", "remote-add", "--if-not-exists"]
    if system:
        args.append("--system")
    args += [remote_name, url]
    return run(args)


def _installed_columns() -> List[str]:
    return ["application", "name", "version", "branch", "origin"]


def parse_installed(output: str) -> List[Dict[str, str]]:
    """Parse ``flatpak list --columns=...`` tab-separated output."""
    rows: List[Dict[str, str]] = []
    cols = _installed_columns()
    for line in output.splitlines():
        line = line.rstrip("\n")
        if not line.strip():
            continue
        # Flatpak separates columns with a tab; a trailing tab adds a "".
        parts = line.split("\t")
        row = {c: (parts[i].strip() if i < len(parts) else "") for i, c in enumerate(cols)}
        if not row["application"]:
            continue
        rows.append(row)
    return rows


def list_installed(
    runner: Optional[Runner] = None, system: bool = True
) -> List[Dict[str, str]]:
    run = runner or default_runner
    args = ["flatpak", "list", "--app", "--columns=" + ",".join(_installed_columns())]
    if system:
        args.append("--system")
    code, out, _ = run(args)
    if code != 0:
        return []
    return parse_installed(out)


def parse_search(output: str) -> List[Dict[str, str]]:
    """Parse ``flatpak search --columns=...`` output.

    Flatpak uses a tab between columns and may append a descriptive block
    after a blank line; we stop at the first blank line.
    """
    cols = ["name", "application", "version", "description"]
    rows: List[Dict[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            if rows:
                break
            continue
        parts = line.split("\t")
        row = {c: (parts[i].strip() if i < len(parts) else "") for i, c in enumerate(cols)}
        if not row["application"]:
            continue
        rows.append(row)
    return rows


def search(
    query: str,
    runner: Optional[Runner] = None,
    remote: str = FLATHUB_REMOTE_NAME,
) -> List[Dict[str, str]]:
    """Search the catalog first, then Flathub. Catalog hits come first."""
    catalog = load_catalog()
    local = []
    for entry in catalog.find(query):
        row = entry.to_dict()
        # Unify the key so callers can rely on 'application' either way.
        row["application"] = entry.id
        row["source"] = "catalog"
        local.append(row)

    run = runner or default_runner
    code, out, _ = run(
        [
            "flatpak",
            "search",
            "--columns=name,application,version,description",
            query,
        ]
    )
    remote_hits = parse_search(out) if code == 0 else []

    known = set()
    for row in local:
        known.add(row.get("id"))
        known.add(row.get("application"))

    merged = list(local)
    for hit in remote_hits:
        app_id = hit.get("application")
        if not app_id or app_id in known:
            continue
        known.add(app_id)
        merged.append(
            {
                "id": app_id,
                "application": app_id,
                "name": hit.get("name", ""),
                "category": "flathub",
                "description": hit.get("description", ""),
                "kind": "flatpak",
                "core": False,
                "version": hit.get("version", ""),
                "source": "flathub",
            }
        )
    return merged


def _validate_ref(app_id: str) -> None:
    """Reject refs that could not possibly be valid before shelling out.

    Flatpak ids are reverse-DNS (``org.mozilla.firefox``); a full ref may add
    ``/arch/branch``. Whitespace or an empty string is always a mistake, and
    catching it here produces a clear message instead of a flatpak error.
    """
    if not app_id or not app_id.strip():
        raise ValueError("app id is required")
    if any(ch.isspace() for ch in app_id):
        raise ValueError(f"invalid flatpak ref (contains whitespace): {app_id!r}")


def install(
    app_id: str,
    runner: Optional[Runner] = None,
    remote: str = FLATHUB_REMOTE_NAME,
    system: bool = True,
    yes: bool = True,
) -> RunnerResult:
    """Install a Flatpak by application id."""
    _validate_ref(app_id)
    run = runner or default_runner
    args = ["flatpak", "install"]
    if system:
        args.append("--system")
    if yes:
        args.append("-y")
    args += [remote, app_id]
    return run(args)


def remove(
    app_id: str,
    runner: Optional[Runner] = None,
    system: bool = True,
    yes: bool = True,
) -> RunnerResult:
    """Uninstall a Flatpak by application id."""
    _validate_ref(app_id)
    run = runner or default_runner
    args = ["flatpak", "uninstall"]
    if system:
        args.append("--system")
    if yes:
        args.append("-y")
    args.append(app_id)
    return run(args)


def update(
    runner: Optional[Runner] = None, system: bool = True, yes: bool = True
) -> RunnerResult:
    run = runner or default_runner
    args = ["flatpak", "update"]
    if system:
        args.append("--system")
    if yes:
        args.append("-y")
    return run(args)


def status(runner: Optional[Runner] = None) -> Dict[str, object]:
    """Report Flatpak/Flathub readiness for the Settings/TopBar UI."""
    run = runner or default_runner
    available = flatpak_available(run)
    remotes = list_remotes(run) if available else []
    catalog = load_catalog()
    return {
        "flatpak_installed": available,
        "flathub_configured": FLATHUB_REMOTE_NAME in remotes,
        "remotes": remotes,
        "catalog_version": catalog.version,
        "catalog_apps": len(catalog.apps),
        "core_apps": [a.id for a in catalog.core_apps()],
        "installed": len(list_installed(run)) if available else 0,
    }


# --- CLI -------------------------------------------------------------------


def _print_table(rows: List[Dict[str, object]], columns: Sequence[str]) -> None:
    if not rows:
        print("(no results)")
        return
    widths = {
        c: max(len(c), max((len(str(r.get(c, ""))) for r in rows), default=0))
        for c in columns
    }
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    print(header)
    print("-" * len(header))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns))


def _catalog_rows(catalog: Catalog) -> List[Dict[str, object]]:
    return [
        {
            "id": a.id,
            "name": a.name,
            "category": a.category,
            "core": "yes" if a.core else "",
        }
        for a in catalog.apps
    ]


def _emit_json(payload: object, exit_code: int = 0) -> int:
    """Print a JSON payload and return the process exit code.

    The exit code is threaded through explicitly so that ``--json`` callers
    (the Tauri layer, scripts) can still detect failure.
    """
    print(json.dumps(payload, indent=2))
    return exit_code


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Lightweight CLI: ``lucy-app-manager <command> [args] [--json]``.

    ``--json`` may appear anywhere in the argument list and switches the
    read-only commands to machine-readable output for the Tauri layer.
    """
    raw = list(argv if argv is not None else sys.argv[1:])
    as_json = "--json" in raw
    args = [a for a in raw if a != "--json"]
    cmd = args[0] if args else "help"

    try:
        if cmd in ("help", "-h", "--help"):
            if as_json:
                return _emit_json(
                    {
                        "commands": [
                            "list",
                            "search <q>",
                            "install <id>",
                            "remove <id>",
                            "installed",
                            "status",
                            "setup",
                            "update",
                        ]
                    }
                )
            print(__doc__)
            print("Commands: list | search <q> | install <id> | remove <id> |")
            print("          installed | status | setup | update")
            return 0

        if cmd == "list":
            catalog = load_catalog()
            if as_json:
                return _emit_json(catalog.to_dict())
            _print_table(_catalog_rows(catalog), ["id", "name", "category", "core"])
            return 0

        if cmd == "search":
            if len(args) < 2:
                print("usage: lucy-app-manager search <query>", file=sys.stderr)
                return 2
            results = search(args[1])
            if as_json:
                return _emit_json({"query": args[1], "results": results})
            _print_table(results, ["id", "name", "description"])
            return 0

        if cmd == "status":
            info = status()
            if as_json:
                return _emit_json(info)
            for key, value in info.items():
                print(f"{key}: {value}")
            return 0

        if cmd == "setup":
            if not flatpak_available():
                msg = "flatpak is not installed"
                if as_json:
                    return _emit_json({"ok": False, "error": msg})
                print(msg, file=sys.stderr)
                return 1
            code, out, err = add_flathub()
            ok = code == 0
            if as_json:
                return _emit_json(
                    {"ok": ok, "exit_code": code, "output": out, "error": err},
                    exit_code=code,
                )
            print(out or err or f"flathub configured (exit {code})")
            return code

        if cmd == "installed":
            rows = list_installed()
            if as_json:
                return _emit_json({"installed": rows})
            _print_table(rows, ["application", "name", "version"])
            return 0

        if cmd == "install":
            if len(args) < 2:
                print("usage: lucy-app-manager install <id>", file=sys.stderr)
                return 2
            code, out, err = install(args[1])
            if as_json:
                return _emit_json(
                    {"ok": code == 0, "exit_code": code, "app": args[1],
                     "output": out, "error": err},
                    exit_code=code,
                )
            sys_out = out or err
            if sys_out:
                print(sys_out)
            return code

        if cmd == "remove":
            if len(args) < 2:
                print("usage: lucy-app-manager remove <id>", file=sys.stderr)
                return 2
            code, out, err = remove(args[1])
            if as_json:
                return _emit_json(
                    {"ok": code == 0, "exit_code": code, "app": args[1],
                     "output": out, "error": err},
                    exit_code=code,
                )
            sys_out = out or err
            if sys_out:
                print(sys_out)
            return code

        if cmd == "update":
            code, out, err = update()
            if as_json:
                return _emit_json(
                    {"ok": code == 0, "exit_code": code, "output": out, "error": err},
                    exit_code=code,
                )
            sys_out = out or err
            if sys_out:
                print(sys_out)
            return code

        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2
    except (AppManagerError, ValueError) as exc:
        if as_json:
            return _emit_json({"ok": False, "error": str(exc)}, exit_code=1)
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
