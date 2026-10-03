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
    gtk3 \
    librsvg \
    patchelf \
    openssl

# Optional dependencies that are not present in every mirror
# snapshot (pacman reports "target not found" for webkit2gtk,
# soup3, and the AppIndicator library). Install each one
# best-effort so the ISO build continues without them.
RUN for pkg in webkit2gtk soup3 libappindicator-gtk3; do \
        pacman -S --noconfirm --needed "$pkg" || \
            echo "warning: $pkg unavailable; continuing"; \
    done

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
