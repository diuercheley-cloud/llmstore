FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

COPY control_plane/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY control_plane /app
COPY tests /app/tests
COPY pytest.ini /app/pytest.ini

CMD ["bash", "-lc", "alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port 8080"]
