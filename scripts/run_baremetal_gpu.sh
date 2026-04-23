#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi not found. GPU driver/runtime is not available on this host."
  exit 1
fi

if [ ! -f "$ROOT_DIR/.venv/bin/activate" ]; then
  rm -rf "$ROOT_DIR/.venv"
  python3 -m venv "$ROOT_DIR/.venv"
fi

source "$ROOT_DIR/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements-baremetal.txt

export PYTHONPATH="$ROOT_DIR/src"
export MI_VARIANT="${MI_VARIANT:-cuda_ad_mono_polarized}"
export SIONNA_MERGE_SHAPES="${SIONNA_MERGE_SHAPES:-true}"

if [ -z "${SCENE_PATH:-}" ]; then
  DETECTED_SCENE_PATH="$(python - <<'PY'
import pathlib
try:
    import sionna.rt
    p = pathlib.Path(sionna.rt.__file__).resolve().parent / "scenes" / "munich" / "munich.xml"
    print(p if p.exists() else "")
except Exception:
    print("")
PY
)"
  if [ -n "$DETECTED_SCENE_PATH" ]; then
    export SCENE_PATH="$DETECTED_SCENE_PATH"
  else
    export SCENE_PATH="$ROOT_DIR/data/scenes/lake-wheeler-scene.xml"
  fi
fi

exec uvicorn app:app --app-dir src --host 0.0.0.0 --port 8000
