#!/usr/bin/env bash
#
# Lucy OS - archiso profile definition
#

iso_name="lucy-os"
iso_label="LUCYOS"
iso_publisher="Lucy OS Project"
iso_application="Lucy OS AI-Native Linux Distribution"
iso_version="0.1.0"
install_dir="lucy"
buildmodes=('iso')
bootmodes=('bios.syslinux' 'uefi.systemd-boot')
arch="x86_64"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
# mkarchiso resolves these relative to the profile directory and
# requires pacman_conf to be non-empty (it runs realpath on it).
packages="packages.${arch}"
pacman_conf="pacman.conf"
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/root"]="0:0:700"
  ["/root/.gnupg"]="0:0:700"
)
