FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
COPY data_plane_mock/main.py /app/main.py
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin -c "App user" appuser \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8081
CMD ["python", "main.py"]
