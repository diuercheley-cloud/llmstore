FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências de áudio necessárias para o pocket-tts no Linux
RUN apt-get update && apt-get install -y --no-install-recommends     curl     libasound2     libportaudio2     libsndfile1     && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin -c "App user" appuser

# Instala o uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/appuser/.local/bin:$PATH"
ENV UV_TOOL_DIR="/home/appuser/.local/share/uv"

# Instala o pocket-tts as appuser
USER appuser
RUN uv tool install pocket-tts

EXPOSE 8000

# Executa o servidor ouvindo em todas as interfaces
CMD ["uvx", "pocket-tts", "serve", "--host", "0.0.0.0", "--port", "8000"]
