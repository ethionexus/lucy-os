#!/usr/bin/env python3
"""Verify the v0.4.0 Phase 1 app/Flatpak configuration.

Runs in CI (and on the live ISO) without pytest or a real Flatpak. Exits
non-zero with a readable report if anything is malformed.

Checks
------
* /etc/lucy/apps.json parses and matches the catalog schema
* app ids are unique; core apps map to a native package
* Flatpak ids look like reverse-DNS
* the Firefox policy and Chromium flag files are valid
* the shell helpers pass `bash -n`
* the systemd unit declares ExecStart and is wanted by multi-user.target
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AIROOTFS = REPO / "src" / "configs" / "airootfs"

APPS_JSON = AIROOTFS / "etc" / "lucy" / "apps.json"
OVERLAY = AIROOTFS / "usr" / "share" / "lucy" / "overlay"
POLICIES_JSON = OVERLAY / "firefox" / "distribution" / "policies.json"
CHROMIUM_FLAGS = OVERLAY / "chromium-flags.conf"
XKB_LAYOUT = OVERLAY / "xkb" / "symbols" / "lucy-amharic"
CUSTOMIZE = AIROOTFS / "root" / "customize_airootfs.sh"
FLATPAK_INIT = AIROOTFS / "usr" / "local" / "bin" / "lucy-flatpak-init"
APP_MANAGER = AIROOTFS / "usr" / "local" / "bin" / "lucy-app-manager"
UNIT = AIROOTFS / "etc" / "systemd" / "system" / "lucy-flatpak-init.service"
PACKAGES = REPO / "src" / "configs" / "packages.x86_64"

# reverse-DNS, at least three dot-separated labels. Flathub does allow short
# ids in rare cases, so only the clearly-wrong shapes are rejected.
REVERSE_DNS = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*\.[A-Za-z0-9_-]+$")

problems: list[str] = []
notes: list[str] = []


def ok(msg: str) -> None:
    print(f"  OK   {msg}")


def fail(msg: str) -> None:
    problems.append(msg)
    print(f"  FAIL {msg}")


def note(msg: str) -> None:
    notes.append(msg)
    print(f"  note {msg}")


def check_catalog() -> None:
    print("=== catalog: etc/lucy/apps.json ===")
    if not APPS_JSON.is_file():
        fail(f"missing {APPS_JSON.relative_to(REPO)}")
        return
    try:
        data = json.loads(APPS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}")
        return
    ok("valid JSON")

    if data.get("remote_name") != "flathub":
        fail("remote_name must be 'flathub'")
    else:
        ok("remote_name is flathub")

    url = str(data.get("remote_url", ""))
    if not url.startswith("https://"):
        fail(f"remote_url must be https (got {url!r})")
    else:
        ok(f"remote_url = {url}")

    apps = data.get("apps")
    if not isinstance(apps, list) or not apps:
        fail("'apps' must be a non-empty list")
        return

    seen: set[str] = set()
    dupes: list[str] = []
    core_native = 0
    bad_ids: list[str] = []
    for entry in apps:
        if not isinstance(entry, dict):
            fail("every app entry must be an object")
            continue
        app_id = str(entry.get("id", "")).strip()
        if not app_id:
            fail("an app entry is missing 'id'")
            continue
        if app_id in seen:
            dupes.append(app_id)
        seen.add(app_id)

        kind = entry.get("kind", "flatpak")
        if kind not in ("flatpak", "native"):
            fail(f"{app_id}: unknown kind {kind!r}")
        if kind == "native" and not entry.get("native_package"):
            fail(f"{app_id}: native app without native_package")
        if kind == "flatpak" and not REVERSE_DNS.match(app_id):
            bad_ids.append(app_id)
        if entry.get("core") and kind == "native":
            core_native += 1

    if dupes:
        fail(f"duplicate app ids: {dupes}")
    else:
        ok(f"{len(apps)} apps, ids unique")

    if bad_ids:
        fail(f"flatpak ids not reverse-DNS: {bad_ids}")
    else:
        ok("all flatpak ids are reverse-DNS")

    if core_native == 0:
        fail("no core native apps declared")
    else:
        ok(f"{core_native} core native apps")


def check_packages() -> None:
    print("=== packages.x86_64 ===")
    if not PACKAGES.is_file():
        fail("packages.x86_64 missing")
        return
    lines = {
        ln.strip()
        for ln in PACKAGES.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }
    required = {"flatpak", "xdg-desktop-portal", "xdg-desktop-portal-gtk", "firefox"}
    missing = sorted(required - lines)
    if missing:
        fail(f"missing required packages: {missing}")
    else:
        ok(f"flatpak/portal/browser packages present ({len(lines)} total)")

    # Guard against the AUR-only names that must never appear here.
    forbidden = {"brave-bin", "vscodium-bin", "calamares", "google-chrome"}
    present = sorted(forbidden & lines)
    if present:
        fail(f"AUR/3rd-party packages must not be in packages.x86_64: {present}")
    else:
        ok("no AUR-only packages leaked in")


def check_browser_configs() -> None:
    print("=== browser hardware acceleration (staged overlay) ===")
    if not POLICIES_JSON.is_file():
        fail("firefox policies.json missing from the overlay")
    else:
        try:
            pol = json.loads(POLICIES_JSON.read_text(encoding="utf-8"))
            prefs = pol.get("policies", {}).get("Preferences", {})
            if prefs.get("media.ffmpeg.vaapi.enabled", {}).get("Value") is True:
                ok(f"firefox VA-API default enabled ({len(prefs)} prefs)")
            else:
                fail("firefox VA-API preference not enabled")
        except json.JSONDecodeError as exc:
            fail(f"firefox policies.json invalid: {exc}")

    if not CHROMIUM_FLAGS.is_file():
        fail("chromium-flags.conf missing from the overlay")
    else:
        text = CHROMIUM_FLAGS.read_text(encoding="utf-8")
        flags = [ln.strip() for ln in text.splitlines()
                 if ln.strip().startswith("--")]
        if flags:
            ok(f"chromium flags present ({len(flags)} flags)")
        else:
            fail("chromium-flags.conf has no flags")


def check_overlay_hook() -> None:
    """Nothing may sit under a package-owned directory in the airootfs.

    archiso copies the overlay before pacstrap, so a file under e.g.
    /usr/share/X11/xkb makes pacman abort with a file conflict. Such files
    must be staged under usr/share/lucy/overlay and copied by the hook.
    """
    print("=== airootfs overlay safety ===")

    risky = [
        "usr/share/X11",
        "usr/lib/firefox",
        "usr/lib",
        "etc/chromium-flags.conf",
    ]
    found = [p for p in risky if (AIROOTFS / p).exists()]
    if found:
        fail(f"collision-prone paths present in the airootfs: {found}")
    else:
        ok("no files under package-owned paths in the airootfs")

    if not XKB_LAYOUT.is_file():
        fail("xkb layout missing from the overlay")
    else:
        text = XKB_LAYOUT.read_text(encoding="utf-8")
        if 'xkb_symbols "basic"' in text and "level3(ralt_switch)" in text:
            ok("xkb layout staged and well-formed")
        else:
            fail("xkb layout staged but missing required xkb boilerplate")

    if not CUSTOMIZE.is_file():
        fail("customize_airootfs.sh hook missing")
        return
    text = CUSTOMIZE.read_text(encoding="utf-8")
    for needle, label in (
        ("/usr/share/X11/xkb/symbols", "installs the xkb layout"),
        ("/usr/lib/firefox/distribution/policies.json", "installs the firefox policy"),
        ("/etc/chromium-flags.conf", "installs the chromium flags"),
    ):
        if needle in text:
            ok(f"hook {label}")
        else:
            fail(f"hook does not {label}")


def check_scripts() -> None:
    print("=== shell helpers ===")
    bash = shutil.which("bash")
    for path in (FLATPAK_INIT, APP_MANAGER, CUSTOMIZE):
        if not path.is_file():
            fail(f"missing {path.name}")
            continue
        if bash is None:
            note(f"bash not available; skipped syntax check for {path.name}")
            continue
        proc = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True)
        if proc.returncode == 0:
            ok(f"{path.name} passes bash -n")
        else:
            fail(f"{path.name} syntax error: {proc.stderr.strip()}")


def check_unit() -> None:
    print("=== systemd unit ===")
    if not UNIT.is_file():
        fail("lucy-flatpak-init.service missing")
        return
    text = UNIT.read_text(encoding="utf-8")
    for needle in (
        "ExecStart=/usr/local/bin/lucy-flatpak-init",
        "WantedBy=multi-user.target",
        "Type=oneshot",
    ):
        if needle in text:
            ok(f"unit contains {needle!r}")
        else:
            fail(f"unit missing {needle!r}")


def main() -> int:
    print("Lucy OS v0.4.0 Phase 1 — app/Flatpak configuration verification\n")
    check_catalog()
    check_packages()
    check_browser_configs()
    check_overlay_hook()
    check_scripts()
    check_unit()

    print()
    if notes:
        print(f"{len(notes)} note(s) — checks skipped in this environment")
    if problems:
        print(f"RESULT: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
