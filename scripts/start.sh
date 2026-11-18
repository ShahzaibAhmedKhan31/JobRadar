#!/usr/bin/env bash
# Start the development servers together; dependencies and migrations are set up separately.
set -u

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [[ -x "$ROOT/backend/.venv/bin/python" ]]; then
  PYTHON="$ROOT/backend/.venv/bin/python"
elif [[ -x "$ROOT/backend/.venv/Scripts/python.exe" ]]; then
  PYTHON="$ROOT/backend/.venv/Scripts/python.exe"
else
  echo "Backend virtual environment not found. Set up backend/.venv and install backend/requirements-dev.txt first (see README)." >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1 || [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  echo "npm or frontend dependencies not found. Install Node.js and run 'npm install' in frontend/ first." >&2
  exit 1
fi
if ! "$PYTHON" -c 'import uvicorn' >/dev/null 2>&1; then
  echo "uvicorn is not installed in backend/.venv. Install backend/requirements-dev.txt first." >&2
  exit 1
fi

# Separate process groups allow cleanup of reload workers and npm's children too.
set -m
backend_pid=
frontend_pid=
cleanup() {
  trap - INT TERM EXIT
  echo "Stopping development servers..."
  for pid in "$backend_pid" "$frontend_pid"; do
    if [[ -n "$pid" ]]; then
      kill -TERM -- "-$pid" 2>/dev/null || true
    fi
  done
  for pid in "$backend_pid" "$frontend_pid"; do
    if [[ -n "$pid" ]]; then
      wait "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

(cd "$ROOT/backend" && exec "$PYTHON" -m uvicorn app.main:app --reload --port 8000) &
backend_pid=$!
(cd "$ROOT/frontend" && exec npm run dev) &
frontend_pid=$!
echo "Starting backend and frontend. Open http://localhost:3000; press Ctrl+C to stop both."

# Polling avoids wait -n, which is unavailable in the default macOS Bash.
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done
if ! kill -0 "$backend_pid" 2>/dev/null; then
  wait "$backend_pid"; status=$?
  echo "Backend exited (status $status); stopping frontend." >&2
else
  wait "$frontend_pid"; status=$?
  echo "Frontend exited (status $status); stopping backend." >&2
fi
# An unexpected clean exit should still be reported as failure.
if [[ $status -eq 0 ]]; then status=1; fi
exit "$status"
