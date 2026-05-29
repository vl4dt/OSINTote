#!/usr/bin/env bash
# Start both the backend API server and the frontend dev server.
# Usage:
#   ./scripts/dev.sh        # Start both servers
#   ./scripts/dev.sh api    # Start only the backend API server
#   ./scripts/dev.sh ui     # Start only the frontend dev server
#
# Alternatively use:
#   make dev        (requires make + uv)
#   cd frontend && npm run dev  (frontend only)
#   osintote serve                            (backend only)

set -euo pipefail

BACKEND_HOST="127.0.0.1"
BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "Shutting down servers..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo "Done."
    exit 0
}

trap cleanup SIGINT SIGTERM

usage() {
    echo "Usage: $0 [api|ui|both]"
    echo ""
    echo "  api   - Start the backend API server only"
    echo "  ui    - Start the frontend dev server only"
    echo "  both  - Start both servers (default)"
}

start_backend() {
    echo "Starting backend API server at http://${BACKEND_HOST}:${BACKEND_PORT}..."
    echo "  API docs: http://${BACKEND_HOST}:${BACKEND_PORT}/api/docs"
    echo ""
    uv run uvicorn osintote.api.app:app \
        --reload \
        --host "${BACKEND_HOST}" \
        --port "${BACKEND_PORT}" &
    BACKEND_PID=$!
    echo "  Backend PID: ${BACKEND_PID}"
}

start_frontend() {
    echo "Starting frontend dev server at http://localhost:${FRONTEND_PORT}..."
    echo ""
    (cd frontend && uv run dev) &
    FRONTEND_PID=$!
    echo "  Frontend PID: ${FRONTEND_PID}"
}

MODE="${1:-both}"

case "$MODE" in
    api)
        start_backend
        echo "Backend running. Press Ctrl+C to stop."
        wait "$BACKEND_PID"
        ;;
    ui)
        start_frontend
        echo "Frontend running. Press Ctrl+C to stop."
        wait "$FRONTEND_PID"
        ;;
    both)
        start_backend
        start_frontend
        echo ""
        echo "========================================"
        echo "  OSINTote dev server"
        echo "  Backend:  http://${BACKEND_HOST}:${BACKEND_PORT}"
        echo "  Frontend: http://localhost:${FRONTEND_PORT}"
        echo "  API docs: http://${BACKEND_HOST}:${BACKEND_PORT}/api/docs"
        echo "========================================"
        echo ""
        echo "Press Ctrl+C to stop all servers."
        echo ""
        # Wait for either process to exit
        wait
        ;;
    *)
        usage
        exit 1
        ;;
esac
