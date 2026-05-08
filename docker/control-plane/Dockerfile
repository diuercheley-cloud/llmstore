FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    git \
    gnupg \
    jq \
    lsb-release && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

COPY control_plane/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY control_plane /app
COPY scripts /app/scripts
COPY tests /app/tests
COPY docs /app/docs
COPY examples /app/examples
COPY demo /app/demo
COPY README.md /app/README.md
COPY .env.example /app/.env.example
COPY .gitignore /app/.gitignore
COPY .githooks /app/.githooks
COPY VERSION /app/VERSION
COPY pytest.ini /app/pytest.ini

RUN chmod +x /app/scripts/*.sh
RUN chmod +x /app/examples/curl/*.sh /app/.githooks/pre-commit

CMD ["bash", "-lc", "alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8080"]
