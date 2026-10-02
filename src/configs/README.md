# Arch ISO Configuration

Custom archiso profile for building Lucy OS installation media.

## Structure

- `profiledef.sh`: ISO profile definition
- `packages.x86_64`: Package list for installation
- `pacman.conf`: Package manager configuration
- `airootfs/`: Custom root filesystem overlay

## Building ISO

```bash
sudo mkarchiso -v -w work/ -o dist/ src/configs
```
