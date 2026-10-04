#!/usr/bin/env bash
# Lucy OS archiso build hook (runs inside the chroot, after packages install).
#
# archiso copies airootfs/ into the build root *before* pacstrap, so any file
# placed directly under a package-owned directory (for example
# /usr/share/X11/xkb or /usr/lib/firefox) makes pacman refuse to install that
# package:
#
#   error: failed to commit transaction (conflicting files)
#   xkeyboard-config: /usr/share/X11/xkb exists in filesystem
#
# Files that need to live in such directories are therefore staged under
# /usr/share/lucy/overlay/ (a path no package owns) and copied into place
# here, once the owning packages are installed.
#
# archiso deletes this script afterwards, so it never ships in the ISO.

set -euo pipefail

OVERLAY="/usr/share/lucy/overlay"
log() { printf 'lucy-customize: %s\n' "$*"; }

# --- XKB symbols (owned by xkeyboard-config) -------------------------------
if [ -d "$OVERLAY/xkb/symbols" ]; then
    install -d -m 0755 /usr/share/X11/xkb/symbols
    for f in "$OVERLAY"/xkb/symbols/*; do
        [ -e "$f" ] || continue
        log "installing XKB layout $(basename "$f")"
        install -m 0644 "$f" "/usr/share/X11/xkb/symbols/$(basename "$f")"
    done
fi

# --- Firefox policies (under the firefox package tree) ---------------------
if [ -f "$OVERLAY/firefox/distribution/policies.json" ]; then
    if [ -d /usr/lib/firefox ]; then
        install -d -m 0755 /usr/lib/firefox/distribution
        log "installing Firefox hardware-acceleration policy"
        install -m 0644 "$OVERLAY/firefox/distribution/policies.json" \
            /usr/lib/firefox/distribution/policies.json
    else
        log "firefox is not installed; skipping browser policy"
    fi
fi

# --- Chromium flags (the chromium package ships an empty template) ---------
if [ -f "$OVERLAY/chromium-flags.conf" ]; then
    log "installing Chromium hardware-acceleration flags"
    install -m 0644 "$OVERLAY/chromium-flags.conf" /etc/chromium-flags.conf
fi

# --- initramfs ------------------------------------------------------------
# archiso does not run mkinitcpio; it copies /boot from this root onto the
# ISO. Rebuild here so the archiso hooks are guaranteed to be included, and
# fail the build loudly if they are not — a missing archiso hook produces an
# ISO that boots straight into "Failed to start Switch Root" emergency mode.
if ! [ -f /etc/mkinitcpio.conf.d/archiso.conf ]; then
    echo "lucy-customize: ERROR: /etc/mkinitcpio.conf.d/archiso.conf is missing" >&2
    exit 1
fi

if command -v mkinitcpio >/dev/null 2>&1; then
    log "rebuilding initramfs (this proves the archiso hooks resolve)"
    # mkinitcpio exits non-zero if any hook in HOOKS cannot be found, so a
    # successful run already means archiso/archiso_loop_mnt were available.
    mkinitcpio -P

    if command -v lsinitcpio >/dev/null 2>&1; then
        for img in /boot/initramfs-*.img; do
            [ -e "$img" ] || continue
            if lsinitcpio "$img" 2>/dev/null | grep -q '^hooks/archiso$'; then
                log "verified: archiso hook present in $(basename "$img")"
            else
                echo "lucy-customize: ERROR: archiso hook missing from $img" >&2
                exit 1
            fi
        done
    fi
else
    echo "lucy-customize: ERROR: mkinitcpio not found" >&2
    exit 1
fi

# --- OS installer ---------------------------------------------------------
# `calamares` lives in the AUR, not the official repos, so it must NOT be in
# packages.x86_64 (pacstrap would abort with "target not found"). Probe it
# best-effort so a future move into [extra] is picked up automatically, and
# never fail the build over it. archinstall is the guaranteed fallback.
if pacman -Si calamares >/dev/null 2>&1; then
    log "installing Calamares from the official repos"
    pacman -S --noconfirm --needed calamares || \
        printf 'lucy-customize: warning: calamares install failed; continuing\n' >&2
else
    log "calamares is not in the official repos (AUR-only); graphical installer unavailable"
fi

log "overlay applied"
