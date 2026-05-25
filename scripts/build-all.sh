#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Building frontend ==="
cd frontend
export ASTRO_TELEMETRY_DISABLED=1
npx astro build
cd ..

echo "=== Building docs ==="
python -m mkdocs build -f docs/mkdocs.yml --site-dir "$(pwd)/server/static/docs"

echo "=== Done ==="
