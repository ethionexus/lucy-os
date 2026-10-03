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
if [ -n "${LUCY_SKIP_TAURI_BUILD:-}" ]; then
    echo "LUCY_SKIP_TAURI_BUILD is set; reusing existing Tauri release bundle"
    if [ ! -d "src-tauri/target/release/bundle" ] || [ -z "$(ls -A src-tauri/target/release/bundle 2>/dev/null)" ]; then
        echo "Error: LUCY_SKIP_TAURI_BUILD is set but no release bundle exists at"
        echo "src-tauri/target/release/bundle. Build the app first (npm run tauri"
        echo "build) or unset LUCY_SKIP_TAURI_BUILD."
        exit 1
    fi
    echo "Release bundle found:"
    ls -R src-tauri/target/release/bundle | head -20
else
    echo "Building Tauri application..."
    npm run tauri build
fi

echo "Desktop UI built successfully!"
echo "Output location: $SHELL_DIR/src-tauri/target/release/bundle/"
