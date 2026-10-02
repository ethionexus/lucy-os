#!/bin/bash
# Build script for complete Lucy OS ISO

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIGS_DIR="$PROJECT_ROOT/src/configs"
DIST_DIR="$PROJECT_ROOT/dist"
WORK_DIR="$PROJECT_ROOT/work"

echo "Building Lucy OS ISO..."

# Create output directories
mkdir -p "$DIST_DIR"
mkdir -p "$WORK_DIR"

# Check if running as root (required for archiso)
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

# Check if archiso is installed
if ! command -v mkarchiso &> /dev/null; then
    echo "Error: archiso not found. Please install archiso first."
    echo "On Arch Linux: sudo pacman -S archiso"
    exit 1
fi

# Step 1: Build core agent
echo "Step 1: Building core AI agent..."
"$SCRIPT_DIR/build-core.sh"

# Step 2: Build desktop UI
echo "Step 2: Building desktop UI..."
"$SCRIPT_DIR/build-shell.sh"

# Step 3: Inject artifacts into archiso profile
echo "Step 3: Injecting artifacts into archiso profile..."

# Copy built agent to airootfs
if [ -d "$PROJECT_ROOT/src/core/python/target/wheels" ]; then
    mkdir -p "$CONFIGS_DIR/airootfs/opt/lucy"
    cp -r "$PROJECT_ROOT/src/core/python/target/wheels"/* "$CONFIGS_DIR/airootfs/opt/lucy/"
fi

# Copy built Tauri app to airootfs
if [ -d "$PROJECT_ROOT/src/shell/src-tauri/target/release/bundle" ]; then
    mkdir -p "$CONFIGS_DIR/airootfs/opt/lucy-shell"
    cp -r "$PROJECT_ROOT/src/shell/src-tauri/target/release/bundle"/* "$CONFIGS_DIR/airootfs/opt/lucy-shell/"
fi

# Step 4: Build ISO with archiso
echo "Step 4: Building ISO with archiso..."
mkarchiso -v -w "$WORK_DIR" -o "$DIST_DIR" "$CONFIGS_DIR"

# Step 5: Cleanup
echo "Step 5: Cleaning up..."
read -p "Clean work directory? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$WORK_DIR"
fi

echo "ISO build complete!"
echo "Output location: $DIST_DIR"
