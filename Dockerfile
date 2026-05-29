# Stage 1: Node frontend build
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + copied frontend build
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OSINTOTE_LISTEN_HOST=0.0.0.0 \
    OSINTOTE_DB_PATH=/data/osintote.db

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy source code
COPY src/ ./src/

# Copy frontend build from Stage 1
COPY --from=frontend-builder /app/frontend/.output ./frontend/.output

# Create data directory for SQLite
RUN mkdir -p /data /app/.osintote/logs

EXPOSE 8000

CMD ["uvicorn", "osintote.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/src"]
