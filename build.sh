#!/usr/bin/env bash
# periodica-app build pipeline (macOS / Linux / Git Bash). See README.md, "Development".
#
#   ./build.sh          ruff lint + tier-A tests (headless)
#   ./build.sh gpu      ... then tier-B tests (needs a GL context; on a headless
#                       Linux box run it under `xvfb-run -a`)
#   ./build.sh exe      ... then a PyInstaller one-folder build in dist/PeriodicaApp
#   ./build.sh setup    pip install -e ".[dev]" first, then lint + tier-A tests
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python
# Test the sources in this checkout even if another copy is installed.
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"

target="${1:-}"
case "$target" in
    ""|gpu|exe|setup) ;;
    *) echo "usage: $0 [gpu|exe|setup]" >&2; exit 2 ;;
esac

if [ "$target" = "setup" ]; then
    echo "=== pip install -e .[dev]"
    "$PYTHON" -m pip install -e ".[dev]"
fi

echo "=== ruff"
"$PYTHON" -m ruff check src tests tools

echo "=== pytest, tier A - headless"
"$PYTHON" -m pytest tests -q

if [ "$target" = "gpu" ]; then
    echo "=== pytest, tier B - gpu"
    "$PYTHON" -m pytest tests -q -m gpu
fi

if [ "$target" = "exe" ]; then
    echo "=== PyInstaller"
    "$PYTHON" -m PyInstaller --noconfirm periodica-app.spec
    echo "Executable: dist/PeriodicaApp/PeriodicaApp"
fi

echo "=== build OK"
