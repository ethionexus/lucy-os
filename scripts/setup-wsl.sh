#!/bin/bash
# Setup script for WSL2 Arch Linux development environment

set -e

echo "Setting up Lucy OS development environment in WSL2..."

# Check if running in WSL
if ! grep -q Microsoft /proc/version; then
    echo "Warning: This script is designed for WSL2 environment"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Updating system packages..."
sudo pacman -Syu --noconfirm

# Install base development tools
echo "Installing base development tools..."
sudo pacman -S --noconfirm --needed \
    base-devel \
    git \
    vim \
    nano \
    curl \
    wget \
    unzip

# Install Rust
echo "Installing Rust..."
if ! command -v rustc &> /dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
else
    echo "Rust already installed"
fi

# Install Python and pip
echo "Installing Python and pip..."
sudo pacman -S --noconfirm --needed python python-pip

# Install Node.js and npm
echo "Installing Node.js and npm..."
sudo pacman -S --noconfirm --needed nodejs npm

# Install maturin for Rust-Python bindings
echo "Installing maturin..."
pip install maturin --user

# Install archiso (for building ISO)
echo "Installing archiso..."
sudo pacman -S --noconfirm --needed archiso

# Install QEMU (for testing ISO)
echo "Installing QEMU..."
sudo pacman -S --noconfirm --needed qemu edk2-ovmf

# Create project directory structure
echo "Creating project directory structure..."
mkdir -p src/core/rust/src
mkdir -p src/core/python/lucy_agent
mkdir -p src/shell/src/components
mkdir -p src/shell/src/hooks
mkdir -p src/shell/src-tauri/src
mkdir -p src/configs/airootfs/etc/lucy
mkdir -p src/configs/airootfs/etc/systemd/system
mkdir -p scripts
mkdir -p docs
mkdir -p dist

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Navigate to project directory"
echo "2. Run: ./scripts/build-core.sh"
echo "3. Run: ./scripts/build-shell.sh"
echo "4. Run: sudo ./scripts/build-iso.sh"
