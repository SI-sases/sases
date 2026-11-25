FROM python:3.12-slim

ARG PIP_INDEX_URL=https://pypi.org/simple

RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} playwright

RUN python -m playwright install --with-deps chromium

WORKDIR /work
CMD ["python"]
