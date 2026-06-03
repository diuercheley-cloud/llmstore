# docker/llm-harness/Dockerfile

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Use virtualenv for cleaner dependency management
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml /build/
# Create a dummy README for installation if needed (project.readme points to it)
RUN mkdir -p scripts/llm_harness && touch scripts/llm_harness/README.md

# Install dependencies first for caching
RUN pip install --no-cache-dir .

# Copy the actual harness code
COPY scripts/llm_harness /build/scripts/llm_harness
RUN pip install --no-cache-dir .

FROM python:3.12-slim

LABEL maintainer="Gemini CLI Agent"
LABEL description="Standalone container for LLM Harness governed agentic execution"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="."

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

# Create a non-root user
RUN useradd -m -u 1000 harness && \
    mkdir -p /workspace /reports /artifacts && \
    chown -R harness:harness /workspace /reports /artifacts

USER harness
WORKDIR /workspace

# Metadata
COPY VERSION /VERSION
ENV LLM_HARNESS_VERSION_FILE=/VERSION

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD llm-harness health --local-only || exit 1

ENTRYPOINT ["llm-harness"]
CMD ["--help"]
