#!/bin/bash
# Build script for Lucy OS Core AI Agent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CORE_DIR="$PROJECT_ROOT/src/core/python"

echo "Building Lucy OS Core AI Agent..."

# Check if Rust is installed
if ! command -v rustc &> /dev/null; then
    echo "Error: Rust not found. Please install Rust first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Please install Python 3 first."
    exit 1
fi

# Check if maturin is installed
if ! command -v maturin &> /dev/null; then
    echo "Installing maturin..."
    pip install maturin
fi

cd "$CORE_DIR"

# Build Rust extension
echo "Building Rust extension with maturin..."
maturin build --release

# Install in development mode for testing
echo "Installing in development mode..."
maturin develop

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -e .

echo "Core agent built successfully!"
echo "To test: python -c 'import lucy_agent; print(lucy_agent.__version__)'"
