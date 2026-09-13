# ==============================================================================
# RailSync 2.0 — Production Multi-Stage Dockerfile for Hugging Face Spaces
# 100% Free · 16 GB RAM · Single URL for React SPA + FastAPI Backend
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build the React 19 + Vite Frontend
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Install dependencies
COPY Frontend/package*.json ./
RUN npm install

# Copy source and compile production bundle
COPY Frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Python 3.12 Backend with Pre-installed ML & OR-Tools
# ------------------------------------------------------------------------------
FROM python:3.12-slim
WORKDIR /app

# Environment variables for Hugging Face Spaces
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    PYTHONPATH=/app:/app/Backend

# Install essential system build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY Backend/requirements.txt ./Backend/
RUN pip install --no-cache-dir -r ./Backend/requirements.txt

# Copy Backend codebase and dataset folders
COPY Backend/ ./Backend/
COPY Railsync_2.0_Layer_0_FINAL/ ./Railsync_2.0_Layer_0_FINAL/
COPY Railsync_Layer1_Complete/ ./Railsync_Layer1_Complete/

# Copy compiled React frontend into Backend/static for unified serving
COPY --from=frontend-builder /app/frontend/dist ./Backend/static

# Hugging Face Spaces requires running as a non-root user (UID 1000)
RUN useradd -m -u 1000 user && \
    chown -R user:user /app

USER user
WORKDIR /app/Backend

# Pre-seed all 6 Indian Railway Corridors (120 segments + risk predictions) into SQLite
RUN python scripts/seed_all_corridors.py

# Hugging Face Spaces default port
EXPOSE 7860

# Start Uvicorn on 0.0.0.0:7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
