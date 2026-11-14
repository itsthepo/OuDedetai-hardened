#!/usr/bin/env bash
# Build the hardened single-file binary into dist/oudedetai using the local venv.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
.venv/bin/pip install -q '.[build]'

if ! .venv/bin/python -c 'import tkinter' 2>/dev/null; then
    echo "ERROR: tkinter is missing; the app imports it at startup, so the binary would not run." >&2
    echo "       Install python3-tkinter (or build inside a toolbox/distrobox that has it)." >&2
    exit 1
fi

.venv/bin/python -m unittest tests.test_hardening
.venv/bin/pyinstaller --clean --noconfirm ou_dedetai.spec

echo
echo "Built: $(pwd)/dist/oudedetai"
sha256sum dist/oudedetai
