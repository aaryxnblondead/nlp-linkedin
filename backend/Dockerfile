# Backend production Dockerfile
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Pre-install spaCy model (can be overridden via build arg)
ARG SPACY_MODEL=en_core_web_sm
ENV SPACY_MODEL=${SPACY_MODEL}
RUN python -m spacy download ${SPACY_MODEL}

# Copy app
COPY . /app

# Ensure runtime dirs exist
RUN mkdir -p /app/uploaded_resumes && mkdir -p /app/chroma_db

# Entrypoint to run migrations then start server
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
