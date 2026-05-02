FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
COPY data_plane_mock/main.py /app/main.py
EXPOSE 8081
CMD ["python", "main.py"]
