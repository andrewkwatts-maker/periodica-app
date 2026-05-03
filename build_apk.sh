#!/usr/bin/env bash
# Build the Periodica Android APK.
#
# Buildozer requires a Linux/WSL host. On Windows: install WSL2 (Ubuntu),
# then `wsl ./build_apk.sh` from this directory.
#
#   ./build_apk.sh           -> debug build (signed with a debug key)
#   ./build_apk.sh release   -> release build (you must provide signing keys)
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v buildozer >/dev/null 2>&1; then
    echo "buildozer not found. Install via:  pip install buildozer cython" >&2
    exit 1
fi

mode="${1:-debug}"
case "$mode" in
    debug)   buildozer -v android debug ;;
    release) buildozer -v android release ;;
    clean)   buildozer android clean ;;
    *)
        echo "Usage: $0 [debug|release|clean]" >&2
        exit 2
        ;;
esac

echo
echo "APK output: bin/"
ls -lh bin/ 2>/dev/null || true
