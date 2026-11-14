#!/usr/bin/env bash
# Pull upstream OuDedetai changes and re-apply the hardening patches on top.
# See HARDENING.md. Safe to re-run; it stops before changing anything if the
# working tree is dirty, and keeps a backup branch of the previous state.
set -euo pipefail

cd "$(dirname "$0")/.."
UPSTREAM_REF="upstream/main"
BRANCH="hardened"

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Working tree has uncommitted changes; commit or stash them first." >&2
    exit 1
fi
if [[ "$(git branch --show-current)" != "$BRANCH" ]]; then
    echo "Check out the '$BRANCH' branch first." >&2
    exit 1
fi

echo "==> Fetching upstream"
git fetch upstream --tags

base="$(git merge-base HEAD "$UPSTREAM_REF")"
if [[ "$base" == "$(git rev-parse "$UPSTREAM_REF")" ]]; then
    echo "Already up to date with $UPSTREAM_REF."
    exit 0
fi

echo
echo "==> New upstream commits"
git --no-pager log --oneline "$base..$UPSTREAM_REF"

echo
echo "==> Files changed upstream"
git --no-pager diff --stat "$base" "$UPSTREAM_REF"

echo
echo "==> Security-relevant lines added upstream (review these)"
git --no-pager diff -U0 "$base" "$UPSTREAM_REF" -- '*.py' '*.sh' '*.yml' '*.yaml' '*.spec' Dockerfile \
    | grep -nE '^\+.*(shell=True|os\.system|os\.popen|eval\(|exec\(|pickle|yaml\.load\(|extractall|https?://|subprocess|chmod|sudo|pkexec|verify=False|requests\.(post|put)|update_lli_binary|_verify_downloaded_file|logos_reuse_download|PID_FILE|tarfile|zipfile)' \
    || echo "  (none matched)"

echo
read -r -p "Rebase the hardening patches onto these changes now? [y/N] " ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "Stopped. Nothing changed."; exit 0; }

backup="hardened-backup-$(date +%Y%m%d-%H%M%S)"
git branch "$backup"
echo "==> Backup of current state: $backup"

if ! git rebase "$UPSTREAM_REF"; then
    cat >&2 <<EOF

!! A hardening patch conflicts with the upstream changes.
   Resolve the conflict (or ask Claude to help), then:
       git add <files> && git rebase --continue
   To give up and restore the previous state:
       git rebase --abort
   (Backup branch: $backup)
EOF
    exit 1
fi

echo
echo "==> Running hardening tests"
PY=".venv/bin/python"; [[ -x "$PY" ]] || PY="python3"
"$PY" -m unittest tests.test_hardening

echo
echo "==> Download URLs upstream now wants (pin any that are new)"
python3 -I scripts/hardened-pin.py suggest
echo
python3 -I scripts/hardened-pin.py list

cat <<EOF

Done. Next steps:
  1. Pin any new URLs above:   scripts/hardened-pin.py add <URL> "<note>"
  2. Commit the pin file.
  3. Rebuild:                  scripts/hardened-build.sh
  4. Push:                     git push --force-with-lease origin $BRANCH
EOF
