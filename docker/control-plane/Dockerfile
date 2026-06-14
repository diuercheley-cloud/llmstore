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

# Use virtualenv for cleaner dependency management
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY control_plane/requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir -r /build/requirements.txt

COPY control_plane /build/control_plane
COPY scripts /build/scripts
COPY examples /build/examples
RUN cd /build/control_plane && python -m compileall . -q 2>/dev/null || true


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && . /etc/os-release \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $VERSION_CODENAME stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Layout: /app/control_plane matches repository structure.
# PYTHONPATH includes /app to allow 'import control_plane.app'
# and /app/control_plane to allow 'import app' for backward compatibility.
COPY control_plane /app/control_plane
COPY scripts /app/scripts
COPY examples /app/examples
COPY VERSION /app/VERSION

ENV PYTHONPATH="/app:/app/control_plane"

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin -c "App user" appuser \
    && chown -R appuser:appuser /app /opt/venv

USER appuser

# Gunicorn configuration for production
ENV WEB_CONCURRENCY=1 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_KEEPALIVE=5

# We run alembic from the control_plane directory so it finds alembic.ini and the alembic/ folder.
CMD ["sh", "-c", "\
    cd control_plane && \
    (alembic upgrade head 2>/dev/null || alembic stamp head 2>/dev/null || true) && \
    cd .. && \
    if [ \"$APP_ENV\" = \"production\" ] || [ \"$APP_ENV\" = \"enterprise-production\" ]; then \
        gunicorn -k uvicorn.workers.UvicornWorker \
                 -w ${WEB_CONCURRENCY:-$(nproc)} \
                 --timeout $GUNICORN_TIMEOUT \
                 --keep-alive $GUNICORN_KEEPALIFE \
                 --bind 0.0.0.0:8080 \
                 app.main:app; \
    else \
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8080; \
    fi"]
