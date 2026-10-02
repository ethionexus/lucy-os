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
# Build entire ISO (requires root)
sudo ./scripts/build-iso.sh
```

**Prerequisites:**
- archiso installed
- Root privileges
- ~20GB free disk space

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
5. **Verify desktop UI launches**

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

### Modifying Archiso Profile

1. Edit `src/configs/profiledef.sh` for metadata
2. Edit `src/configs/packages.x86_64` for packages
3. Add files to `src/configs/airootfs/`
4. Test with `sudo mkarchiso -v src/configs`

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
