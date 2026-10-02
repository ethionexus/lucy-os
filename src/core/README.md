# Lucy OS Core AI Agent

Hybrid Python+Rust daemon that translates natural language into safe bash commands, manages system logs, and handles system resources.

## Architecture

- **Rust components** (`rust/`): Performance-critical operations
  - Safe command execution with validation
  - System resource monitoring
  - Structured logging

- **Python components** (`python/`): AI logic
  - Natural language processing
  - Command safety validation
  - Daemon orchestration

## Building

```bash
cd src/core/python
maturin develop
```

## Testing

```bash
cd rust
cargo test

cd ../python
pytest
```
