#!/bin/bash
# Sentinel – Start Script (macOS / Linux)
# Runs sentinel_detect.py and sentinel.py concurrently.
# Usage: ./start.sh

echo ""
echo "Sentinel Startup"
echo "=================="
echo ""

# Kill both processes cleanly on Ctrl+C
cleanup() {
    echo ""
    echo "[sentinel] Shutting down..."
    kill $API_PID $DETECT_PID $STREAMLIT_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start detection pipeline in background
echo "[sentinel] Starting API..."
uvicorn sentinel_api:app --port 8000 &
API_PID=$!

sleep 2

echo "[sentinel] Starting detection pipeline..."
python3 sentinel_detect.py &
DETECT_PID=$!

# Small delay so detect can connect to DB before Streamlit opens
sleep 2

# Start Streamlit dashboard in background
echo "[sentinel] Starting Streamlit dashboard..."
streamlit run sentinel.py &
STREAMLIT_PID=$!

echo ""
echo "[sentinel] Both services running."
echo "[sentinel] Press Ctrl+C to stop everything."
echo ""

# Wait for either process to exit
wait $DETECT_PID $STREAMLIT_PID