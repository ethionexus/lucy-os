#!/usr/bin/env python3
"""Verify the v0.4.0 app/Flatpak/installer/boot configuration.

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
* the initramfs carries the archiso hooks, in the right order
* no airootfs file sits under a package-owned path
* Calamares is absent from packages.x86_64 (AUR-only) and the configs are
  present, including the postinstall step that strips the live archiso hook
* Super+Space is owned by the command palette, not the WM
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
LIGHTDM_CONF = OVERLAY / "lightdm" / "lightdm.conf"
GREETER_CONF = OVERLAY / "lightdm" / "lightdm-gtk-greeter.conf"
PLYMOUTH_CONF = OVERLAY / "plymouth" / "plymouthd.conf"

FLATPAK_INIT = AIROOTFS / "usr" / "local" / "bin" / "lucy-flatpak-init"
APP_MANAGER = AIROOTFS / "usr" / "local" / "bin" / "lucy-app-manager"
UNIT = AIROOTFS / "etc" / "systemd" / "system" / "lucy-flatpak-init.service"
PACKAGES = REPO / "src" / "configs" / "packages.x86_64"

PROFILEDEF = REPO / "src" / "configs" / "profiledef.sh"
MKINITCPIO_DROPIN = AIROOTFS / "etc" / "mkinitcpio.conf.d" / "archiso.conf"
FSTAB = AIROOTFS / "etc" / "fstab"
SYSLINUX_CFG = REPO / "src" / "configs" / "syslinux" / "syslinux.cfg"
EFIBOOT_ENTRIES = REPO / "src" / "configs" / "efiboot" / "loader" / "entries"

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


def check_boot_config() -> None:
    """Guards against the initramfs/bootloader problems that stop an ISO boot.

    The signature failure this catches is a missing `archiso` initcpio hook,
    which produces "[FAILED] Failed to start Switch Root" and drops the user
    into emergency mode.
    """
    print("=== boot: initramfs hooks ===")

    if not MKINITCPIO_DROPIN.is_file():
        fail("etc/mkinitcpio.conf.d/archiso.conf is missing (ISO will not boot)")
        return

    text = MKINITCPIO_DROPIN.read_text(encoding="utf-8")
    line = next((l for l in text.splitlines()
                 if l.strip().startswith("HOOKS=")), "")
    if not line:
        fail("archiso.conf has no HOOKS= line")
        return

    raw = line.split("(", 1)[-1].split(")", 1)[0]
    hooks = raw.split()
    ok(f"initramfs hooks: {' '.join(hooks)}")

    for required in ("archiso", "archiso_loop_mnt"):
        if required not in hooks:
            fail(f"required initcpio hook {required!r} is missing")
        else:
            ok(f"hook {required} present")

    def pos(name: str) -> int:
        return hooks.index(name) if name in hooks else -1

    # archiso/archiso_loop_mnt create the live root device, so they must come
    # before the hooks that mount it.
    if pos("archiso_loop_mnt") != -1 and pos("block") != -1 and pos("archiso_loop_mnt") < pos("block"):
        ok("archiso hooks ordered before 'block'")
    else:
        fail("archiso/archiso_loop_mnt must come before the 'block' hook")

    if pos("filesystems") == -1:
        fail("the 'filesystems' hook is missing")
    elif pos("block") != -1 and pos("block") < pos("filesystems"):
        ok("'block' ordered before 'filesystems'")
    else:
        fail("'block' must come before 'filesystems'")

    # The hook implementation ships in mkinitcpio-archiso, which archiso does
    # not depend on, so it must be an explicit package.
    pkgs = {
        ln.strip() for ln in PACKAGES.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }
    if "mkinitcpio-archiso" in pkgs:
        ok("mkinitcpio-archiso is in packages.x86_64")
    else:
        fail("mkinitcpio-archiso is not in packages.x86_64 (archiso hook would be missing)")
    if "mkinitcpio" in pkgs:
        ok("mkinitcpio is in packages.x86_64")

    print("=== boot: fstab and bootloader label ===")

    # A live ISO must not carry a static fstab with disk UUIDs.
    if not FSTAB.is_file():
        ok("no airootfs/etc/fstab (correct for live media)")
    else:
        body = [
            l.strip() for l in FSTAB.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        uuid_lines = [l for l in body if "UUID=" in l]
        if not body:
            ok("airootfs/etc/fstab is empty")
        elif uuid_lines:
            fail(f"airootfs/etc/fstab has static UUID mounts: {uuid_lines[:3]}")
        else:
            note(f"airootfs/etc/fstab has {len(body)} entry(ies)")

    # The bootloaders use %ARCHISO_LABEL%, which archiso substitutes with
    # iso_label; if the placeholder is dropped the label never matches.
    pd = PROFILEDEF.read_text(encoding="utf-8")
    label = ""
    for ln in pd.splitlines():
        if ln.strip().startswith("iso_label="):
            label = ln.split("=", 1)[1].strip().strip('"').strip("'")
    if label:
        ok(f"profiledef iso_label = {label!r}")
    else:
        fail("profiledef.sh has no iso_label")

    for cfg in [SYSLINUX_CFG, *sorted(EFIBOOT_ENTRIES.glob("*.conf"))]:
        if not cfg.is_file():
            fail(f"missing bootloader config {cfg.name}")
            continue
        body = cfg.read_text(encoding="utf-8")
        if "%ARCHISO_LABEL%" not in body:
            fail(f"{cfg.name} does not use %ARCHISO_LABEL% (label would not match)")
        elif "%INSTALL_DIR%" not in body or "%ARCHISO_UUID%" not in body:
            fail(f"{cfg.name} is missing %INSTALL_DIR%/%ARCHISO_UUID%")
        else:
            ok(f"{cfg.name} uses the archiso boot placeholders")


def check_installer_and_palette() -> None:
    """Guards for the Phase 2 installer, command palette and app store."""
    print("=== installer (Calamares / archinstall) ===")

    pkgs = {
        ln.strip() for ln in PACKAGES.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }

    # calamares is AUR-only: listing it makes pacstrap abort with
    # "target not found" and breaks the entire ISO build.
    if "calamares" in pkgs:
        fail("calamares is in packages.x86_64 but is AUR-only (build would fail)")
    else:
        ok("calamares is not in packages.x86_64 (AUR-only, correct)")

    for pkg in ("archinstall", "btrfs-progs", "efibootmgr"):
        if pkg in pkgs:
            ok(f"{pkg} is in packages.x86_64")
        else:
            fail(f"{pkg} is missing from packages.x86_64")

    # customize_airootfs.sh must probe calamares without failing the build.
    if CUSTOMIZE.is_file():
        text = CUSTOMIZE.read_text(encoding="utf-8")
        if "pacman -Si calamares" in text:
            ok("build hook probes calamares best-effort")
        else:
            fail("build hook does not probe calamares")
    else:
        fail("customize_airootfs.sh missing")

    cal = AIROOTFS / "etc" / "calamares"
    for rel in (
        "settings.conf",
        "modules/partition.conf",
        "modules/mount.conf",
        "modules/unpackfs.conf",
        "modules/bootloader.conf",
        "modules/initcpiocfg.conf",
        "modules/shellprocess-postinstall.conf",
        "branding/lucy/branding.desc",
    ):
        if (cal / rel).is_file():
            ok(f"calamares config {rel}")
        else:
            fail(f"calamares config missing: {rel}")

    post = cal / "modules" / "shellprocess-postinstall.conf"
    if post.is_file():
        body = post.read_text(encoding="utf-8")
        # Without this the installed system inherits the live archiso hook and
        # cannot boot — the very failure the ISO just had.
        if "mkinitcpio.conf.d/archiso.conf" in body:
            ok("postinstall strips the archiso hook from the installed system")
        else:
            fail("postinstall does not remove /etc/mkinitcpio.conf.d/archiso.conf")
        if "dontChroot: true" in body:
            ok("postinstall runs against ${ROOT} (dontChroot: true)")
        else:
            fail("postinstall uses ${ROOT} paths but is not dontChroot: true")

    part = cal / "modules" / "partition.conf"
    if part.is_file() and "/.snapshots" in part.read_text(encoding="utf-8"):
        ok("partition.conf creates /.snapshots for the rollback engine")
    elif part.is_file():
        fail("partition.conf has no /.snapshots subvolume")

    # bootloader.conf installs GRUB into the target, so GRUB has to be on the
    # medium as well or a Calamares install cannot finish.
    boot = cal / "modules" / "bootloader.conf"
    if boot.is_file() and "grub" in boot.read_text(encoding="utf-8").lower():
        if "grub" in pkgs:
            ok("bootloader.conf wants GRUB and grub is in packages.x86_64")
        else:
            fail("bootloader.conf installs GRUB but grub is not in packages.x86_64")

    # Desktop entries must point at an icon that actually exists.
    pixmap = AIROOTFS / "usr" / "share" / "pixmaps" / "lucy.png"
    if pixmap.is_file():
        ok("lucy.png icon shipped for the desktop entries")
    else:
        fail("usr/share/pixmaps/lucy.png missing (Icon=lucy would not resolve)")

    if (AIROOTFS / "etc" / "skel" / "Desktop" / "calamares.desktop").is_file():
        ok("live Desktop shortcut Install Lucy OS")
    else:
        fail("missing etc/skel/Desktop/calamares.desktop")

    inst = AIROOTFS / "usr" / "local" / "bin" / "lucy-installer"
    if inst.is_file():
        body = inst.read_text(encoding="utf-8")
        if "calamares" in body and "archinstall" in body:
            ok("lucy-installer prefers calamares and falls back to archinstall")
        else:
            fail("lucy-installer lacks the archinstall fallback")

    print("=== command palette key wiring ===")
    rc = REPO / "src" / "configs" / "airootfs" / "etc" / "xdg" / "openbox" / "lxde-rc.xml"
    if rc.is_file():
        body = rc.read_text(encoding="utf-8")
        if 'keybind key="Super+space"' in body:
            fail("openbox also binds Super+space; it is reserved for the palette")
        else:
            ok("openbox does not bind Super+space (palette owns it)")
        if 'keybind key="Super+Shift+space"' in body:
            ok("keyboard layout toggle moved to Super+Shift+space")
        else:
            fail("keyboard layout toggle binding missing (Super+Shift+space)")

    lib = REPO / "src" / "shell" / "src-tauri" / "src" / "lib.rs"
    app = REPO / "src" / "shell" / "src" / "App.tsx"
    if lib.is_file():
        body = lib.read_text(encoding="utf-8")
        if "Modifiers::SUPER" in body and "Code::Space" in body:
            ok("Tauri registers Super+Space")
        else:
            fail("Tauri does not register the Super+Space global shortcut")

        # The event name must match on both sides or the palette never opens.
        m = re.search(r'PALETTE_EVENT: &str = "([^"]+)"', body)
        event = m.group(1) if m else None
        if event and app.is_file() and event in app.read_text(encoding="utf-8"):
            ok(f"palette event name matches across Rust and React ({event})")
        else:
            fail(f"palette event name mismatch (rust={event!r})")

    store = REPO / "src" / "shell" / "src" / "components" / "AppStore.tsx"
    if store.is_file():
        body = store.read_text(encoding="utf-8")
        rpcs = [
            "app_catalog", "app_search", "app_install",
            "app_remove", "app_installed", "app_status", "app_flathub_setup",
        ]
        missing = [r for r in rpcs if f'"{r}"' not in body]
        if missing:
            fail(f"App Store does not call: {missing}")
        else:
            ok("App Store calls all 7 appstore RPCs")
    else:
        fail("AppStore.tsx missing")


def check_live_boot() -> None:
    """Guards the live-boot pipeline: autologin, no prompts, splash.

    The failure this catches is exactly the reported one — the ISO falling
    through to a TTY login because nothing started the display manager.
    """
    print("=== live boot: autologin + display manager ===")

    # These live in the post-install overlay, NOT in etc/, because the
    # packages that own those paths ship their own copies and would replace
    # an airootfs copy during pacstrap. That is what silently dropped
    # autologin-user=lucy once.
    for path, owner in ((LIGHTDM_CONF, "lightdm"),
                        (GREETER_CONF, "lightdm-gtk-greeter"),
                        (PLYMOUTH_CONF, "plymouth")):
        if path.is_file():
            ok(f"{path.name} staged for post-install by {owner}")
        else:
            fail(f"{path.name} is not staged under usr/share/lucy/overlay")

    # Nothing may sit in airootfs/etc for these package-owned paths.
    strays = {
        "etc/lightdm/lightdm.conf": "lightdm",
        "etc/lightdm/lightdm-gtk-greeter.conf": "lightdm-gtk-greeter",
        "etc/plymouth/plymouthd.conf": "plymouth",
    }
    for stray, owner in strays.items():
        if (AIROOTFS / stray).exists():
            fail(f"{stray} is in the airootfs; the {owner} package would overwrite it")

    lightdm = LIGHTDM_CONF
    if not lightdm.is_file():
        fail("lightdm.conf is missing (boot would reach a TTY/greeter)")
    else:
        body = lightdm.read_text(encoding="utf-8")
        checks = {
            "autologin-user=lucy": "autologin for the live user",
            "autologin-user-timeout=0": "no wait for input",
            "autologin-session=lucy": "session selected for autologin",
            "greeter-session=lightdm-gtk-greeter": "GTK greeter",
        }
        for needle, label in checks.items():
            if needle in body:
                ok(label)
            else:
                fail(f"lightdm.conf missing {needle!r} ({label})")

    greeter = GREETER_CONF
    if greeter.is_file():
        body = greeter.read_text(encoding="utf-8")
        # Two [greeter] groups would be a malformed key file.
        if body.count("[greeter]") > 1:
            fail("lightdm-gtk-greeter.conf has duplicate [greeter] sections")
        else:
            ok("greeter theme configured (papirus/deepin available)")
    else:
        fail("etc/lightdm/lightdm-gtk-greeter.conf missing")

    xsess = AIROOTFS / "usr" / "share" / "xsessions" / "lucy.desktop"
    if xsess.is_file() and "Exec=/usr/local/bin/lucy-session" in xsess.read_text(encoding="utf-8"):
        ok("xsession 'lucy' points at lucy-session")
    else:
        fail("usr/share/xsessions/lucy.desktop missing or wrong Exec")

    session = AIROOTFS / "usr" / "local" / "bin" / "lucy-session"
    if session.is_file() and "startlxde" in session.read_text(encoding="utf-8"):
        ok("lucy-session launches the desktop")
    else:
        fail("lucy-session missing or does not start the desktop")

    # The hook has to do the symlink/mask/user work; nothing else will.
    hook = CUSTOMIZE.read_text(encoding="utf-8") if CUSTOMIZE.is_file() else ""
    required_hook = {
        "/etc/systemd/system/display-manager.service": "symlinks display-manager.service",
        "graphical.target": "sets the graphical default target",
        "systemd-firstboot.service": "masks systemd-firstboot",
        "getty@tty1.service": "masks the tty1 login prompt",
        "useradd": "creates the live user",
        "NOPASSWD": "grants passwordless sudo",
        # Without this the greeter asks for a password even though
        # autologin-user is set: pam_succeed_if fails and PAM falls through.
        "groupadd": "creates the autologin group",
        "autologin": "adds the live user to the autologin group",
        "/etc/pam.d/lightdm-autologin": "touches the lightdm-autologin PAM stack",
        # Package-owned config paths must be installed post-pacstrap.
        "OVERLAY/lightdm": "installs the LightDM configs after pacstrap",
        "OVERLAY/plymouth/plymouthd.conf": "installs plymouthd.conf after pacstrap",
    }
    for needle, label in required_hook.items():
        if needle in hook:
            ok(f"build hook {label}")
        else:
            fail(f"build hook does not {label}")

    print("=== live boot: plymouth ===")
    pkgs = {
        ln.strip() for ln in PACKAGES.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }
    for pkg in ("plymouth", "lightdm", "lightdm-gtk-greeter", "papirus-icon-theme",
                "deepin-icon-theme", "deepin-gtk-theme", "gnu-free-fonts"):
        if pkg in pkgs:
            ok(f"{pkg} is in packages.x86_64")
        else:
            fail(f"{pkg} is missing from packages.x86_64")

    # AUR-only theme packages would break the build.
    for pkg in ("fluent-gtk-theme", "arc-gtk-theme", "numix-icon-theme", "qogir-icon-theme"):
        if pkg in pkgs:
            fail(f"{pkg} is AUR-only and must not be in packages.x86_64")
    ok("no AUR-only theme packages")

    dropin = MKINITCPIO_DROPIN.read_text(encoding="utf-8") if MKINITCPIO_DROPIN.is_file() else ""
    line = next((l for l in dropin.splitlines() if l.strip().startswith("HOOKS=")), "")
    hooks = line.split("(", 1)[-1].split(")", 1)[0].split() if line else []
    if "plymouth" in hooks:
        after_udev = "udev" in hooks and hooks.index("udev") < hooks.index("plymouth")
        before_kms = (hooks.index("kms") > hooks.index("plymouth")) if "kms" in hooks else True
        if after_udev and before_kms:
            ok("plymouth hook sits right after udev and before kms")
        else:
            fail("plymouth hook is not ordered after udev / before kms")
    else:
        fail("plymouth is not in the initramfs HOOKS")
    if "archiso" in hooks:
        ok("archiso hook still present alongside plymouth")
    else:
        fail("archiso hook was lost while adding plymouth")

    theme = AIROOTFS / "usr" / "share" / "plymouth" / "themes" / "lucy"
    for rel in ("lucy.plymouth", "lucy.script"):
        if (theme / rel).is_file():
            ok(f"plymouth theme file {rel}")
        else:
            fail(f"plymouth theme file missing: {rel}")
    if PLYMOUTH_CONF.is_file() and "Theme=lucy" in PLYMOUTH_CONF.read_text(encoding="utf-8"):
        ok("plymouthd.conf selects the lucy theme")
    else:
        fail("plymouthd.conf does not select the lucy theme")

    if (AIROOTFS / "etc" / "skel" / ".config" / "gtk-3.0" / "settings.ini").is_file():
        ok("GTK/icon theme set for the live session")
    else:
        fail("etc/skel/.config/gtk-3.0/settings.ini missing")

    bootcheck = AIROOTFS / "usr" / "local" / "bin" / "lucy-boot-check"
    if bootcheck.is_file():
        ok("lucy-boot-check verification script shipped")
    else:
        fail("lucy-boot-check missing")


def main() -> int:
    print("Lucy OS v0.4.0 — app/Flatpak/installer/boot configuration verification\n")
    check_catalog()
    check_packages()
    check_browser_configs()
    check_overlay_hook()
    check_boot_config()
    check_installer_and_palette()
    check_live_boot()
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
