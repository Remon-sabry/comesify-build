FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip ffmpeg curl ca-certificates fonts-dejavu && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir runpod requests
COPY fonts /opt/ias-fonts
COPY handler.py /handler.py
CMD ["python3","/handler.py"]
