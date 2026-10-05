# Lucy OS Development Guide

This file contains project-specific rules, build commands, and verification steps for Lucy OS development.

## Build Commands

### Core Agent

```bash
# Build Rust extension and Python package
cd src/core/python
maturin build --release

# Install in development mode
maturin develop

# Run tests
cd ../rust
cargo test

cd ../python
pytest
```

**Script:**
```bash
./scripts/build-core.sh
```

### Desktop UI

```bash
# Install dependencies
cd src/shell
npm install

# Development mode with hot reload
npm run tauri dev

# Production build
npm run tauri build

# Build for Linux specifically
npm run tauri build --target x86_64-unknown-linux-gnu
```

**Script:**
```bash
./scripts/build-shell.sh
```

### Complete ISO

```bash
# Build entire ISO (requires root and Arch Linux)
sudo ./scripts/build-iso.sh
```

**Prerequisites:**
- Arch Linux environment
- archiso installed
- Root privileges
- ~25GB free disk space (increased due to Ollama)

**Alternative: Docker Build**
```bash
./scripts/build-docker.sh
```

**Alternative: GitHub Actions**
Push to GitHub to trigger automated builds.

### WSL Setup

```bash
# Initial environment setup
./scripts/setup-wsl.sh
```

## Verification Steps

### After Building Core Agent

1. **Check Rust compilation:**
   ```bash
   cd src/core/rust
   cargo check
   cargo test
   ```

2. **Check Python import:**
   ```bash
   cd src/core/python
   python -c "import lucy_core; print('OK')"
   ```

3. **Test daemon:**
   ```bash
   python -c "from lucy_agent import LucyDaemon; print('OK')"
   ```

4. **Test auto-healing module:**
   ```bash
   python -c "from lucy_agent import AutoHealDaemon; print('OK')"
   ```

5. **Test ai-shell wrapper:**
   ```bash
   python3 -m lucy_agent.shell_wrapper "show disk usage"
   # Should output: df -h
   ```

6. **Verify ai-shell executable:**
   ```bash
   ls -l src/configs/airootfs/usr/local/bin/ai-shell
   # Should be executable
   ```

7. **Verify lucyfetch executable:**
   ```bash
   ls -l src/configs/airootfs/usr/local/bin/lucyfetch
   # Should be executable
   ```

8. **Verify skel directory:**
   ```bash
   ls -la src/configs/airootfs/etc/skel/
   # Should contain .bashrc
   ```

### After Building Desktop UI

1. **Check TypeScript compilation:**
   ```bash
   cd src/shell
   npx tsc --noEmit
   ```

2. **Check Rust compilation:**
   ```bash
   cd src-tauri
   cargo check
   ```

3. **Test dev server:**
   ```bash
   npm run tauri dev
   # Verify UI loads correctly
   # Verify splash screen appears
   ```

4. **Verify splash screen component:**
   ```bash
   # Check that Splash.tsx exists in src/components/
   ls src/shell/src/components/Splash.tsx
   ```

### After Building ISO

1. **Validate archiso profile:**
   ```bash
   sudo mkarchiso -v src/configs
   ```

2. **Test in QEMU:**
   ```bash
   qemu-system-x86_64 \
     -m 4G \
     -smp 2 \
     -enable-kvm \
     -boot d \
     -cdrom dist/lucy-os-0.1.0-x86_64.iso
   ```

3. **Verify ISO boots**
4. **Check agent daemon starts**
5. **Verify Ollama service starts**
6. **Verify auto-heal service starts**
7. **Verify desktop UI launches**
8. **Check MOTD displays Dinkinesh story**
9. **Verify wallpaper is set**

### Testing Ollama Integration

1. **Check Ollama service:**
   ```bash
   systemctl status ollama
   ```

2. **Test Ollama endpoint:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. **Test Ollama fallback:**
   ```bash
   # Disconnect network
   # Run agent with offline test
   python -c "from lucy_agent import CommandTranslator; t = CommandTranslator(config={'fallback_to_ollama': True}); print(t.translate('list files'))"
   ```

### Testing Auto-Healing

1. **Check auto-heal service:**
   ```bash
   systemctl status lucy-autoheal
   ```

2. **Test threshold checking:**
   ```bash
   cd src/core/rust
   cargo test check_memory_threshold
   cargo test check_disk_threshold
   ```

3. **Test cache clearing:**
   ```bash
   python -c "import lucy_core; m = lucy_core.SystemMonitor(); print(m.clear_system_cache())"
   ```

4. **Test log rotation:**
   ```bash
   python -c "import lucy_core; m = lucy_core.SystemMonitor(); print(m.rotate_logs('/var/log/lucy', 100))"
   ```

### Testing AI-Native Terminal

1. **Test ai-shell:**
   ```bash
   src/configs/airootfs/usr/local/bin/ai-shell
   # Try: "list files"
   # Should translate to "ls -la"
   # Confirm execution
   ```

2. **Test shell wrapper:**
   ```bash
   python3 -m lucy_agent.shell_wrapper "show disk usage"
   # Should output: "df -h"
   ```

3. **Test fallback:**
   ```bash
   # Enter untranslatable command
   # Should execute directly
   ```

### Testing lucyfetch

1. **Verify lucyfetch script:**
   ```bash
   ls -l src/configs/airootfs/usr/local/bin/lucyfetch
   # Should be executable (-rwxr-xr-x)
   ```

2. **Test lucyfetch execution** (requires Python environment):
   ```bash
   python3 src/configs/airootfs/usr/local/bin/lucyfetch
   # Should display ASCII logo and system info
   ```

3. **Verify .bashrc configuration:**
   ```bash
   cat src/configs/airootfs/etc/skel/.bashrc
   # Should contain lucyfetch invocation
   ```

4. **Test psutil dependency:**
   ```bash
   grep "python-psutil" src/configs/packages.x86_64
   # Should find the package
   ```

### Docker Build Verification

1. **Check Docker availability:**
   ```bash
   docker --version
   docker info
   ```

2. **Validate build environment:**
   ```bash
   ./scripts/validate-build.sh
   ```

3. **Build Docker image:**
   ```bash
   docker build -t lucy-os-builder .
   ```

4. **Test Docker build:**
   ```bash
   ./scripts/build-docker.sh
   ```

5. **Verify ISO output:**
   ```bash
   ls -lh dist/*.iso
   ```

### Environment Validation

Before building, validate your environment:
```bash
./scripts/validate-build.sh
```

This checks:
- Arch Linux environment
- Required tools (archiso, Rust, Python, Node.js)
- Project files
- Disk space
- Docker availability (as alternative)

## Development Workflow

### Adding New Commands

1. **Rust layer** (`src/core/rust/src/command.rs`):
   - Add to `allowed_commands` whitelist
   - Implement safety checks if needed

2. **Python layer** (`src/core/python/lucy_agent/safety.py`):
   - Add to `safe_commands` or `dangerous_patterns`
   - Implement risk assessment

3. **NLP layer** (`src/core/python/lucy_agent/nlp.py`):
   - Add translation pattern
   - Test translation

4. **Tauri layer** (`src/shell/src-tauri/src/main.rs`):
   - Add command if needed for UI

### Adding New UI Components

1. Create component in `src/shell/src/components/`
2. Add Tauri command in `src-tauri/src/main.rs` if needed
3. Integrate in `src/shell/src/App.tsx`
4. Add navigation tab

### v0.2.0 Features

#### Welcome App (lucy-intro)

First-boot glassmorphism intro that plays `lucy-intro.mp4` (obsidian + gold
theme). Shown once, tracked via the webview's `localStorage`
(`lucy.welcomed`). Falls back to a Dinknesh history slideshow when the
media asset is absent.

- Component: `src/shell/src/components/Welcome.tsx`
- Media asset: `src/shell/public/media/lucy-intro.mp4`
- Integrated in `src/shell/src/App.tsx` (after the splash)

#### Live Wallpaper Service

Loops `lucy-wallpaper-live.mp4` as the X11 desktop background.

- Engine: `src/configs/airootfs/usr/local/bin/lucy-wallpaper`
- Video asset: `src/configs/airootfs/usr/share/lucy/lucy-wallpaper-live.mp4`
- systemd user service: `src/configs/airootfs/etc/systemd/user/lucy-wallpaper.service`
- XDG autostart: `src/configs/airootfs/etc/xdg/autostart/lucy-wallpaper.desktop`
- Uses `xwinwrap` + `mpv` when `xwinwrap` is installed (AUR); otherwise an
  `mpv` desktop-window fallback, then the static Openbox wallpaper.

#### USB Persistence

Live-USB persistence via the archiso `cow_label` overlay mechanism. A
partition labeled `LUCY_PERSIST` (ext4) is used as a copy-on-write store for
the whole root filesystem.

- Build host: `sudo ./scripts/build-iso.sh --usb /dev/sdX` (writes the ISO,
  then creates the `LUCY_PERSIST` partition in the trailing free space)
- Live system: `sudo lucy-usb-persist` (auto-detects the boot medium)
- Boot entries: `syslinux.cfg` (`LABEL persistent`) and
  `efiboot/loader/entries/lucy-persistent-x86_64.conf` pass
  `cow_label=LUCY_PERSIST cow_persistent=P`

### v0.2.0 Glassmorphic Shell, Apps, VPN

#### Launch animation (lucy-launch.mp4)

10-second full-screen boot/login animation. Single source of truth is
`src/shell/public/media/lucy-launch.mp4`; `build-iso.sh` Step 3 syncs it
into `airootfs/usr/share/lucy/lucy-launch.mp4` (the airootfs copy is NOT
committed, to avoid duplicating the 24 MB blob).

- Player: `airootfs/usr/local/bin/lucy-launch` (mpv fullscreen)
- Autostart: `airootfs/etc/xdg/autostart/lucy-launch.desktop`
- Post-installer transition: `airootfs/usr/local/bin/lucy-installer`
  launches Calamares, then plays the animation into the desktop
- Also selectable as a live wallpaper in the Control Center

#### Glassmorphic shell (Dock, TopBar, Control Center, Flow)

- `src/shell/src/components/Dock.tsx` — bottom floating dock (browser,
  files, terminal, media, hub, settings)
- `src/shell/src/components/TopBar.tsx` — top status bar with clock and
  Wi-Fi/Bluetooth/Audio/VPN toggles
- `src/shell/src/components/ControlCenter.tsx` — quick toggles, wallpaper
  switcher (live / launch / static), theme picker
- `src/shell/src/components/Flow.tsx` — Lucy Flow automation hub
  (one-click offline tasks via the `execute_command` Tauri backend)
- `src/shell/src/shell.css` — glassmorphic styles (blur backdrops,
  obsidian + gold)
- Backend: `launch_app` + `system_action` Tauri commands in
  `src-tauri/src/lib.rs`

#### App suite and VPN

Packages in `src/configs/packages.x86_64`: `chromium`, `alacritty`,
`thunar` (+ plugins, `gvfs`, `tumbler`), `mpv`, `bluez`, `sing-box`,
`parted`, `xdotool`, `xorg-xprop`.

- `sing-box` VPN engine with China-friendly routing + Clash API
  (`airootfs/etc/sing-box/config.json`); toggle via TopBar/Control Center
- Lucy dark start page: `airootfs/usr/share/lucy/start-page.html`
- Lucy Hub launcher: `airootfs/usr/local/bin/lucy-shell` +
  `lucy-shell.desktop`
- Performance: `airootfs/etc/sysctl.d/99-lucy-performance.conf`
- Calamares branding (Dinknesh slideshow): `airootfs/etc/calamares/`
  (the `calamares` package itself is AUR-only, so it is NOT in
  `packages.x86_64`; install from AUR to enable the graphical installer)

### v0.3.0 "Evolution Edition"

Four pillars. **English is the default throughout** — every localization
feature is opt-in and reverting it leaves the system fully usable in English.

#### Week 1: hardware detection and model selection

`src/core/python/lucy_agent/models.py` profiles the machine at startup and
selects a fitting model so the AI never oversubscribes the hardware.

- `HardwareProfile` (cores/RAM/VRAM/backend), `ModelSpec` (size/quant/context)
- `init()`, `get_profile()`, `get_model_spec()`, `is_light_profile()`,
  `is_high_profile()`

#### Week 2: offline semantic file indexer

`src/core/python/lucy_agent/search.py` — offline semantic file search.

- `SemanticIndexer`, `GGUFEmbedder` (4-bit GGUF), `HashEmbedder` fallback
- `VectorStore` (ChromaDB, JSONL fallback), `chunk_text()`, `search_files()`
- `throttle()` enforces the max-50% CPU budget (5% target, 50% pause)
- Daemon: `search_daemon.py` +
  `airootfs/etc/systemd/system/lucy-indexer.service`
- Shell: `search_files` Tauri command
- AI performance rules: max 50% CPU/GPU, on-demand model load, 3-minute idle
  auto-unload, 4-bit quantized GGUF only

#### Week 3: self-healing and instant rollback

- `snapshot.py`: `SnapshotManager` (Btrfs/timeshift), `BootGuard`,
  `create_snapshot()`, `trigger_rollback()`, `get_boot_status()`
- `autoheal.py`: journal fault watchdog, `record_boot()`, `mark_healthy()`,
  `handle_faults()`; `_load_config` parses both INI (`agent.conf`) and JSON
- Btrfs cannot swap a live `/`: `trigger_rollback()` writes
  `/var/lib/lucy/rollback.request`; `lucy-rollback.service`
  (`DefaultDependencies=no`, before `graphical-session-pre`) applies it early
  in boot with `btrfs subvolume set-default`
- Keys: `rollback_enabled`, `snapshot_on_boot`, `journal_scan_interval`,
  `rollback_fail_threshold` under `[auto_healing]` in `agent.conf`
- Shell: `get_boot_status`, `trigger_rollback`, `create_snapshot`

#### Week 4: optional Amharic/Ge'ez localization

All opt-in. English (US) stays the default system language and layout.

| Feature | Entry point | Wiring |
| --- | --- | --- |
| Keyboard toggle | `usr/local/bin/lucy-keyboard` | TopBar indicator, **Super+Space** in `etc/xdg/openbox/lxde-rc.xml`, Settings |
| Locale pack | `usr/local/bin/lucy-locale` | Settings → Region & Language; writes `/etc/locale.gen` + `locale-gen` |
| Heritage theme | `usr/local/bin/lucy-theme` | Settings → Appearance; `data-theme="heritage"` in `shell.css` |
| Multi-language AI | `parse_language_flag()` in `nlp.py` | `/lang:am` and friends; `ai_language` under `[ai]` in `agent.conf` |

- Ethiopic layout: staged at
  `airootfs/usr/share/lucy/overlay/xkb/symbols/lucy-amharic`, installed into
  `/usr/share/X11/xkb/symbols/` by `customize_airootfs.sh`
  (26 keys, second vowel orders on Shift, `grp:alt_shift_toggle`)
- Shell RPC: `keyboard_layout`, `system_locale`, `heritage_theme`,
  `get_localization_status`
- State persisted in `$XDG_CONFIG_HOME/lucy/` as `keyboard`, `locale`, `theme`
- `Super+Space` in `lxde-rc.xml` must `Execute` `lucy-keyboard toggle` —
  Openbox's own `Toggle` action switches windows, not layouts

**Never** change the default language automatically: `lucy-locale remove`
only resets the state file, and English remains active.

### v0.4.0 Phase 1: essential apps and Flatpak

#### Flatpak / Flathub

- Packages: `flatpak`, `xdg-desktop-portal`, `xdg-desktop-portal-gtk`,
  `xdg-user-dirs` (added to `packages.x86_64`)
- First-boot: `airootfs/etc/systemd/system/lucy-flatpak-init.service` runs
  `usr/local/bin/lucy-flatpak-init`
- Idempotent (`--if-not-exists`), marker at
  `/var/lib/lucy/flatpak-init.done`, never fails the boot when offline.
  `LUCY_STATE_DIR` overrides the marker location for testing.
- Manual run: `lucy-flatpak-init [--status|--force]`

#### Core pre-installed apps

Native (`extra`) so they work offline with no Flatpak: `firefox`, `code`,
`celluloid`, `mpv`, `alacritty`, `thunar`, `chromium`.

Hardware acceleration:

- `airootfs/usr/share/lucy/overlay/firefox/distribution/policies.json` —
  WebRender + VA-API + DMA-BUF defaults, installed to
  `/usr/lib/firefox/distribution/` by `customize_airootfs.sh` (this is the
  Mozilla-sanctioned path; do not use the older `mozilla.cfg` autoconfig)
- `airootfs/usr/share/lucy/overlay/chromium-flags.conf` — installed to
  `/etc/chromium-flags.conf` by the hook; Arch's chromium launcher sources it
  automatically, and per-user overrides go in `~/.config/chromium-flags.conf`
- VA-API packages: `libva`, `libva-utils`, `libvdpau`, `intel-media-driver`.
  NOTE: `libva-mesa-driver` and `mesa-vdpau` were merged into `mesa` and no
  longer exist as separate packages — do not re-add them.

#### App manager

- Module: `src/core/python/lucy_agent/appstore.py` (stdlib only)
- Catalog: `airootfs/etc/lucy/apps.json` (schema: `version`, `remote_name`,
  `remote_url`, `apps[]` with `id`, `name`, `category`, `kind`
  (`flatpak`|`native`), `core`, `native_package`)
- CLI: `airootfs/usr/local/bin/lucy-app-manager` — tries `python3` then
  `python`, picking the first interpreter that can import the module, then
  falls back to running `appstore.py` directly. `--json` for machine output.
- Tauri RPC: `app_catalog`, `app_search`, `app_install`, `app_remove`,
  `app_installed`, `app_status`, `app_flathub_setup`
- All system access goes through an injectable `runner`, so tests assert exact
  command lines without a real Flatpak.

#### Lazy package exports (important)

`lucy_agent/__init__.py` resolves exports lazily via PEP 562 `__getattr__`.
Do **not** add eager imports there — it would force `pydantic` etc. to load for
the stdlib-only `appstore`, breaking `lucy-app-manager` on minimal systems.
`tests/test_package_exports.py` guards this with a pydantic-free subprocess.

#### Verification

```bash
python scripts/verify-app-configs.py   # config/schema/unit checks (CI-safe)
bash   scripts/test-app-manager.sh     # functional smoke test (fake flatpak)
cd src/core/python && pytest tests
```

`scripts/verify-app-configs.py` is the quick gate after editing
`apps.json`, `packages.x86_64` or the browser configs.

#### CRITICAL: the airootfs overlay and pacman file conflicts

archiso copies `airootfs/` into the build root **before** pacstrap, then runs
`airootfs/root/customize_airootfs.sh` in the chroot afterwards
(`_make_custom_airootfs` -> `_make_packages` -> `_make_customize_airootfs`).

So **never place a file under a directory owned by a package you install**.
Doing so makes pacman abort:

```
error: failed to commit transaction (conflicting files)
xkeyboard-config: /usr/share/X11/xkb exists in filesystem
```

This exact mistake shipped in the Week 4 commit and broke CI. It was missed
because the push was verified but not the CI conclusion — always check the
check-run result, not just the ref update.

Instead, stage the file under `airootfs/usr/share/lucy/overlay/` and install
it from `customize_airootfs.sh`. Current staged files:

| Staged | Installed to | Owning package |
| --- | --- | --- |
| `overlay/xkb/symbols/lucy-amharic` | `/usr/share/X11/xkb/symbols/` | `xkeyboard-config` |
| `overlay/firefox/distribution/policies.json` | `/usr/lib/firefox/distribution/` | `firefox` |
| `overlay/chromium-flags.conf` | `/etc/chromium-flags.conf` | `chromium` |

`scripts/verify-app-configs.py` has a `check_overlay_hook()` guard that fails
if any collision-prone path reappears, and `lucy-keyboard` self-heals at
runtime by copying the staged layout if it is missing.

Safe locations (no package ships these): `/etc/lucy/`, `/usr/local/bin/`,
`/usr/share/lucy/`, `/etc/systemd/system/lucy-*.service`.

Note: `customize_airootfs.sh` is *deprecated* in archiso but still executed;
it is deleted after running so it never ships in the ISO.

### CRITICAL: the initramfs must contain the archiso hook

An archiso ISO boots with **no `root=` kernel parameter**. The `archiso`
initcpio hook finds the live medium and `archiso_loop_mnt` loop-mounts the
airootfs squashfs. Without them, boot dies at:

```
[FAILED] Failed to start Switch Root
You are in emergency mode
```

Required (both present in this profile):

1. `airootfs/etc/mkinitcpio.conf.d/archiso.conf` (drop-in for
   `/etc/mkinitcpio.conf`):

   ```
   HOOKS=(base udev modconf kms archiso archiso_loop_mnt block filesystems keyboard)
   ```

   `archiso`/`archiso_loop_mnt` must precede `block` and `filesystems`.
   The upstream `archiso_pxe_*` hooks are omitted on purpose: they need
   `mkinitcpio-nfs-utils`/`nbd`, which are not installed, and a missing hook
   makes mkinitcpio fail.

2. `mkinitcpio-archiso` in `packages.x86_64`. The `archiso` package does
   **not** depend on it — it must be listed explicitly.

archiso does not run mkinitcpio itself; it copies `/boot` from the build root
onto the ISO. `customize_airootfs.sh` therefore runs `mkinitcpio -P` and then
asserts `hooks/archiso` is inside every `/boot/initramfs-*.img`, failing the
build otherwise. Do not remove that check — it is what makes this class of
boot failure impossible to ship silently.

Bootloader label: entries use `%ARCHISO_LABEL%` / `%INSTALL_DIR%` /
`%ARCHISO_UUID%`, substituted by archiso from `profiledef.sh`
(`iso_label="LUCYOS"`). Never hardcode the label. Do **not** add
`airootfs/etc/fstab` — a live ISO must not have static disk UUID mounts.

`scripts/verify-app-configs.py::check_boot_config()` guards all of this.

### v0.4.0 Phase 2: palette, app store, installer

#### Super+Space ownership

`Super+Space` belongs to the **command palette** and nothing else.

- Registered as a real global shortcut in `src-tauri/src/lib.rs`
  (`tauri-plugin-global-shortcut`, `Modifiers::SUPER` + `Code::Space`), so it
  fires over any application, not just when the shell has focus.
- Rust emits `lucy://toggle-palette`; `App.tsx` listens and toggles. The
  event name is defined once in Rust (`PALETTE_EVENT`) and
  `verify-app-configs.py` fails if the React side drifts from it.
- The Amharic layout toggle moved to **`Super+Shift+Space`** in
  `etc/xdg/openbox/lxde-rc.xml`. Do **not** re-bind `Super+space` in openbox:
  two owners of the key fight, and the verifier fails the build.
- A failed registration is only a warning; the in-app `keydown` handler is
  the fallback.

Palette: `src/shell/src/components/CommandPalette.tsx` (app launch, actions,
settings toggles, debounced offline semantic search, `ai_translate` fallback).
Store: `src/shell/src/components/AppStore.tsx` (all 7 appstore RPCs, with
graceful degradation when Flatpak is missing).

#### Installer: calamares is AUR-only

**Never add `calamares` to `packages.x86_64`.** It is not in `[core]`/`[extra]`
(verified against the Arch package API), so pacstrap aborts with
`target not found` and the entire ISO build fails.

- `customize_airootfs.sh` probes it best-effort with `pacman -Si calamares`
  and installs it only if present. Truthful, and it cannot break the build.
- `archinstall` is the shipped, working installer (plus `btrfs-progs`,
  `dosfstools`, `efibootmgr`).
- `lucy-installer` prefers `calamares`, falls back to `archinstall`, then
  prints AUR instructions.

Calamares config lives in `airootfs/etc/calamares/`: `settings.conf`,
`branding/lucy/` and `modules/{partition,mount,unpackfs,bootloader,
initcpiocfg,shellprocess-postinstall}.conf`.

Two details that matter:

1. `partition.conf` creates the `/.snapshots` Btrfs subvolume — the Week 3
   rollback engine (`lucy_agent.snapshot`, `lucy-rollback`) requires it.
2. `shellprocess-postinstall.conf` uses `dontChroot: true` (so `${ROOT}` paths
   actually resolve) and **deletes `/etc/mkinitcpio.conf.d/archiso.conf` from
   the target before rebuilding its initramfs**. The installed system has no
   live medium: leaving the `archiso` hook in HOOKS makes it unbootable with
   the same "Failed to start Switch Root" error the live ISO just had.

The live desktop shortcut is `etc/skel/Desktop/calamares.desktop`
("Install Lucy OS"); the postinstall removes it from the installed user.

### v0.4.0: live boot pipeline (autologin, DM, plymouth)

The medium must boot straight to the desktop; never to a TTY login prompt.

Everything is wired in `airootfs/root/customize_airootfs.sh`:

- creates the live user **`lucy`** (`useradd -m`, empty password, NOPASSWD
  sudo in `/etc/sudoers.d/10-lucy`). `-m` copies `/etc/skel`, which is how
  the desktop shortcut and GTK settings appear.
- `ln -sf /usr/lib/systemd/system/lightdm.service /etc/systemd/system/display-manager.service`
- `ln -sf /usr/lib/systemd/system/graphical.target /etc/systemd/system/default.target`
- masks `systemd-firstboot.service` and `getty@tty1.service` to `/dev/null`

**Why symlinks are created in the hook and not committed:** this project is
developed on Windows, where Git stores symlinks as plain files. A committed
"symlink" would land in the ISO as a text file, `display-manager.service`
would not be a symlink, and nothing would start X — the exact bug reported.
Never commit these as repo symlinks.

Config (package-owned paths are staged under `usr/share/lucy/overlay/` and
installed **after pacstrap** by the hook — see the next subsection):

- `usr/share/lucy/overlay/lightdm/lightdm.conf` → `/etc/lightdm/lightdm.conf`
  — `autologin-user=lucy`, `autologin-user-timeout=0`, `autologin-session=lucy`
- `usr/share/lucy/overlay/lightdm/lightdm-gtk-greeter.conf` →
  `/etc/lightdm/lightdm-gtk-greeter.conf` — exactly one `[greeter]` section
- `usr/share/lucy/overlay/plymouth/plymouthd.conf` →
  `/etc/plymouth/plymouthd.conf` — `Theme=lucy`, with the theme staged at
  `usr/share/plymouth/themes/lucy/`. The logo is copied from
  `/usr/share/pixmaps/lucy.png` by the hook (single source of truth).
- `usr/share/xsessions/lucy.desktop` → `/usr/local/bin/lucy-session`
  (startlxde, falling back to openbox-session)
- `etc/skel/.config/gtk-3.0/settings.ini` — Adwaita-dark + Papirus-Dark,
  names that are guaranteed present.

#### Package-owned config paths MUST be installed after pacstrap

`/etc/lightdm/lightdm.conf` (lightdm), `/etc/lightdm/lightdm-gtk-greeter.conf`
(lightdm-gtk-greeter) and `/etc/plymouth/plymouthd.conf` (plymouth) are all
**shipped by their packages**. The airootfs overlay is copied before pacstrap,
so a copy placed there is replaced by the package default when the package
installs.

This is not theoretical — it silently discarded `autologin-user=lucy`, so
LightDM showed a greeter and asked for a password.

Stage such files under `usr/share/lucy/overlay/` (a path no package owns) and
have `customize_airootfs.sh` install them into `/etc/...` after pacstrap.
`verify-app-configs.py` fails if any of the three reappears under
`airootfs/etc/`.

Plymouth must never block boot. If it cannot draw, it logs and startup
continues; `plymouth.enable=0` disables it. `tty2`–`tty6` remain available.

Initramfs HOOKS:

```
base udev plymouth modconf kms archiso archiso_loop_mnt block filesystems keyboard
```

`plymouth` goes immediately after `udev` and **before** `kms` (kms hands the
framebuffer over). Never reorder those, and never let archiso hooks move after
`block` — `verify-app-configs.py::check_live_boot()` enforces both.

Runtime verification: **`lucy-boot-check`** (shipped in
`usr/local/bin/`) checks the target, display manager, X server, logind session
for `lucy`, autologin settings, masked prompts and the Plymouth theme.
It cannot be exercised in CI (no VM), so it is written to be run on the live
medium or from a rescue TTY.

#### Why autologin can still prompt for a password

Setting `autologin-user` alone is **not** sufficient. LightDM authenticates
through the `lightdm-autologin` PAM stack, whose first rule is normally:

```
auth  sufficient  pam_succeed_if.so user ingroup autologin
```

If the user is not in that group the rule fails, PAM falls through to
`system-login`, and the greeter asks for a password — even though
`autologin-user=lucy` is correct. This is exactly what happened once.

`customize_airootfs.sh` therefore:

- creates the `autologin` group and adds `lucy` to it
- **reads the group name out of the installed PAM file** rather than assuming
  it, because some distributions use `nopasswdlogin` instead
- injects a `pam_succeed_if ... ingroup autologin` rule only if the stack has
  none at all (never duplicates an existing one)

`lucy-boot-check` verifies the group membership and every group named by the
PAM rule, so this is diagnosable from the live system.

Theme/font packages: only official repos — `papirus-icon-theme`,
`deepin-icon-theme`, `deepin-gtk-theme`, `materia-gtk-theme`,
`gnome-themes-extra`, `ttf-dejavu`, `gnu-free-fonts` (Ethiopic coverage).
`fluent-gtk-theme`, `arc-gtk-theme`, `numix-icon-theme`, `qogir-icon-theme`
are AUR-only and must never be listed.

### Modifying Archiso Profile

1. Edit `src/configs/profiledef.sh` for metadata
2. Edit `src/configs/packages.x86_64` for packages
3. Add files to `src/configs/airootfs/`
4. Test with `sudo mkarchiso -v src/configs`

### Configuring Ollama

1. Edit `src/configs/airootfs/etc/lucy/agent.conf`:
   ```ini
   [ai]
   fallback_to_ollama = true
   ollama_model = llama2
   ollama_endpoint = http://localhost:11434
   ```

2. Add ollama to `src/configs/packages.x86_64`

3. Test service startup:
   ```bash
   systemctl start ollama
   systemctl status ollama
   ```

### Configuring Auto-Healing

1. Edit `src/configs/airootfs/etc/lucy/agent.conf`:
   ```ini
   [auto_healing]
   enabled = true
   memory_threshold = 85
   disk_threshold = 90
   clear_cache = true
   rotate_logs = true
   max_log_size = 100M
   check_interval = 300
   ```

2. Enable service:
   ```bash
   systemctl enable lucy-autoheal
   systemctl start lucy-autoheal
   ```

3. Monitor logs:
   ```bash
   journalctl -u lucy-autoheal -f
   ```

## Code Conventions

### Rust

- Use `cargo fmt` for formatting
- Use `cargo clippy` for linting
- Follow Rust API guidelines
- Document public APIs with `///`

### Python

- Follow PEP 8 style guide
- Use type hints
- Document functions with docstrings
- Use `black` for formatting
- Use `ruff` for linting

### TypeScript/React

- Use functional components with hooks
- Use TypeScript strict mode
- Inline styles for MVP (no CSS framework yet)
- Keep components small and focused

### Shell Scripts

- Use `set -e` for error handling
- Use meaningful variable names
- Comment complex logic
- Make scripts executable with `chmod +x`

## Testing Strategy

### Unit Tests

**Rust:**
```bash
cd src/core/rust
cargo test
```

**Python:**
```bash
cd src/core/python
pytest
```

### Integration Tests

Test Rust-Python FFI:
```bash
cd src/core/python
python -c "import lucy_core; print(lucy_core.__version__)"
```

Test Tauri commands:
```bash
cd src/shell
npm run tauri dev
# Test each command from UI
```

### System Tests

Test ISO boot in QEMU:
```bash
qemu-system-x86_64 -m 4G -boot d -cdrom dist/lucy-os-0.1.0-x86_64.iso
```

## Troubleshooting

### Common Issues

**Rust not found:**
```bash
source "$HOME/.cargo/env"
```

**maturin build fails:**
```bash
pip install --upgrade maturin
```

**Tauri build fails:**
```bash
# Install webkit2gtk
sudo pacman -S webkit2gtk gtk3
```

**archiso permission denied:**
```bash
sudo ./scripts/build-iso.sh
```

**ISO build out of space:**
```bash
rm -rf work/
```

**Not running in Arch Linux:**
```bash
# Use Docker instead
./scripts/build-docker.sh

# Or install Arch Linux WSL2
# See docs/wsl-build-guide.md
```

**Docker not available:**
```bash
# Install Docker from https://docs.docker.com/get-docker/
# Or use GitHub Actions for automated builds
```

**archiso not found in WSL2:**
```bash
# WSL2 archiso may have limitations
# Use Docker build instead: ./scripts/build-docker.sh
```

### Getting Help

- Check logs in `/var/log/lucy/`
- Enable verbose builds with `-v` flag
- Check GitHub Issues
- Review documentation in `docs/`

## Project Structure Notes

### Module Dependencies

- **Core Agent**: No external dependencies (self-contained)
- **Desktop UI**: Depends on Core Agent (via IPC)
- **Archiso**: Depends on both Core Agent and Desktop UI

### Build Order

1. Core Agent (Rust + Python)
2. Desktop UI (Tauri)
3. ISO (Archiso with injected artifacts)

### File Locations

- **Source**: `src/`
- **Build artifacts**: `target/`, `dist/`
- **Work directory**: `work/` (archiso)
- **Logs**: `/var/log/lucy/` (in ISO)

## Security Guidelines

### Command Safety

- Always validate commands before execution
- Use whitelist approach for allowed commands
- Require confirmation for destructive operations
- Log all command executions

### Systemd Service

- Run as unprivileged user when possible
- Use security hardening options
- Restrict file system access
- Enable SELinux/AppArmor if available

### API Security

- Implement rate limiting
- Use authentication for IPC
- Validate all inputs
- Sanitize outputs

## Performance Guidelines

### Rust Components

- Use async I/O for blocking operations
- Minimize allocations in hot paths
- Use efficient data structures
- Profile with `cargo flamegraph`

### Python Components

- Use async/await for I/O operations
- Cache expensive computations
- Use connection pooling
- Profile with `cProfile`

### UI Components

- Debounce system updates
- Use virtual scrolling for lists
- Lazy load components
- Profile with React DevTools

## Release Process

1. Update version numbers in:
   - `src/core/rust/Cargo.toml`
   - `src/core/python/pyproject.toml`
   - `src/shell/package.json`
   - `src/shell/src-tauri/Cargo.toml`
   - `src/configs/profiledef.sh`

2. Update CHANGELOG.md

3. Run full build:
   ```bash
   ./scripts/build-core.sh
   ./scripts/build-shell.sh
   sudo ./scripts/build-iso.sh
   ```

4. Test ISO in QEMU

5. Tag release:
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```

6. Upload ISO to release

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

### Pull Request Checklist

- [ ] Code follows project conventions
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Commit messages are clear

## Additional Resources

- [Arch Wiki](https://wiki.archlinux.org/)
- [PyO3 Documentation](https://pyo3.rs/)
- [Tauri Documentation](https://tauri.app/)
- [React Documentation](https://react.dev/)
- [Rust Book](https://doc.rust-lang.org/book/)
