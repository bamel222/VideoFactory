#!/bin/bash
# Start backend in background
cd "$(dirname "$0")/backend" || exit 1
uvicorn app.main:app --port 3001 --reload &
BACKEND_PID=$!

# Start frontend (exposed port)
cd ../frontend || exit 1
npm run dev

# Cleanup
trap "kill $BACKEND_PID" EXIT
