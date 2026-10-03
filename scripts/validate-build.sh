#!/bin/bash
# Validate build environment and prerequisites for Lucy OS ISO build

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Validating Lucy OS build environment..."
echo ""

ERRORS=0
WARNINGS=0

# Function to log error
log_error() {
    echo "✗ ERROR: $1"
    ((ERRORS++))
}

# Function to log warning
log_warning() {
    echo "⚠ WARNING: $1"
    ((WARNINGS++))
}

# Function to log success
log_success() {
    echo "✓ $1"
}

# Check if running in Arch Linux
if [ -f /etc/arch-release ]; then
    log_success "Running in Arch Linux"
else
    log_error "Not running in Arch Linux (required for native ISO build)"
    echo "  Use Docker: ./scripts/build-docker.sh"
    echo "  Or install Arch Linux WSL2: see docs/wsl-build-guide.md"
fi

# Check for archiso
if command -v mkarchiso &> /dev/null; then
    log_success "archiso installed"
else
    log_error "archiso not found"
    echo "  Install with: sudo pacman -S archiso"
fi

# Check for Rust
if command -v rustc &> /dev/null; then
    log_success "Rust installed"
else
    log_error "Rust not found"
    echo "  Install with: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
fi

# Check for Python
if command -v python3 &> /dev/null; then
    log_success "Python 3 installed"
else
    log_error "Python 3 not found"
    echo "  Install with: sudo pacman -S python"
fi

# Check for Node.js
if command -v node &> /dev/null; then
    log_success "Node.js installed"
else
    log_error "Node.js not found"
    echo "  Install with: sudo pacman -S nodejs"
fi

# Check for maturin
if command -v maturin &> /dev/null; then
    log_success "maturin installed"
else
    log_warning "maturin not found in PATH"
    echo "  Install with: pip install maturin --user"
fi

# Check for required files
echo ""
echo "Checking project files..."

cd "$PROJECT_ROOT"

if [ -f "src/configs/profiledef.sh" ]; then
    log_success "Profile definition found"
else
    log_error "Profile definition not found"
fi

if [ -f "src/configs/packages.x86_64" ]; then
    log_success "Package list found"
else
    log_error "Package list not found"
fi

if [ -f "scripts/build-core.sh" ]; then
    log_success "Core build script found"
else
    log_error "Core build script not found"
fi

if [ -f "scripts/build-shell.sh" ]; then
    log_success "Shell build script found"
else
    log_error "Shell build script not found"
fi

if [ -f "scripts/build-iso.sh" ]; then
    log_success "ISO build script found"
else
    log_error "ISO build script not found"
fi

# Check for disk space
echo ""
echo "Checking disk space..."
DISK_AVAILABLE=$(df -BG . | tail -1 | awk '{print $4}')
if [ "$DISK_AVAILABLE" != "" ]; then
    log_success "Disk space available: $DISK_AVAILABLE"
else
    log_warning "Could not determine disk space"
fi

# Check for Docker as alternative
echo ""
echo "Checking for Docker (alternative build method)..."
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        log_success "Docker available (alternative build method)"
        echo "  Use: ./scripts/build-docker.sh"
    else
        log_warning "Docker installed but daemon not running"
    fi
else
    log_warning "Docker not found"
    echo "  Install from: https://docs.docker.com/get-docker/"
fi

# Summary
echo ""
echo "=== Validation Summary ==="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "✓ All critical checks passed!"
    echo "You can proceed with: sudo ./scripts/build-iso.sh"
    exit 0
else
    echo "✗ Critical errors found. Please fix them before building."
    exit 1
fi
