FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    SASES_DB_PATH=/data/users.db \
    SASES_DISABLE_LOCAL_EMBEDDING=1 \
    EMBEDDING_MODE=api

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8001/version || exit 1

CMD ["python", "-m", "uvicorn", "app_full:app", "--host", "0.0.0.0", "--port", "8001"]
