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

## Quick Start

```bash
# Set up WSL2 environment
./scripts/setup-wsl.sh

# Build core agent
./scripts/build-core.sh

# Build desktop UI
./scripts/build-shell.sh

# Build complete ISO
./scripts/build-iso.sh
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

## License

MIT License - See LICENSE file for details

## Contributing

See [AGENTS.md](AGENTS.md) for development guidelines.
