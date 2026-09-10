#!/bin/zsh
cd "$(dirname "$0")"
source .venv/bin/activate

PORT=5050
for candidate in 5050 5051 5052 8000 5000; do
  if ! lsof -iTCP:$candidate -sTCP:LISTEN >/dev/null 2>&1; then
    PORT=$candidate
    break
  fi
done

export PORT
open "http://127.0.0.1:$PORT" 2>/dev/null || true
python app/app.py
