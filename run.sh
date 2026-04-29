#!/bin/bash
# Start the ShallWe Tech CRM (Streamlit).
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtualenv…"
    python3 -m venv .venv
fi
source .venv/bin/activate

pip install -q -r requirements.txt

echo ""
echo "Opening CRM at http://localhost:8501"
echo ""
streamlit run app.py
