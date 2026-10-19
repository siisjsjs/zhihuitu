FROM python:3.12-slim

# 国内构建慢时：docker compose build --build-arg USE_CN_MIRROR=1 backend
ARG USE_CN_MIRROR=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

RUN if [ "$USE_CN_MIRROR" = "1" ]; then \
      if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
        && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources; \
      elif [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
        && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list; \
      fi; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev fonts-noto-cjk fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN if [ "$USE_CN_MIRROR" = "1" ]; then \
      pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
      && pip config set install.trusted-host mirrors.aliyun.com; \
    fi \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

COPY backend .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
