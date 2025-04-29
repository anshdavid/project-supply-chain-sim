FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

LABEL maintainer="ansh1990@gmail.com"
LABEL version="0.1.0"
LABEL description="Dev image"

RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    apt-utils \
    gnupg2 \
    wget \  
    curl \
    ca-certificates \
    lsb-release \
    software-properties-common \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3.12-venv \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

ENV PATH="/root/.cargo/bin:$PATH"

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

RUN uv venv /.venv

RUN echo 'source /.venv/bin/activate' >> ~/.bashrc

# RUN echo 'VIRTUAL_ENV=/.venv' >> ~/.bashrc

RUN echo 'UV_PROJECT_ENVIRONMENT=/.venv' >> ~/.bashrc

# RUN source /.venv/bin/activate

WORKDIR /app

# CMD ["/bin/bash"]
CMD ["tail", "-f", "/dev/null"]