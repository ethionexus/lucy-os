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
