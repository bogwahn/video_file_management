#!/usr/bin/env bash
set -euo pipefail

# Navigate to this script's directory
cd "$(dirname "$0")"

# Create and activate virtual environment if missing
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the helper
python app.py
