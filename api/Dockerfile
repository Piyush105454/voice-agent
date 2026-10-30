# Guru Line API. Build context is the repo root (compose: context ".", dockerfile api/Dockerfile) so the image
# also carries sql/ and scripts/: `docker compose run --rm api python scripts/reset_demo.py` sets up the database.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api/ api/
COPY sql/ sql/
COPY scripts/ scripts/

WORKDIR /app/api
EXPOSE 8000
# one worker: in-process state (Bolna cooldown, browser-call sessions) lives in memory
# $PORT is set by Railway / Render / Hugging Face; 8000 locally and in docker compose
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 75 --proxy-headers --forwarded-allow-ips '*'"]
