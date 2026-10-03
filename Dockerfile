FROM archlinux/archlinux:latest

# Install base system
RUN pacman -Syu --noconfirm

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
    xorriso

# Install Python packages
RUN pip install maturin requests pydantic openai ollama

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
