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

log "overlay applied"
