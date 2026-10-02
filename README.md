# Lucy OS

An advanced, AI-native Linux distribution named after Lucy (Dinqnesh) from Ethiopia.

## Vision

Lucy OS is a Linux distribution where artificial intelligence is integrated at the core, providing a natural language interface for system management and operations.

## Architecture

- **Base OS**: Arch Linux (archiso-based)
- **Core AI Agent**: Hybrid Python+Rust daemon using PyO3/maturin
- **Desktop UI**: Tauri v2 + React 19 + TypeScript
- **ISO Builder**: Automated archiso scripts

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

### Desktop UI
- Tauri v2 for lightweight, cross-platform desktop application
- React 19 + TypeScript for modern, type-safe frontend
- Chat interface for natural language interaction
- System resource monitoring dashboard

### ISO Builder
- Custom archiso profile for Lucy OS
- Automated build pipeline
- Bootable installation media

## Safety

The AI agent includes multi-layer safety validation:
- Rust-level command whitelist and validation
- Python-level semantic analysis
- User confirmation for destructive operations

## License

MIT License - See LICENSE file for details

## Contributing

See [AGENTS.md](AGENTS.md) for development guidelines.
