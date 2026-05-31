#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "Created .env — add your ANTHROPIC_API_KEY"
fi

echo "Installed. Usage:"
echo "  ./run.sh                             # start the web app"
echo "  ./argue.sh screenshot.png            # CLI (still works)"
echo ""
echo "Web app runs at http://127.0.0.1:8080"
