# Lucy OS

An advanced, AI-native Linux distribution named after Lucy (Dinqnesh) from Ethiopia.

![Lucy OS Banner](docs/assets/banner.jpg)

## Vision

Lucy OS is a Linux distribution where artificial intelligence is integrated at the core, providing a natural language interface for system management and operations.

**Rooted in Origins, Powered by AI**

## Lucy (Dinkinesh) — 3.2 Million Years of Intelligence

Discovered in 1974 at Hadar, Afar, Ethiopia, Lucy (Amharic: ድንቅነሽ, meaning "you are marvelous") is one of the oldest and most complete hominid fossils ever found. She walked upright on two legs, marking a pivotal moment in the evolution of human intelligence.

Just as Lucy represents the dawn of human cognition, Lucy OS represents the dawn of AI-native computing — where artificial intelligence is woven into the fabric of the operating system itself.

## Architecture

- **Base OS**: Arch Linux (archiso-based)
- **Core AI Agent**: Hybrid Python+Rust daemon (PyO3/maturin)
- **Desktop UI**: Tauri v2 + React 19 + TypeScript
- **ISO Builder**: Automated archiso scripts
- **Ollama Integration**: Local LLM support for offline AI
- **Auto-Healing**: System resource monitoring and automatic cleanup
- **Self-Healing & Rollback**: Journal fault watchdog + Btrfs snapshot rollback
- **Semantic Index**: Offline GGUF-embedding file search with CPU throttling
- **Localization**: Optional Amharic/Ge'ez keyboard, locale pack and theme

## Project Structure

```
lucy-os/
├── src/
│   ├── core/           # AI Agent Daemon (Python+Rust)
│   ├── shell/          # Desktop UI (Tauri)
│   └── configs/        # Arch ISO configurations
├── scripts/            # Build automation
├── docs/               # Documentation
└── AGENTS.md          # Development rules
```

## Development Environment

Recommended: Windows with WSL2 (Arch Linux)

See [docs/installation.md](docs/installation.md) for setup instructions.

## Build Methods

### Docker Build (Recommended)

The recommended way to build the ISO is using Docker, which provides a clean, reproducible Arch Linux environment:

```bash
./scripts/build-docker.sh
```

### GitHub Actions CI/CD

Automated builds are available via GitHub Actions. Push to trigger automatic builds.

### Native Arch Linux

For native builds, use Arch Linux WSL2 or a native Arch Linux installation:

```bash
# In Arch Linux WSL2
sudo ./scripts/build-iso.sh
```

See [docs/wsl-build-guide.md](docs/wsl-build-guide.md) for detailed WSL2 setup instructions.

## Quick Start

### Using Docker (Recommended)

```bash
# Build complete ISO in Docker
./scripts/build-docker.sh
```

### Using GitHub Actions

Push to GitHub to trigger automated builds. Download ISO from Actions artifacts.

### Using Native Arch Linux

```bash
# Set up WSL2 environment
./scripts/setup-wsl.sh

# Build core agent
./scripts/build-core.sh

# Build desktop UI
./scripts/build-shell.sh

# Build complete ISO (requires Arch Linux)
sudo ./scripts/build-iso.sh
```

## Components

### Core AI Agent
- Rust components for performance-critical operations (command safety, resource monitoring)
- Python components for AI logic and natural language processing
- PyO3 bindings for seamless integration
- **Ollama fallback**: Local LLM support when offline
- **Auto-healing**: Automatic cache clearing and log rotation

### Desktop UI
- Tauri v2 for lightweight, cross-platform desktop application
- React 19 + TypeScript for modern, type-safe frontend
- Chat interface for natural language interaction
- System resource monitoring dashboard
- **Splash screen**: Branded boot experience

### AI-Native Terminal
- **ai-shell**: Bash wrapper with natural language command translation
- User confirmation before execution
- Fallback to direct execution when translation fails
- Color-coded output

### System Information Tool
- **lucyfetch**: Custom CLI tool with Dinkinesh ASCII logo
- Displays system information (OS, Kernel, Uptime, Memory, Disk)
- Shows Ollama AI status (online/offline, loaded models)
- Automatically runs on terminal open
- Gold/Amber/Purple color theme matching Lucy OS branding

### ISO Builder
- Custom archiso profile for Lucy OS
- Automated build pipeline
- Bootable installation media
- **Branded wallpaper**: Ethiopian obsidian/gold theme

## Safety

The AI agent includes multi-layer safety validation:
- Rust-level command whitelist and validation
- Python-level semantic analysis
- User confirmation for destructive operations
- Configurable auto-healing thresholds

## New Features in v0.1.0

### Branding & Visual Identity
- Ethiopian heritage story in MOTD
- Custom splash screen with logo
- Branded desktop wallpaper
- Logo assets for UI integration

### Embedded Ollama
- Local LLM service for offline AI
- Automatic fallback when no internet
- Configurable model selection
- Systemd service integration

### Auto-Healing System
- Configurable RAM/Disk thresholds
- Automatic cache clearing
- Log rotation
- Background monitoring daemon

### AI-Native Terminal
- Natural language command translation
- User confirmation prompts
- Seamless fallback to direct execution
- Color-coded output

### System Information Tool
- **lucyfetch**: Custom CLI tool with Dinkinesh ASCII logo
- Displays system information (OS, Kernel, Uptime, Memory, Disk)
- Shows Ollama AI status (online/offline, loaded models)
- Automatically runs on terminal open
- Gold/Amber/Purple color theme matching Lucy OS branding

## v0.2.0 — Glassmorphic Shell

### Launch & Welcome Experience

The boot/login animation `lucy-launch.mp4` has a **single source of truth** at
`src/shell/public/media/lucy-launch.mp4`. `scripts/build-iso.sh` syncs it into
`airootfs/usr/share/lucy/` at build time, so the 24 MB blob is never duplicated
in git history.

It is wired in three places:

| Surface | Mechanism |
| --- | --- |
| Boot / login animation | `lucy-launch` (mpv fullscreen) via `etc/xdg/autostart/lucy-launch.desktop` |
| Post-installer transition | `lucy-installer` runs Calamares, then plays the animation into the desktop |
| Live wallpaper option | `ControlCenter` → Wallpaper → *Launch animation* |

A separate first-boot **Welcome App** plays `lucy-intro.mp4`, tracked via
`localStorage` (`lucy.welcomed`), and falls back to the Dinkinesh history
slideshow when the asset is missing.

### Glassmorphic Shell

- `Dock.tsx` — floating bottom dock (browser, files, terminal, media, hub, settings)
- `TopBar.tsx` — status bar with clock and Wi-Fi/Bluetooth/Audio/VPN/keyboard toggles
- `ControlCenter.tsx` — quick toggles, wallpaper switcher (live / launch / static), theme picker
- `Flow.tsx` — **Lucy Flow** automation hub, one-click offline tasks
- `shell.css` — blur backdrops over the obsidian + gold palette

### App Suite & VPN

Pre-installed from `packages.x86_64`: `chromium` (with the Lucy dark start
page), `alacritty`, `thunar` (+ `gvfs`, `tumbler`), `mpv`, `bluez`.

The VPN is **sing-box** (`[extra]`) with China-friendly routing:
`geoip-cn` / `geosite-geolocation-cn` go direct, `geosite-geolocation-!cn` is
proxied. The Clash API on `127.0.0.1:9090` backs the TopBar/Control Center
widget. Config lives at `airootfs/etc/sing-box/config.json`.

### USB Persistence

Live-USB persistence via archiso's `cow_label` overlay:

```bash
sudo ./scripts/build-iso.sh --usb /dev/sdX   # writes the ISO + LUCY_PERSIST partition
sudo lucy-usb-persist                        # on the live system
```

Both `syslinux.cfg` and `efiboot/loader/entries/lucy-persistent-x86_64.conf`
pass `cow_label=LUCY_PERSIST cow_persistent=P`.

## v0.3.0 — "Evolution Edition"

Four pillars, built over four verified sprints. **English is the default in
every one of them**; all localization features are strictly opt-in.

### Week 1 — Hardware Detection & Model Selection

`src/core/python/lucy_agent/models.py` profiles the machine at startup and
picks a model that fits, so the AI never oversubscribes the hardware.

- `HardwareProfile` — CPU cores, RAM, VRAM, backend (CPU/CUDA/Metal)
- `ModelSpec` — per-model size/quant/context metadata
- `init()` / `get_profile()` / `get_model_spec()` / `is_light_profile()` / `is_high_profile()`

### Week 2 — Offline Semantic File Indexer

`src/core/python/lucy_agent/search.py` gives Lucy semantic search over your
files with **no network calls**.

- `SemanticIndexer` — walks, chunks and embeds the filesystem
- `GGUFEmbedder` (4-bit quantized GGUF) with a dependency-free `HashEmbedder` fallback
- `VectorStore` — ChromaDB when present, JSONL fallback otherwise
- `throttle()` — enforces the **max 50% CPU** budget, pausing above it
- `search_files()` — top-k query entry point, exposed to the shell via the `search_files` Tauri command
- `search_daemon.py` + `lucy-indexer.service` for background indexing

On-demand model loading with a 3-minute idle auto-unload keeps the AI resident
only while it is actually being used.

### Week 3 — Self-Healing & Instant Rollback

Two complementary layers in `autoheal.py` and `snapshot.py`:

1. **Resource healing** — RAM/disk thresholds, cache clearing, log rotation
2. **Fault rollback** — a journal fault watchdog counts failed boots; past
   `rollback_fail_threshold`, the system boots the last known-good Btrfs subvolume

Btrfs cannot swap a live `/`, so `trigger_rollback()` writes
`/var/lib/lucy/rollback.request` and `lucy-rollback.service`
(`DefaultDependencies=no`, ordered `before graphical-session-pre`) completes
the swap with `btrfs subvolume set-default` early in boot.

Shell commands: `get_boot_status`, `trigger_rollback`, `create_snapshot`.
Knobs live under `[auto_healing]` in `etc/lucy/agent.conf`.

### Week 4 — Optional Amharic/Ge'ez Localization

Everything here is **opt-in**. English (US) remains the default system
language and layout, and switching any of it off leaves the system fully
usable in English.

| Feature | Where | Notes |
| --- | --- | --- |
| Keyboard layout toggle | TopBar (`EN` / `አማ`), **Super+Space**, Settings | `lucy-keyboard`, `setxkbmap us,lucy-amharic` |
| Locale pack installer | Settings → Region & Language | `lucy-locale`, generates `am_ET.UTF-8` |
| Heritage theme | Settings → Appearance | `lucy-theme`, warm gold + Ge'ez accent |
| Multi-language AI | Any AI request | `/lang:am`, `/lang:fr`, `/lang:ar`, `/lang:es`, `/lang:zh`, `/lang:ru` |

The Ethiopic layout is a bundled XKB symbols file
(`airootfs/usr/share/lucy/overlay/xkb/symbols/lucy-amharic`, installed into
`/usr/share/X11/xkb/symbols/` at build time) covering 26 keys across
three rows, with second vowel orders on Shift. All state is persisted under
`$XDG_CONFIG_HOME/lucy/` (`keyboard`, `locale`, `theme`).

The `/lang:` directive is parsed by `parse_language_flag()` in `nlp.py`. An
unsupported code is stripped and ignored rather than erroring, so a typo can
never break a command. Set a session default with `ai_language` under `[ai]`
in `agent.conf`.

## v0.4.0 — Phase 1: Essential Apps & Flatpak

### Flatpak & Flathub

`flatpak` plus the XDG desktop portals ship in the ISO, so sandboxed apps can
reach the desktop (file pickers, notifications, URL opening) under
openbox/LXDE:

```
flatpak
xdg-desktop-portal
xdg-desktop-portal-gtk
xdg-user-dirs
```

The Flathub remote is configured on first boot by
`lucy-flatpak-init.service` → `/usr/local/bin/lucy-flatpak-init`:

```bash
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

The service is deliberately forgiving: `--if-not-exists` makes it idempotent,
a success marker (`/var/lib/lucy/flatpak-init.done`) prevents needless work on
later boots, and an offline first boot simply retries next time without ever
failing the boot.

### Core pre-installed applications

| Role | App | Source |
| --- | --- | --- |
| Browser | Firefox (VA-API enabled), Chromium | `extra` |
| Editor | Code (OSS) | `extra` |
| Media | Celluloid, mpv | `extra` |
| Terminal | Alacritty (Lucy AI shell), lxterminal | `extra` |
| Files | Thunar | `extra` |
| Monitor | Lucy System Monitor | built in |

Hardware acceleration is enabled for both browsers:

- Firefox — `/usr/lib/firefox/distribution/policies.json` turns on WebRender,
  VA-API and DMA-BUF by default (users can still override).
- Chromium — `/etc/chromium-flags.conf` enables GPU rasterisation and VA-API
  decode.

### The airootfs overlay (important)

archiso copies `airootfs/` into the build root **before** pacstrap runs. Any
file placed directly under a package-owned directory therefore makes pacman
abort with a file conflict:

```
error: failed to commit transaction (conflicting files)
xkeyboard-config: /usr/share/X11/xkb exists in filesystem
```

Files that must live in such directories are staged under
`/usr/share/lucy/overlay/` (a path no package owns) and installed by
`airootfs/root/customize_airootfs.sh`, which archiso runs in the chroot after
the packages are in place:

| Staged at | Installed to |
| --- | --- |
| `overlay/xkb/symbols/lucy-amharic` | `/usr/share/X11/xkb/symbols/` |
| `overlay/firefox/distribution/policies.json` | `/usr/lib/firefox/distribution/` |
| `overlay/chromium-flags.conf` | `/etc/chromium-flags.conf` |

`scripts/verify-app-configs.py` fails if any file reappears under a
package-owned path in the airootfs.

Supporting VA-API packages: `libva`, `libva-utils`, `libvdpau`,
`intel-media-driver` (`mesa` already provides the Radeon VA-API driver).

### Lucy App Manager

A lightweight Flatpak/Flathub front-end. The core is pure standard library, so
it runs even when the heavier AI dependencies are absent.

```bash
lucy-app-manager list                 # curated catalog
lucy-app-manager search spotify       # catalog + Flathub
lucy-app-manager install com.spotify.Client
lucy-app-manager remove  com.spotify.Client
lucy-app-manager installed
lucy-app-manager status
lucy-app-manager setup                # add Flathub (idempotent)
```

Add `--json` anywhere for machine-readable output. The Tauri layer exposes
`app_catalog`, `app_search`, `app_install`, `app_remove`, `app_installed`,
`app_status` and `app_flathub_setup`.

The catalog lives at `/etc/lucy/apps.json`: 35 apps, 7 of them core native
packages and the rest recommended Flatpaks (Brave, VSCodium, VLC, GIMP,
LibreOffice, Spotify, OBS, Krita and more).

### Verification

```bash
python scripts/verify-app-configs.py   # config only, no Flatpak needed
bash   scripts/test-app-manager.sh     # functional, uses a fake flatpak
cd src/core/python && pytest tests     # 56 tests
lucy-boot-check                        # on the live medium: confirm autologin
```

### Boot requirements (initramfs)

An archiso live ISO does **not** use a `root=` kernel parameter. The
`archiso` initcpio hook locates the medium (by label or UUID) and
`archiso_loop_mnt` loop-mounts the airootfs squashfs. Without those hooks the
initramfs has no root to switch to and boot stops at:

```
[FAILED] Failed to start Switch Root
You are in emergency mode
```

Two things are required, and both live in this profile:

1. `airootfs/etc/mkinitcpio.conf.d/archiso.conf` — a drop-in for
   `/etc/mkinitcpio.conf`:

   ```
   HOOKS=(base udev modconf kms archiso archiso_loop_mnt block filesystems keyboard)
   ```

   `archiso` and `archiso_loop_mnt` must come **before** `block` and
   `filesystems`. The PXE hooks from the upstream profile are omitted because
   they need `mkinitcpio-nfs-utils`/`nbd`, which Lucy OS does not ship.

2. `mkinitcpio-archiso` in `packages.x86_64`. The `archiso` package does
   **not** depend on it, so it has to be explicit.

archiso never runs mkinitcpio itself — it copies `/boot` from the build root
onto the ISO — so `customize_airootfs.sh` rebuilds the initramfs and asserts
the `archiso` hook is inside it, failing the build otherwise.

The bootloader entries use `%ARCHISO_LABEL%`, `%INSTALL_DIR%` and
`%ARCHISO_UUID%`, which archiso substitutes from `profiledef.sh`
(`iso_label="LUCYOS"`). There is deliberately no `airootfs/etc/fstab`: a live
ISO must not carry static disk UUID mounts.

`scripts/verify-app-configs.py` checks all of the above on every run.

## v0.4.0 — Phase 2: Command Palette, App Store, Installer

### Global Command Palette (Super+Space)

A Spotlight-style overlay: instant app launch, in-shell actions, Lucy
settings toggles, offline semantic file search and an AI fallback.

| Piece | Where |
| --- | --- |
| Overlay UI | `src/shell/src/components/CommandPalette.tsx` |
| Global shortcut | `src-tauri/src/lib.rs` — `tauri-plugin-global-shortcut`, `SUPER`+`Space` |
| Event bridge | Rust emits `lucy://toggle-palette`; React listens and toggles |
| AI fallback | `ai_translate` RPC → `lucy_agent.shell_wrapper` |

The shortcut is a **real global hotkey**, so it works over any application.
`Super+Space` is reserved for it — the window manager deliberately does not
bind it, because two owners of the same key would fight. The Amharic layout
toggle therefore moved to **`Super+Shift+Space`**.

Type to filter apps; results include live semantic file hits (debounced
250 ms) and, with `Ctrl`+`Enter`, an AI-suggested shell command you can run.

### App Store

`src/shell/src/components/AppStore.tsx` is the graphical view over all seven
appstore RPCs (`app_catalog`, `app_search`, `app_install`, `app_remove`,
`app_installed`, `app_status`, `app_flathub_setup`). It shows the curated
catalog, category filters, install/remove, live Flatpak/Flathub status badges,
an "Enable Flathub" button, and a "Search Flathub" action that merges
Flathub-only hits into the grid. It degrades honestly when Flatpak is absent.

### UI refinements

Glassmorphic palette and store surfaces (blurred backdrops, gold accents),
responsive breakpoints at 720 px and 480 px, and a
`prefers-reduced-motion` guard.

### Graphical OS installer

**`calamares` is AUR-only — it cannot be listed in `packages.x86_64`.** Doing
so makes pacstrap abort with `target not found` and breaks the whole ISO
build, exactly like the earlier failures. So:

- `customize_airootfs.sh` probes for Calamares **best-effort** (so it is
  picked up automatically if it ever moves into the official repos) and never
  fails the build.
- `archinstall` (+ `btrfs-progs`, `dosfstools`, `efibootmgr`) **is** shipped,
  so the medium always has a working installer.
- `lucy-installer` prefers Calamares, falls back to archinstall, and otherwise
  prints exact AUR instructions.
- "**Install Lucy OS**" appears on the live desktop
  (`etc/skel/Desktop/calamares.desktop`) and in the applications menu.

Calamares configuration is complete in `airootfs/etc/calamares/`: branding,
`partition.conf` with the Btrfs subvolume layout (including `/.snapshots`,
which the Week 3 rollback engine requires), `mount.conf`, `unpackfs.conf`,
`bootloader.conf`, `initcpiocfg.conf` and the postinstall step.

**Critical:** the postinstall step removes the live medium's
`/etc/mkinitcpio.conf.d/archiso.conf` from the target and rebuilds its
initramfs. Without that the installed system inherits the `archiso` hook,
has no live medium to find, and will not boot.

### Live boot: autologin, display manager, splash

The ISO boots straight into the desktop. Nothing should ever fall through to a
TTY login prompt.

| Piece | Where |
| --- | --- |
| Live user | created in `customize_airootfs.sh` — `lucy`, empty password, NOPASSWD sudo, `-m` copies `/etc/skel` |
| Autologin | `etc/lightdm/lightdm.conf` — `autologin-user=lucy`, `autologin-user-timeout=0` |
| Autologin group | `lucy` added to the `autologin` group in `customize_airootfs.sh` |
| Greeter | `etc/lightdm/lightdm-gtk-greeter.conf` (only matters if autologin is off) |
| Session | `usr/share/xsessions/lucy.desktop` → `/usr/local/bin/lucy-session` (LXDE on Openbox) |
| Desktop | `display-manager.service` → `lightdm.service`, `default.target` → `graphical.target` |
| Prompts | `systemd-firstboot.service` and `getty@tty1.service` masked to `/dev/null` |
| Splash | `plymouth` + the `lucy` theme (`usr/share/plymouth/themes/lucy`), hook right after `udev` |

The symlinks and the user are created in `customize_airootfs.sh` rather than
committed as repo symlinks, because Git on Windows (where this project is
developed) stores them as plain files — which would leave
`display-manager.service` a text file and nothing would start X.

Plymouth cannot block boot: if the theme fails to draw on an unusual GPU or VM,
Plymouth logs it and startup continues. `plymouth.enable=0` on the kernel
command line disables it entirely. `tty2`–`tty6` stay available for rescue.

Run **`lucy-boot-check`** on the live system to confirm the whole pipeline:
target, display manager, X session, logind session for `lucy`, autologin
settings, masked prompts, and the Plymouth theme.

### Desktop themes

Official repo packages only — `papirus-icon-theme`, `deepin-icon-theme`,
`deepin-gtk-theme`, `materia-gtk-theme`, `gnome-themes-extra`, `ttf-dejavu`
and `gnu-free-fonts` (FreeSerif/FreeSans carry Ethiopic, so the optional
Amharic layout renders real glyphs instead of boxes).

`fluent-gtk-theme`, `arc-gtk-theme`, `numix-icon-theme` and
`qogir-icon-theme` are **AUR-only** and must never be added to
`packages.x86_64` — pacstrap would abort and break the build.

The live session's default GTK/icon theme is set in
`etc/skel/.config/gtk-3.0/settings.ini` using only names guaranteed to exist
(Adwaita-dark, Papirus-Dark); the Deepin themes are installed and selectable
from lxappearance.

## License

MIT License - See LICENSE file for details

## Contributing

See [AGENTS.md](AGENTS.md) for development guidelines.

## Build Environment

### Docker

The project includes Docker support for building the ISO in a clean Arch Linux environment:

```bash
# Build Docker image
docker build -t lucy-os-builder .

# Run ISO build in container
docker run --rm \
  -v $(pwd)/dist:/build/dist \
  -v $(pwd)/work:/build/work \
  --privileged \
  lucy-os-builder \
  ./scripts/build-iso.sh
```

Or use the convenience script:
```bash
./scripts/build-docker.sh
```

### GitHub Actions

Automated CI/CD builds are available via GitHub Actions. See `.github/workflows/` for workflow definitions.

### Validation

Before building, validate your environment:
```bash
./scripts/validate-build.sh
```
