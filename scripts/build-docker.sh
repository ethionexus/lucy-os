#!/bin/bash
# Build Lucy OS ISO using Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Building Lucy OS ISO using Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "Error: Docker daemon is not running. Please start Docker."
    exit 1
fi

echo "Building Docker image..."
cd "$PROJECT_ROOT"
docker build -t lucy-os-builder .

echo "Running ISO build in container..."

# Reuse the Tauri app bundle when it was already built on the
# host (the GitHub Actions workflow builds it before the Docker
# ISO build). This avoids rebuilding WebKit-dependent code inside
# the container on systems where the WebKit development packages
# are unavailable.
SKIP_TAURI=()
BUNDLE_DIR="$PROJECT_ROOT/src/shell/src-tauri/target/release/bundle"
if [ -d "$BUNDLE_DIR" ] && [ -n "$(ls -A "$BUNDLE_DIR" 2>/dev/null)" ]; then
    SKIP_TAURI=(-e LUCY_SKIP_TAURI_BUILD=1)
    echo "Host-built Tauri bundle found; reusing it in the container"
fi

docker run --rm \
  "${SKIP_TAURI[@]}" \
  -v "$(pwd)/dist:/build/dist" \
  -v "$(pwd)/work:/build/work" \
  -v "$(pwd)/src/core/python/target/wheels:/build/src/core/python/target/wheels" \
  -v "$BUNDLE_DIR:/build/src/shell/src-tauri/target/release/bundle" \
  --privileged \
  lucy-os-builder \
  ./scripts/build-iso.sh

echo "ISO build complete!"
echo "Output: dist/"
ls -lh dist/*.iso 2>/dev/null || echo "No ISO file found in dist/"
