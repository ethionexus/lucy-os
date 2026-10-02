# Lucy OS Architecture

## Overview

Lucy OS is an AI-native Linux distribution with a hybrid architecture combining Rust, Python, and web technologies.

## System Components

### 1. Core AI Agent

The core AI agent is a hybrid Python+Rust daemon that provides natural language processing and safe command execution.

#### Rust Components (`src/core/rust/`)

- **lib.rs**: PyO3 module initialization and Python bindings
- **command.rs**: Safe command execution with whitelist validation
- **resource.rs**: System resource monitoring (CPU, memory, disk)
- **log.rs**: Structured logging with rotation

**Why Rust?**
- Performance-critical operations
- Memory safety
- Low-level system access
- Direct process execution

#### Python Components (`src/core/python/`)

- **nlp.py**: Natural language to command translation
- **safety.py**: Command safety validation layer
- **daemon.py**: Main daemon process with IPC

**Why Python?**
- Rich AI/ML ecosystem
- Rapid development
- Easy integration with LLM APIs
- Flexibility for AI logic

#### Integration

PyO3 provides seamless Rust-Python FFI:
- Rust compiled as Python extension module
- maturin handles build process
- Stable ABI (abi3) for compatibility

### 2. Desktop UI

The desktop UI is built with Tauri, providing a lightweight, cross-platform interface.

#### Backend (`src/shell/src-tauri/`)

- **main.rs**: Tauri commands for system interaction
- **Commands**:
  - `execute_command`: Execute shell commands
  - `get_system_info`: Fetch system resources
  - `get_logs`: Retrieve system logs
  - `agent_status`: Check daemon status

**Why Tauri?**
- Tiny binary size (~3MB)
- Native performance
- Web technology frontend
- Cross-platform support

#### Frontend (`src/shell/src/`)

- **App.tsx**: Main application layout
- **Chat.tsx**: Natural language chat interface
- **SystemMonitor.tsx**: Resource visualization
- **LogViewer.tsx**: Log display component

**Tech Stack:**
- React 19
- TypeScript
- Vite
- Inline styles (no CSS framework for MVP)

### 3. Archiso Configuration

Custom archiso profile for building bootable ISO images.

#### Profile Structure

- **profiledef.sh**: ISO metadata and build modes
- **packages.x86_64**: Package list for installation
- **pacman.conf**: Package manager configuration
- **airootfs/**: Custom root filesystem overlay

#### System Integration

- **Systemd service**: Auto-start daemon on boot
- **Configuration**: `/etc/lucy/agent.conf`
- **Logs**: `/var/log/lucy/`

## Data Flow

### Command Execution Flow

```
User Input (Chat UI)
    ↓
Tauri Frontend
    ↓
Tauri Command (execute_command)
    ↓
Python Daemon (IPC)
    ↓
NLP Translation (nlp.py)
    ↓
Safety Validation (safety.py)
    ↓
Rust Executor (command.rs)
    ↓
Shell Command
    ↓
Result
    ↓
UI Display
```

### System Monitoring Flow

```
System Events
    ↓
Rust Monitor (resource.rs)
    ↓
Python Daemon
    ↓
Tauri Command (get_system_info)
    ↓
React Component (SystemMonitor)
    ↓
UI Display
```

## Security Model

### Multi-Layer Safety

1. **Rust Layer**: Command whitelist and validation
2. **Python Layer**: Semantic analysis and risk assessment
3. **User Layer**: Confirmation for destructive operations

### Sandboxing

- Systemd service with restricted permissions
- NoNewPrivileges=true
- PrivateTmp=true
- ProtectSystem=strict
- ProtectHome=true

## Performance Considerations

### Rust Components
- Zero-cost abstractions
- Direct system calls
- Minimal overhead

### Python Components
- Async I/O for non-blocking operations
- Rust extensions for hot paths
- Connection pooling for IPC

### UI Components
- Virtual DOM (React)
- Efficient re-renders
- Debounced system updates

## Extension Points

### Adding New Commands

1. Add to Rust whitelist in `command.rs`
2. Add safety rule in `safety.py`
3. Add NLP pattern in `nlp.py`

### Adding New UI Components

1. Create component in `src/shell/src/components/`
2. Add Tauri command in `src-tauri/src/main.rs`
3. Integrate in `App.tsx`

### Adding System Services

1. Create systemd unit in `airootfs/etc/systemd/system/`
2. Add to packages.x86_64
3. Configure in agent.conf

## Build Pipeline

```
Source Code
    ↓
Rust (cargo build)
    ↓
Python (maturin build)
    ↓
Tauri (npm run tauri build)
    ↓
Archiso (mkarchiso)
    ↓
ISO Image
```

## Testing Strategy

### Unit Tests
- Rust: `cargo test`
- Python: `pytest`

### Integration Tests
- Agent daemon functionality
- Tauri IPC communication
- Command execution safety

### System Tests
- ISO boot in QEMU
- Installation to disk
- Service startup
- UI functionality
