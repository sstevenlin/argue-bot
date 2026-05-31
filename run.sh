#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || { echo "Run ./install.sh first"; exit 1; }
python app.py "$@"
