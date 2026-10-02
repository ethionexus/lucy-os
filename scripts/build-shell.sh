#!/bin/bash
# Build script for Lucy OS Desktop UI (Tauri)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SHELL_DIR="$PROJECT_ROOT/src/shell"

echo "Building Lucy OS Desktop UI..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js not found. Please install Node.js first."
    exit 1
fi

# Check if Rust is installed
if ! command -v rustc &> /dev/null; then
    echo "Error: Rust not found. Please install Rust first."
    exit 1
fi

cd "$SHELL_DIR"

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

# Build Tauri app
echo "Building Tauri application..."
npm run tauri build

echo "Desktop UI built successfully!"
echo "Output location: $SHELL_DIR/src-tauri/target/release/bundle/"
