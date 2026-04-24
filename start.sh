#!/usr/bin/env bash
set -e

# Start backend
cd backend
./venv/bin/uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "🟢 Backend:  http://localhost:8000"
echo "🟢 Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers."
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
