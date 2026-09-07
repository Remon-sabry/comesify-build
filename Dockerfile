FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    curl \
    ca-certificates \
    fonts-dejavu && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir "runpod>=1.10.1" requests

RUN mkdir -p /opt/ias-fonts

COPY Roboto-Bold.ttf /opt/ias-fonts/Roboto-Bold.ttf
COPY NotoEmoji-Regular.ttf /opt/ias-fonts/NotoEmoji-Regular.ttf
COPY NotoSansArabic-Regular.ttf /opt/ias-fonts/NotoSansArabic-Regular.ttf
COPY NotoSansDevanagari-Regular.ttf /opt/ias-fonts/NotoSansDevanagari-Regular.ttf

COPY handler.py /handler.py

CMD ["python3", "/handler.py"]
