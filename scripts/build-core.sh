#!/bin/bash
# Build script for Lucy OS Core AI Agent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CORE_DIR="$PROJECT_ROOT/src/core/python"
CONFIGS_DIR="$PROJECT_ROOT/src/configs"

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

# Install in development mode when a virtualenv/conda env is active
# (local development). maturin develop requires VIRTUAL_ENV or
# CONDA_PREFIX; in CI no virtualenv is active, so install the wheel
# produced by `maturin build` instead (maturin's recommended workflow).
if [ -n "${VIRTUAL_ENV:-}" ] || [ -n "${CONDA_PREFIX:-}" ] || [ -d ".venv" ]; then
    echo "Installing in development mode..."
    maturin develop
else
    echo "No virtualenv detected; installing built wheel..."
    WHEEL="$(ls -t target/wheels/*.whl 2>/dev/null | head -1)"
    if [ -z "$WHEEL" ]; then
        echo "Error: no wheel found in target/wheels/"
        exit 1
    fi
    pip install --force-reinstall "$WHEEL"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -e .

# Make ai-shell executable
echo "Setting up ai-shell wrapper..."
AI_SHELL="$CONFIGS_DIR/airootfs/usr/local/bin/ai-shell"
if [ -f "$AI_SHELL" ]; then
    chmod +x "$AI_SHELL"
    echo "ai-shell wrapper made executable"
fi

# Make lucyfetch executable
echo "Setting up lucyfetch tool..."
LUCYFETCH="$CONFIGS_DIR/airootfs/usr/local/bin/lucyfetch"
if [ -f "$LUCYFETCH" ]; then
    chmod +x "$LUCYFETCH"
    echo "lucyfetch tool made executable"
fi

echo "Core agent built successfully!"
echo "To test: python -c 'import lucy_agent; print(lucy_agent.__version__)'"
