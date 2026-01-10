# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # help Chrome run in containers
    UC_EXTRA_ARGS="--no-sandbox --disable-dev-shm-usage" \
    TZ=Asia/Colombo

# OS deps for Chrome
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libdrm2 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxi6 \
    libxtst6 libxrandr2 libgbm1 libgtk-3-0 libasound2 libxshmfence1 curl unzip \
  && rm -rf /var/lib/apt/lists/*

# Install Google Chrome stable
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
  && apt-get update \
  && apt-get install -y ./google-chrome-stable_current_amd64.deb \
  && rm google-chrome-stable_current_amd64.deb

# App dirs
WORKDIR /app
COPY requirements.txt /app/

RUN python -m pip install --upgrade pip wheel setuptools \
  && pip install -r requirements.txt

# Copy code
COPY new-token-extractor-redis.py trader-extractor-redis.py token-info-api.py /app/

# Point undetected-chromedriver to Chrome
ENV UC_CHROME_BINARY=/usr/bin/google-chrome

# Default command overridden by compose services
CMD ["python", "-u", "new-token-extractor-redis.py"]