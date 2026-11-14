#!/usr/bin/env bash
# Build the hardened single-file binary into dist/oudedetai.
#
# The build runs in a throwaway, rootless podman container so nothing is
# installed on the host (Bazzite is immutable and lacks tkinter):
#   - only a snapshot of the *committed* source (git archive HEAD) goes in
#   - only the output dir (dist/) is mounted; only the binary comes out
#   - "root" inside the container is your own unprivileged user on the host;
#     it is used only to dnf-install build deps into the throwaway container
#   - the build itself runs as an unprivileged user inside the container
#   - the container is deleted afterwards (--rm)
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="registry.fedoraproject.org/fedora:45"
OUT="$PWD/dist"

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "Uncommitted changes to tracked files; commit first (the build uses HEAD)." >&2
    exit 1
fi

rm -rf "$OUT"
mkdir -p "$OUT"
echo "==> Building $(git rev-parse --short HEAD) in $IMAGE"

git archive --format=tar HEAD | podman run --rm -i \
    --security-opt no-new-privileges \
    -v "$OUT:/out:Z" \
    "$IMAGE" bash -euo pipefail -c '
        dnf -y -q install python3 python3-pip python3-tkinter binutils util-linux >/dev/null
        useradd -m builder
        mkdir /src && tar -x -C /src && chown -R builder /src
        runuser -u builder -- bash -euo pipefail -c "
            cd /src
            python3 -m venv /tmp/venv
            /tmp/venv/bin/pip install -q --disable-pip-version-check \".[build]\"
            /tmp/venv/bin/python -c \"import tkinter\"
            /tmp/venv/bin/python -m unittest tests.test_hardening
            /tmp/venv/bin/pyinstaller --clean --noconfirm --log-level WARN ou_dedetai.spec
            ./dist/oudedetai --version
        "
        install -m 0755 /src/dist/oudedetai /out/oudedetai
    '

echo
echo "Built: $OUT/oudedetai"
sha256sum "$OUT/oudedetai"
