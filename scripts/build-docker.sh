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
docker run --rm \
  -v "$(pwd)/dist:/build/dist" \
  -v "$(pwd)/work:/build/work" \
  --privileged \
  lucy-os-builder \
  ./scripts/build-iso.sh

echo "ISO build complete!"
echo "Output: dist/"
ls -lh dist/*.iso 2>/dev/null || echo "No ISO file found in dist/"
