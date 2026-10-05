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

# --- Plymouth logo --------------------------------------------------------
# The theme lives in the airootfs; the logo is the same file the desktop
# entries use, copied here so the image has a single source of truth.
if [ -f /usr/share/pixmaps/lucy.png ] && [ -d /usr/share/plymouth/themes/lucy ]; then
    install -m 0644 /usr/share/pixmaps/lucy.png \
        /usr/share/plymouth/themes/lucy/lucy.png
    log "installed Plymouth theme logo"
fi

# --- Live user ------------------------------------------------------------
# A real user (not root) with an empty password and passwordless sudo, so the
# live session behaves like an installed system. `-m` copies /etc/skel, which
# is how the "Install Lucy OS" desktop shortcut appears.
if ! id lucy >/dev/null 2>&1; then
    log "creating live user 'lucy'"
    useradd -m -c "Lucy OS Live User" \
        -G wheel,video,audio,storage,optical,network,power \
        -s /bin/bash lucy
    # Empty password: autologin needs none, and sudo never prompts.
    passwd -d lucy >/dev/null
fi

# sudo already ships /etc/sudoers.d; only create it if a minimal image lacks
# it, so we never chmod a package-owned directory.
[ -d /etc/sudoers.d ] || install -d -m 0750 /etc/sudoers.d
printf '# Lucy OS live user: no password prompt inside the live session.\nlucy ALL=(ALL:ALL) NOPASSWD: ALL\n' \
    > /etc/sudoers.d/10-lucy
chmod 0440 /etc/sudoers.d/10-lucy || true
log "live user ready (passwordless sudo)"

# --- LightDM autologin group ----------------------------------------------
# Having autologin-user in lightdm.conf is NOT enough. LightDM authenticates
# through the lightdm-autologin PAM stack, whose first rule is normally
#
#     auth sufficient pam_succeed_if.so user ingroup autologin
#
# If the user is not in that group the rule fails, PAM falls through to
# system-login, and the greeter appears asking for a password even though
# autologin is configured correctly.
#
# The group name varies between distributions (autologin vs nopasswdlogin), so
# read it from the installed PAM file instead of assuming, and always cover
# "autologin" as well.
AUTOLOGIN_PAM="/etc/pam.d/lightdm-autologin"
autologin_groups="autologin"

if [ -f "$AUTOLOGIN_PAM" ]; then
    for g in $(sed -n 's/.*pam_succeed_if\.so.*ingroup[[:space:]]\{1,\}\([A-Za-z0-9_-]\{1,\}\).*/\1/p' \
                   "$AUTOLOGIN_PAM" 2>/dev/null); do
        case " $autologin_groups " in
            *" $g "*) ;;
            *) autologin_groups="$autologin_groups $g" ;;
        esac
    done
fi

for g in $autologin_groups; do
    getent group "$g" >/dev/null 2>&1 || groupadd -r "$g" 2>/dev/null || true
    gpasswd -a lucy "$g" >/dev/null 2>&1 || usermod -aG "$g" lucy >/dev/null 2>&1 || true
done
log "autologin group membership: $(id -nG lucy 2>/dev/null || echo unknown)"

# If the PAM stack has no autologin rule at all it would still demand a
# password. Add a sufficient rule at the top of the auth stack.
if [ -f "$AUTOLOGIN_PAM" ]; then
    if grep -q 'pam_succeed_if' "$AUTOLOGIN_PAM"; then
        log "lightdm-autologin already permits group-based autologin"
    else
        pam_tmp="$(mktemp)"
        {
            printf '# Lucy OS: passwordless autologin for the live user.\n'
            printf 'auth      sufficient pam_succeed_if.so user ingroup autologin\n'
            cat "$AUTOLOGIN_PAM"
        } > "$pam_tmp"
        cat "$pam_tmp" > "$AUTOLOGIN_PAM"
        rm -f "$pam_tmp"
        log "added pam_succeed_if autologin rule to $AUTOLOGIN_PAM"
    fi
fi

# --- Display manager + graphical target -----------------------------------
# Explicitly symlink display-manager.service: lightdm and lxdm can both be
# installed, and without this link nothing starts X and the boot falls through
# to a TTY login prompt.
DM_UNIT=""
for unit in /usr/lib/systemd/system/lightdm.service /lib/systemd/system/lightdm.service; do
    if [ -f "$unit" ]; then DM_UNIT="$unit"; break; fi
done

if [ -n "$DM_UNIT" ]; then
    ln -sf "$DM_UNIT" /etc/systemd/system/display-manager.service
    log "display-manager.service -> $DM_UNIT"
else
    printf 'lucy-customize: warning: lightdm.service not found; no display manager\n' >&2
fi

# Boot straight to the desktop.
ln -sf /usr/lib/systemd/system/graphical.target /etc/systemd/system/default.target
log "default target -> graphical.target"

# --- Suppress interactive prompts -----------------------------------------
# Masked units are symlinks to /dev/null, systemd's way of making a unit
# impossible to start. tty2-6 stay available (logind starts them on demand) so
# a broken session can still be rescued.
ln -sf /dev/null /etc/systemd/system/systemd-firstboot.service
ln -sf /dev/null /etc/systemd/system/getty@tty1.service
log "masked systemd-firstboot and getty@tty1"

# Belt and braces: also stop getty.target from pulling tty1 in.
ln -sf /dev/null /etc/systemd/system/getty.target.wants/getty@tty1.service 2>/dev/null || true

log "live boot pipeline configured"

