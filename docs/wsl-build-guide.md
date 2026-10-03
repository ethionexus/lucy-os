# Building Lucy OS in Arch Linux WSL2

This guide explains how to build Lucy OS using Arch Linux WSL2 on Windows.

## Prerequisites

- Windows 10/11 with WSL2 installed
- At least 30GB free disk space
- Administrator access

## Step 1: Install Arch Linux WSL2

### Option A: From Microsoft Store (Recommended)

1. Open Microsoft Store
2. Search for "Arch Linux"
3. Click "Get" or "Install"
4. Launch Arch Linux from Start menu

### Option B: Manual Installation

1. Download the latest Arch Linux WSL image:
   ```powershell
   Invoke-WebRequest -Uri "https://github.com/archlinux/archlinux-wsl/releases/latest/download/archlinux-bootstrap-x86_64.tar.zst" -OutFile "archlinux.tar.zst"
   ```

2. Import into WSL2:
   ```powershell
   wsl --import archlinux C:\WSL\ArchLinux archlinux.tar.zst
   ```

3. Launch Arch Linux:
   ```powershell
   wsl -d archlinux
   ```

## Step 2: Initial Setup in Arch WSL2

Enter the Arch Linux WSL2 environment:
```bash
wsl -d archlinux
```

Update the system:
```bash
sudo pacman -Syu
```

Install base development tools:
```bash
sudo pacman -S --needed base-devel git vim nano curl wget
```

## Step 3: Install Build Dependencies

Install Rust:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

Install Python and pip:
```bash
sudo pacman -S python python-pip
```

Install Node.js and npm:
```bash
sudo pacman -S nodejs npm
```

Install maturin:
```bash
pip install maturin --user
```

Install archiso:
```bash
sudo pacman -S archiso
```

Install QEMU (for testing):
```bash
sudo pacman -S qemu edk2-ovmf
```

## Step 4: Clone Lucy OS Repository

Clone the repository (if not already done):
```bash
cd ~
git clone <your-repo-url> lucy-os
cd lucy-os
```

If the repository is on Windows filesystem, mount it in WSL2:
```bash
# From Windows PowerShell (as Administrator)
wsl --mount \\wsl$\Ubuntu\mnt\c C:\Users

# Then in WSL2
cd /mnt/c/Users/ERMI/Desktop/lucy\ os
```

## Step 5: Build Lucy OS Components

### Build Core Agent
```bash
./scripts/build-core.sh
```

### Build Desktop UI
```bash
./scripts/build-shell.sh
```

## Step 6: Build ISO

```bash
sudo ./scripts/build-iso.sh
```

This will:
1. Build core agent
2. Build desktop UI
3. Inject artifacts into archiso profile
4. Run mkarchiso to generate ISO
5. Output to `dist/` directory

## Step 7: Test ISO in QEMU

```bash
qemu-system-x86_64 \
  -m 4G \
  -smp 2 \
  -enable-kvm \
  -boot d \
  -cdrom dist/lucy-os-0.1.0-x86_64.iso
```

## Troubleshooting

### archiso Not Found
```bash
sudo pacman -S archiso
```

### Rust Not Found
```bash
source "$HOME/.cargo/env"
```

### Python Module Not Found
```bash
pip install maturin requests pydantic openai ollama psutil
```

### Permission Denied on build-iso.sh
```bash
sudo ./scripts/build-iso.sh
```

### Out of Disk Space
```bash
# Clean work directory
rm -rf work/
```

### WSL2 Filesystem Performance

If building from Windows filesystem is slow:
1. Copy repository to WSL2 filesystem
2. Build there
3. Copy ISO back to Windows

```bash
cp -r /mnt/c/Users/ERMI/Desktop/lucy\ os ~/lucy-os
cd ~/lucy-os
./scripts/build-iso.sh
cp dist/*.iso /mnt/c/Users/ERMI/Desktop/lucy\ os/dist/
```

## Alternative: Use Docker

If WSL2 archiso has limitations, use Docker instead:

```bash
# In Windows PowerShell (not WSL2)
cd "C:\Users\ERMI\Desktop\lucy os"
./scripts/build-docker.sh
```

## Performance Tips

- Use WSL2 filesystem for the project (not Windows filesystem)
- Allocate more memory to WSL2 in `.wslconfig`
- Disable Windows Defender real-time scanning for WSL2 directories
- Use SSD storage for better performance

## Next Steps

After successful build:
1. Test ISO in QEMU
2. Install ISO to VM or bare metal
3. Verify all services start correctly
4. Test lucyfetch, ai-shell, and other tools
