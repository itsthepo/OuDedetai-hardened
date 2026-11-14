# Hardened build of OuDedetai

This is a private, security-hardened copy of
[FaithLife-Community/OuDedetai](https://github.com/FaithLife-Community/OuDedetai).
Upstream code is unchanged except for a small, separate stack of commits on
the `hardened` branch, each labelled `hardening(Hn)` and marked in the code
with `# HARDENING (Hn)` comments.

Baseline reviewed: upstream `a22e766` (2026-11-13).

## Patches

| ID | Problem upstream | Fix | Files |
|----|------------------|-----|-------|
| H1 | Self-update downloads the newest GitHub release binary with no signature check, runs it, and overwrites itself. It would also replace this hardened build with an unpatched one. | Self-update is disabled. Update via `scripts/hardened-sync.sh` and rebuild. | `ou_dedetai/network.py` |
| H2 | Downloads (Wine, ICU, Logos/Verbum installer, winetricks) are only checked against size/MD5 headers from the **same** server, which proves nothing if a release is tampered with. | Every download must match a reviewed SHA-256 in `ou_dedetai/assets/hardened-pins.json`. Unpinned files are refused; mismatches abort and leave the file for inspection. This also blocks the "untested" third-party Wine AppImages unless you pin one deliberately. | `ou_dedetai/network.py`, `ou_dedetai/assets/hardened-pins.json`, `scripts/hardened-pin.py` |
| H3 | ICU archive extracted with plain `extractall()`; a malicious archive could write outside the Wine prefix. | Uses tarfile's `filter="data"`. | `ou_dedetai/utils.py` |
| H4 | Dependency install joins tokens into one unquoted string and runs `sudo sh -c "…"` with `shell=True`; the user isn't shown what runs as root. | Each argument is `shlex`-quoted, the exact root script is shown for approval, and it runs as an argv list (still one password prompt). `reboot()` no longer uses a shell. Also fixes the SteamOS `sed` command breaking on spaces. | `ou_dedetai/system.py` |
| H5 | PID file in world-writable `/tmp`; the app offers to `SIGKILL` whatever PID it contains. | PID file in `$XDG_RUNTIME_DIR`; only a live process owned by you that is actually this app is offered for killing. | `ou_dedetai/constants.py`, `ou_dedetai/utils.py` |
| H6 | `os.system("rm -f <cwd>/wget-log*")` with an unquoted path. | `glob` + `os.remove`. | `ou_dedetai/utils.py` |
| H7 | The `logos4:`/`libronixdls:` URL handler put the link (which any web page can choose) unquoted inside a `/bin/sh -c "…"` string — a Desktop Entry spec violation that, depending on the launcher, allows command injection from a malicious link. | The menu entry runs a generated `url-handler.sh` with the link as a separate argument; the script only uses `"$1"`. | `ou_dedetai/installer.py` |

Tests for all of the above: `tests/test_hardening.py`.

Note: upstream currently has its `die_if_running()` call commented out, so H5 guards dormant code; kept in case upstream re-enables it.

### Known residual risks (not patched)

- **Trust on first use.** The initial pins (below) were recorded by downloading
  the files on 2026-11-14 over HTTPS. Neither GitHub (no published asset digest
  for these releases) nor Faithlife offered an independent hash to compare
  against. Pinning guarantees nothing changes *after* that point.
- **Winetricks downloads** its own components (fonts, runtimes) at install
  time; winetricks verifies those with its own SHA-256 list.
- **The Logos/Verbum installer itself** is Faithlife's proprietary software
  running inside Wine; this build does not change that trust relationship.
- **Python dependencies** (`requests`, `psutil`, `textual`, …) come from PyPI at
  build time and are not pinned by hash.

## Current pins

Run `scripts/hardened-pin.py list` for the authoritative list.

- Wine `10.8-staging` AppImage (FaithLife-Community/wine-appimages)
- ICU `72.1-custom+4` (FaithLife-Community/icu)
- Logos 10 installer `54.3.0.0005`

To install **Verbum** or a different Logos release, pin its installer URL
first (`scripts/hardened-pin.py suggest` prints it).

## After rebuilding

Install the new binary over the copy Logos launches from, then regenerate the menu entries:

```bash
D=~/.local/share/FaithLife-Community/oudedetai
install -m 0755 dist/oudedetai "$D/oudedetai.new" && mv -f "$D/oudedetai.new" "$D/oudedetai"
"$D/oudedetai" --create-shortcuts
```

## Everyday commands

```bash
scripts/hardened-build.sh                 # build dist/oudedetai in a throwaway rootless podman container
scripts/hardened-pin.py suggest           # URLs upstream currently wants
scripts/hardened-pin.py add <URL> "note"  # review + pin a new download
scripts/hardened-pin.py list
OUDEDETAI_ALLOW_UNPINNED=1 dist/oudedetai # one-off escape hatch (logs a warning)
```

## When upstream releases an update

```bash
scripts/hardened-sync.sh
```

It will:

1. fetch upstream and list the new commits and changed files,
2. highlight newly added lines touching security-sensitive code
   (shell commands, downloads, archives, URLs, privilege escalation),
3. ask before rebasing; keep a `hardened-backup-<timestamp>` branch,
4. re-apply the hardening commits; on a conflict it stops and explains how to
   continue or abort,
5. run `tests/test_hardening.py`,
6. show download URLs that may need new pins.

Then pin anything new, commit, rebuild, and
`git push --force-with-lease origin hardened`.

If upstream fixes one of these issues itself, drop the matching
`hardening(Hn)` commit during the rebase rather than keeping both.

## Remotes

- `upstream`: https://github.com/FaithLife-Community/OuDedetai (read only)
- `origin`: private GitHub repo holding the `hardened` branch
