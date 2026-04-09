#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f "$ROOT_DIR/.venv/bin/activate" ]; then
  echo ".venv not found. Run scripts/run_baremetal_gpu.sh once first."
  exit 1
fi

source "$ROOT_DIR/.venv/bin/activate"
python test/gpu_latency_benchmark.py \
  --server-url "${SERVER_URL:-http://127.0.0.1:8000}" \
  --iterations "${ITERATIONS:-20}" \
  --max-depth "${MAX_DEPTH:-3}" \
  --num-samples "${NUM_SAMPLES:-100000}" \
  ${SCENE_PATH:+--scene-path "$SCENE_PATH"}
