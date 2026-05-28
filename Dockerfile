# ---- Python backend ----
FROM python:3.14-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --group dev

COPY src/ ./src/

# ---- SvelteKit frontend ----
FROM node:22-slim AS node-base

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Final image ----
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OSINTOTE_DB_PATH=/data/osintote.db

WORKDIR /app

RUN useradd --create-home osintote
USER osintote

RUN mkdir -p /data /app/.osintote/logs

COPY --from=python-base /app/.venv /app/.venv
COPY --from=python-base /app/src ./src

COPY --from=node-base /app/frontend/.output ./frontend/.output

ENTRYPOINT ["/app/.venv/bin/python", "-m", "osintote.cli"]
CMD ["serve"]
