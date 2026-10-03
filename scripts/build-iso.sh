#!/bin/bash
# Build script for complete Lucy OS ISO

set -e

# Parse command-line arguments.
USB_DEVICE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --usb)
            USB_DEVICE="${2:-}"
            shift 2
            ;;
        --usb=*)
            USB_DEVICE="${1#*=}"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--usb /dev/sdX]"
            exit 1
            ;;
    esac
done

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
    echo ""
    echo "Alternative: Use Docker build:"
    echo "  ./scripts/build-docker.sh"
    exit 1
fi

# Check if running in Arch Linux
if [ ! -f /etc/arch-release ]; then
    echo "Error: This script must be run in Arch Linux"
    echo "Current OS: $(uname -s)"
    echo ""
    echo "Alternative build methods:"
    echo "  Docker: ./scripts/build-docker.sh"
    echo "  GitHub Actions: Push to trigger workflow"
    echo "  WSL2: See docs/wsl-build-guide.md"
    exit 1
fi

# Check if archiso is installed
if ! command -v mkarchiso &> /dev/null; then
    echo "Error: archiso not found. Please install archiso first."
    echo "On Arch Linux: sudo pacman -S archiso"
    exit 1
fi

# ---------------------------------------------------------------------------
# USB persistence support
# ---------------------------------------------------------------------------
# Label used for the copy-on-write (persistent) partition. The archiso
# mkinitcpio hook locates the partition at /dev/disk/by-label/<label> when
# booted with cow_label=<label>.
LUCY_COW_LABEL="LUCY_PERSIST"

# create_persistent_usb <device> <iso>
#   Prepares a bootable, persistent live USB:
#     1. Writes the hybrid ISO to the whole device (isohybrid MBR => bootable).
#     2. Creates an ext4 partition in the trailing free space of the drive,
#        labeled LUCY_PERSIST, that the archiso hook uses as the COW store.
#   The USB is then booted with the "USB persistence" boot entry (or by adding
#   cow_label=LUCY_PERSIST to the kernel command line).
create_persistent_usb() {
    local device="$1"
    local iso="$2"
    local cow_label="${LUCY_COW_LABEL}"

    if [ -z "$device" ] || [ -z "$iso" ]; then
        echo "Usage: create_persistent_usb <device> <iso>"
        return 2
    fi
    if [ ! -b "$device" ]; then
        echo "Error: '$device' is not a block device."
        return 1
    fi
    if [[ "$device" =~ [0-9]+$ ]]; then
        echo "Error: '$device' looks like a partition. Specify the whole disk (e.g. /dev/sdX)."
        return 1
    fi
    if [ ! -f "$iso" ]; then
        echo "Error: ISO file '$iso' not found."
        return 1
    fi
    for tool in parted mkfs.ext4; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            echo "Error: '$tool' is required (parted / e2fsprogs)."
            return 1
        fi
    done

    echo "WARNING: This will ERASE all data on $device"
    lsblk "$device" 2>/dev/null || true
    if [ -t 0 ]; then
        read -r -p "Type 'yes' to continue: " reply
        [ "$reply" = "yes" ] || { echo "Aborted."; return 1; }
    fi

    echo "Writing ISO to $device ..."
    dd if="$iso" of="$device" bs=8M status=progress conv=fsync

    # The isohybrid MBR leaves the space after the ISO unallocated on a
    # larger USB drive. Create the persistence partition there.
    local free_start free_end
    read -r free_start free_end <<< "$(
        LC_ALL=C parted --script "$device" unit MiB print free 2>/dev/null |
            awk '/Free Space/ { gsub(/MiB/, "", $2); gsub(/MiB/, "", $3); s=$2; e=$3 } END { print s, e }'
    )"
    if [ -z "$free_start" ] || [ -z "$free_end" ]; then
        echo "Error: no free space found on $device. Use a USB drive larger than the ISO (e.g. 8 GB)."
        return 1
    fi
    local free_size=$(( free_end - free_start ))
    if [ "$free_size" -lt 256 ]; then
        echo "Error: only ${free_size} MiB of free space; at least 256 MiB is required for persistence."
        return 1
    fi

    echo "Creating persistence partition on $device (label: $cow_label) ..."
    parted --script --align optimal "$device" mkpart primary ext4 "${free_start}MiB" "100%"

    local part
    if [[ "$device" =~ (nvme|mmcblk) ]]; then
        part="${device}p2"
    else
        part="${device}2"
    fi

    local tries=0
    while [ ! -b "$part" ] && [ "$tries" -lt 20 ]; do
        partprobe "$device" >/dev/null 2>&1 || true
        sleep 0.5
        tries=$(( tries + 1 ))
    done

    mkfs.ext4 -F -L "$cow_label" "$part"

    echo ""
    echo "Persistent live USB created on $device"
    echo "  Boot partition : $device  (ISO, isohybrid)"
    echo "  Persistence    : $part  (label: $cow_label)"
    echo ""
    echo "Boot the 'USB persistence' entry from the boot menu (or add"
    echo "cow_label=${cow_label} to the kernel command line). Changes are"
    echo "saved to the $cow_label partition and persist across reboots."
}

# Step 1: Build core agent
echo "Step 1: Building core AI agent..."
"$SCRIPT_DIR/build-core.sh"

# Step 2: Build desktop UI
echo "Step 2: Building desktop UI..."
"$SCRIPT_DIR/build-shell.sh"

# Step 3: Inject artifacts into archiso profile
echo "Step 3: Injecting artifacts into archiso profile..."

# Copy built agent to airootfs
if [ -d "$PROJECT_ROOT/src/core/python/target/wheels" ] && [ -n "$(ls -A "$PROJECT_ROOT/src/core/python/target/wheels" 2>/dev/null)" ]; then
    mkdir -p "$CONFIGS_DIR/airootfs/opt/lucy"
    cp -r "$PROJECT_ROOT/src/core/python/target/wheels"/* "$CONFIGS_DIR/airootfs/opt/lucy/"
fi

# Copy built Tauri app to airootfs
if [ -d "$PROJECT_ROOT/src/shell/src-tauri/target/release/bundle" ] && [ -n "$(ls -A "$PROJECT_ROOT/src/shell/src-tauri/target/release/bundle" 2>/dev/null)" ]; then
    mkdir -p "$CONFIGS_DIR/airootfs/opt/lucy-shell"
    cp -r "$PROJECT_ROOT/src/shell/src-tauri/target/release/bundle"/* "$CONFIGS_DIR/airootfs/opt/lucy-shell/"
fi

# Step 4: Build ISO with archiso
echo "Step 4: Building ISO with archiso..."
mkarchiso -v -w "$WORK_DIR" -o "$DIST_DIR" "$CONFIGS_DIR"

# Step 4.5: Optionally prepare a persistent live USB.
if [ -n "$USB_DEVICE" ]; then
    echo "Step 4.5: Preparing persistent live USB on $USB_DEVICE..."
    ISO_FILE="$(find "$DIST_DIR" -maxdepth 1 -name '*.iso' -print -quit 2>/dev/null)"
    if [ -z "$ISO_FILE" ]; then
        echo "Error: no ISO found in $DIST_DIR to write to $USB_DEVICE"
        exit 1
    fi
    create_persistent_usb "$USB_DEVICE" "$ISO_FILE"
fi

# Step 5: Cleanup
echo "Step 5: Cleaning up..."
if [ -t 0 ]; then
    read -p "Clean work directory? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$WORK_DIR"
    fi
else
    echo "Non-interactive mode: keeping work directory for inspection"
fi

echo "ISO build complete!"
echo "Output location: $DIST_DIR"
