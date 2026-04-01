#!/bin/bash
# Run the Mock Interview prototype (API + Streamlit UI)
# Usage: ./run_prototype.sh  or  bash run_prototype.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d "venv" ]]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

echo "Activating venv..."
source venv/bin/activate

if ! command -v streamlit &>/dev/null; then
  echo "Installing dependencies (including Streamlit)..."
  pip install -q -r requirements.txt
fi

echo ""
echo "Starting backend API on http://localhost:8000"
python main.py &
API_PID=$!
sleep 2

echo "Starting Streamlit UI on http://localhost:8501"
streamlit run app.py --server.headless true

kill $API_PID 2>/dev/null || true
