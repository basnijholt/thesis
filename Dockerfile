FROM debian:testing-20200224

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
    python3-setuptools \
    python3-pip

RUN python3 -m pip install pyyaml jinja2

WORKDIR /data
VOLUME ["/data"]
