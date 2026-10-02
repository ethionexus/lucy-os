# Lucy OS Installation Guide

## Development Environment Setup

### Prerequisites

- Windows 10/11 with WSL2
- Administrator access
- At least 20GB free disk space

### Step 1: Install WSL2 Arch Linux

#### Option A: From Microsoft Store (Recommended)

1. Install WSL2 on Windows:
   ```powershell
   wsl --install
   ```

2. Install Arch Linux from Microsoft Store:
   - Search "Arch Linux" in Microsoft Store
   - Install and launch

#### Option B: Manual Installation

1. Download Arch Linux WSL image:
   ```powershell
   curl -L -o archlinux.wsl https://github.com/archlinux/archlinux-wsl/releases/latest/download/archlinux-bootstrap-x86_64.tar.zst
   ```

2. Import into WSL2:
   ```powershell
   wsl --import archlinux C:\WSL\ArchLinux archlinux.wsl
   ```

### Step 2: Run Setup Script

1. Clone the repository:
   ```bash
   git clone https://github.com/lucy-os/lucy-os.git
   cd lucy-os
   ```

2. Run the setup script:
   ```bash
   ./scripts/setup-wsl.sh
   ```

This will install:
- Rust toolchain
- Python 3 and pip
- Node.js and npm
- maturin
- archiso
- QEMU (for testing)

### Step 3: Build Components

#### Build Core Agent

```bash
./scripts/build-core.sh
```

This builds:
- Rust extension module
- Python package
- Installs in development mode

#### Build Desktop UI

```bash
./scripts/build-shell.sh
```

This builds:
- React frontend
- Tauri backend
- Native binary

#### Build Complete ISO

```bash
sudo ./scripts/build-iso.sh
```

This:
- Builds all components
- Injects into archiso profile
- Generates bootable ISO
- Outputs to `dist/` directory

## Manual Installation Steps

If the setup script fails, follow these manual steps:

### Install Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

### Install Python Tools

```bash
sudo pacman -S python python-pip
pip install maturin
```

### Install Node.js

```bash
sudo pacman -S nodejs npm
```

### Install Archiso

```bash
sudo pacman -S archiso
```

### Install QEMU (for testing)

```bash
sudo pacman -S qemu edk2-ovmf
```

## Building Individual Components

### Core Agent Only

```bash
cd src/core/python
maturin develop
```

### Desktop UI Only

```bash
cd src/shell
npm install
npm run tauri dev  # Development mode
npm run tauri build  # Production build
```

### Archiso Profile Only

```bash
sudo mkarchiso -v -w work/ -o dist/ src/configs
```

## Testing the ISO

### Using QEMU

```bash
qemu-system-x86_64 \
  -m 4G \
  -smp 2 \
  -enable-kvm \
  -boot d \
  -cdrom dist/lucy-os-0.1.0-x86_64.iso \
  -drive if=virtio,file=disk.qcow2,format=qcow2
```

### Using VirtualBox

1. Create new VM
2. Mount ISO as optical drive
3. Start VM
4. Follow Arch Linux installation process

## Installing to Disk

1. Boot from ISO
2. Open terminal
3. Run installation script (if provided) or manual install:
   ```bash
   # Partition disk
   fdisk /dev/sda

   # Format partitions
   mkfs.ext4 /dev/sda1

   # Mount
   mount /dev/sda1 /mnt

   # Install base system
   pacstrap /mnt base linux linux-firmware

   # Generate fstab
   genfstab -U /mnt >> /mnt/etc/fstab

   # Chroot
   arch-chroot /mnt

   # Install Lucy OS components
   # (manual or via script)
   ```

## Troubleshooting

### WSL2 Issues

**Problem: WSL2 not installed**
```powershell
wsl --install
```

**Problem: Arch Linux WSL fails to start**
```powershell
wsl --set-default-version 2
wsl --terminate archlinux
wsl -d archlinux
```

### Build Issues

**Problem: Rust not found**
```bash
source "$HOME/.cargo/env"
```

**Problem: maturin build fails**
```bash
pip install --upgrade maturin
```

**Problem: Tauri build fails**
```bash
cd src/shell
npm install
sudo pacman -S webkit2gtk gtk3
```

### Archiso Issues

**Problem: mkarchiso not found**
```bash
sudo pacman -S archiso
```

**Problem: Permission denied**
```bash
sudo ./scripts/build-iso.sh
```

**Problem: Out of space**
```bash
# Clean work directory
rm -rf work/
```

## Development Workflow

### Typical Development Cycle

1. Make changes to code
2. Build affected component:
   - Core: `./scripts/build-core.sh`
   - UI: `./scripts/build-shell.sh`
3. Test locally
4. Build ISO: `sudo ./scripts/build-iso.sh`
5. Test in QEMU

### Hot Reloading

For UI development:
```bash
cd src/shell
npm run tauri dev
```

For agent development:
```bash
cd src/core/python
maturin develop
python -m lucy_agent.daemon
```

## Continuous Integration

The project supports CI/CD via GitHub Actions (to be configured):

- Build Rust components
- Build Python package
- Build Tauri app
- Generate ISO
- Test in QEMU
- Upload artifacts

## Support

For issues and questions:
- GitHub Issues: https://github.com/lucy-os/lucy-os/issues
- Documentation: https://docs.lucy-os.org
