FROM python:3.12-slim

ARG APT_MIRROR=deb.debian.org
ARG PIP_INDEX_URL=https://pypi.org/simple

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    SASES_DB_PATH=/data/users.db \
    SASES_DISABLE_LOCAL_EMBEDDING=1 \
    EMBEDDING_MODE=api

COPY requirements.txt .
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} -r requirements.txt

COPY . .
RUN mkdir -p /data

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/version', timeout=3)" || exit 1

CMD ["python", "-m", "uvicorn", "app_full:app", "--host", "0.0.0.0", "--port", "8001"]
