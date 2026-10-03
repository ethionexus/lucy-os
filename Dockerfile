FROM archlinux/archlinux:latest

# Refresh keyring first to avoid database synchronization failures,
# then upgrade the system
RUN pacman -Syu --noconfirm --needed archlinux-keyring && \
    pacman -Syu --noconfirm

# Sync the repo databases so package resolution is up to date
RUN pacman -Sy --noconfirm

# Install build dependencies
RUN pacman -S --noconfirm --needed \
    base-devel \
    git \
    python \
    python-pip \
    python-psutil \
    python-pygments \
    rust \
    cargo \
    maturin \
    nodejs \
    npm \
    archiso \
    qemu \
    edk2-ovmf \
    dosfstools \
    e2fsprogs \
    squashfs-tools \
    libisoburn \
    xorriso \
    webkit2gtk \
    gtk3 \
    librsvg \
    soup3 \
    patchelf \
    openssl

# AppIndicator (system tray support for the desktop UI).
# libayatana-appindicator is AUR-only on Arch Linux and fails to
# resolve in the official repos, so use the official equivalent
# libappindicator-gtk3. Treat it as optional: the ISO build must
# continue even when the package is unavailable.
RUN pacman -S --noconfirm --needed libappindicator-gtk3 || \
    echo "libappindicator-gtk3 unavailable; continuing without AppIndicator"

# Arch Linux enforces PEP 668 (externally managed environment).
# Allow pip installs into the system Python inside this build container.
ENV PIP_BREAK_SYSTEM_PACKAGES=1
ENV PIP_ROOT_USER_ACTION=ignore

# Install Python packages
RUN pip install requests pydantic openai ollama

# Set working directory
WORKDIR /build

# Copy project files (excluding .dockerignore)
COPY . /build/

# Make scripts executable
RUN chmod +x scripts/*.sh

# Create output directories
RUN mkdir -p dist work

# Set environment variables
ENV PATH="/root/.cargo/bin:${PATH}"
ENV CARGO_HOME="/root/.cargo"

# Default command
CMD ["/bin/bash"]
