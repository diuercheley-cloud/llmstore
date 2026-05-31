FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    git \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY control_plane/requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir --user -r /build/requirements.txt

COPY control_plane /build/control_plane
RUN cd /build/control_plane && python -m compileall . -q 2>/dev/null || true


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb-release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

COPY control_plane/app /app/app
COPY control_plane/alembic /app/alembic
COPY control_plane/alembic.ini /app/alembic.ini
COPY control_plane/migrations /app/migrations
COPY control_plane/scripts /app/scripts
COPY VERSION /app/VERSION
RUN chmod +x /app/scripts/*.sh 2>/dev/null || true

CMD ["bash", "-lc", "alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8080"]
