FROM debian:testing

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    texlive-full \
    fonts-texgyre \
    fonts-linuxlibertine \
    fonts-inconsolata \
    fonts-freefont-otf \
    fonts-lmodern \
    python-pygments \
    make \
    inkscape \
    python3 \
    python3-dev \
    python3-pip

RUN pip install pyyaml

WORKDIR /data
VOLUME ["/data"]
