# Backend image with every trained model ready. Build from the Development folder (it needs Daraz_Model too):
#   git lfs pull                                   # the real model files, not placeholders
#   docker build -f backend/Dockerfile -t optistratix-backend .
#   docker run -p 8000:8000 --env-file backend/.env optistratix-backend
# Needs about 6 GB of RAM while analysing (Daraz review models ~2.2 GB, picture + caption models ~1.5 GB).
FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/Development/backend
COPY backend/requirements.txt backend/requirements-models.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-models.txt

COPY backend/ ./
COPY Daraz_Model/ /srv/Development/Daraz_Model/

# Refuse to start if any model cannot run, instead of silently giving fewer gaps.
ENV REQUIRE_MODELS=true \
    HF_HOME=/srv/cache/huggingface
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
