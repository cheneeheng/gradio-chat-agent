FROM ubuntu:24.04

# =============================================================================
# OS SETUP
# =============================================================================

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Berlin

# Install sudo and other essentials
RUN apt-get update && apt-get install -y \
    sudo \
    curl \
    git \
    nano \
    wget \
    unzip \
    gnupg2 \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# # Create a new user 'vscode' with sudo privileges
# RUN useradd -m vscode \
#     && echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/vscode 
RUN echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/ubuntu

# Create /workspace directory and set permissions
RUN mkdir /workspace \
    && chown ubuntu:ubuntu /workspace \
    && chmod 755 /workspace

# Set user
USER ubuntu
ENV HOME_DIR=/home/ubuntu

# Set working directory
WORKDIR /workspace

# =============================================================================
# NODE JS
# =============================================================================

# Install Node.js + npm + gemini cli
ENV NVM_DIR=$HOME_DIR/nvm
RUN mkdir $NVM_DIR \
    && curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash \
    && \. "$NVM_DIR/nvm.sh" \
    && nvm install 24 \
    && npm install -g @google/gemini-cli \
    && echo 'source $NVM_DIR/nvm.sh' >> $HOME_DIR/.bashrc

# =============================================================================
# PYTHON
# =============================================================================

# Install uv - a fast Python package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/ubuntu/.local/bin:${PATH}"

# Python venv setup
RUN uv python install 3.12.11
RUN uv venv .venv

# Python cache
ENV PYTHONPYCACHEPREFIX=/tmp/pycache
ENV PYTHONPATH=/workspace

# =============================================================================
# PRE STARTUP
# =============================================================================
