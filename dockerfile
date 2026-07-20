FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml .
RUN pip install --upgrade pip && pip install \
    "fastapi>=0.110" "uvicorn[standard]>=0.29" "httpx>=0.27" \
    "pydantic>=2.6" "pydantic-settings>=2.2"

COPY app ./app

# Railway inyecta $PORT. Idle esperado ~80-120MB (vs. 700MB del JVM).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
