#!/usr/bin/env python3
"""Manage the reviewed SHA-256 pins used by the hardened build (HARDENING H2).

  scripts/hardened-pin.py suggest        # show the URLs upstream currently wants
  scripts/hardened-pin.py add URL [NOTE] # download, hash, cross-check, pin
  scripts/hardened-pin.py list           # show current pins
  scripts/hardened-pin.py remove URL

Only standard library. Downloads go to a fresh temp dir and are deleted after.
"""
import datetime
import hashlib
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

PINS = Path(__file__).resolve().parent.parent / "ou_dedetai" / "assets" / "hardened-pins.json"
UA = {"User-Agent": "oudedetai-hardened-pin"}


def _get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def _gh_release(repo: str, tag: str = "latest") -> dict:
    path = "latest" if tag == "latest" else f"tags/{tag}"
    return json.loads(_get(f"https://api.github.com/repos/{repo}/releases/{path}"))


def _gh_asset_digest(url: str) -> str | None:
    """GitHub publishes a sha256 digest for release assets; use it as a cross-check."""
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/releases/download/([^/]+)/(.+)$", url)
    if not m:
        return None
    repo, tag, name = m.groups()
    try:
        rel = _gh_release(repo, tag)
    except Exception as e:  # noqa: BLE001
        print(f"  (could not query GitHub digest: {e})")
        return None
    for a in rel.get("assets", []):
        if a.get("name") == urllib.request.unquote(name) and (a.get("digest") or "").startswith("sha256:"):
            return a["digest"].split(":", 1)[1].lower()
    return None


def load() -> dict:
    if PINS.exists():
        return json.loads(PINS.read_text())
    return {"pins": {}}


def save(data: dict) -> None:
    data["pins"] = dict(sorted(data["pins"].items()))
    PINS.write_text(json.dumps(data, indent=2) + "\n")


def cmd_add(url: str, note: str = "") -> None:
    print(f"Downloading {url}")
    h = hashlib.sha256()
    size = 0
    with tempfile.TemporaryDirectory() as td:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=600) as r, open(Path(td) / "f", "wb") as f:
            for chunk in iter(lambda: r.read(1024 * 1024), b""):
                h.update(chunk)
                f.write(chunk)
                size += len(chunk)
    digest = h.hexdigest()
    print(f"  size:    {size} bytes\n  sha256:  {digest}")
    gh = _gh_asset_digest(url)
    if gh is not None:
        if gh != digest:
            sys.exit(f"  MISMATCH with GitHub's published digest {gh}. NOT pinning.")
        print("  GitHub's published asset digest matches.")
    else:
        print("  No independent digest available; you are trusting this download.")
    if input("Pin this hash? [y/N] ").strip().lower() != "y":
        sys.exit("Not pinned.")
    data = load()
    data["pins"][url] = {
        "sha256": digest,
        "size": size,
        "added": datetime.date.today().isoformat(),
        "note": note,
    }
    save(data)
    print(f"Pinned. Commit {PINS.relative_to(PINS.parents[2])} and rebuild.")


def cmd_suggest() -> None:
    print("URLs the app will request for a default Logos 10 install:\n")
    for repo, pat in [
        ("FaithLife-Community/wine-appimages", r".*\.AppImage"),
        ("FaithLife-Community/wine-appimages", r".*\.tar\.xz"),
        ("FaithLife-Community/icu", None),
    ]:
        try:
            rel = _gh_release(repo)
            assets = [a for a in rel.get("assets", []) if pat is None or re.fullmatch(pat, a["name"])]
            if assets:
                print(f"  {repo} {rel['tag_name']}:\n    {assets[0]['browser_download_url']}")
        except Exception as e:  # noqa: BLE001
            print(f"  {repo}: {e}")
    try:
        feed = _get("https://clientservices.logos.com/update/v1/feed/logos10/stable.xml").decode("utf-8-sig")
        ver = re.search(r"<(?:\w+:)?version>([^<]+)<", feed).group(1)
        print(f"  Logos 10 stable {ver}:\n    https://downloads.logoscdn.com/LBS10/Installer/{ver}/Logos-x64.msi")
        print(f"  Verbum 10 stable {ver}:\n    https://downloads.logoscdn.com/LBS10/Verbum/Installer/{ver}/Verbum-x64.msi")
    except Exception as e:  # noqa: BLE001
        print(f"  Logos feed: {e}")
    print("\nWinetricks is only downloaded if the Wine build doesn't bundle it.")


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, rest = argv[0], argv[1:]
    if cmd == "add" and rest:
        cmd_add(rest[0], " ".join(rest[1:]))
    elif cmd == "list":
        for url, e in load()["pins"].items():
            print(f"{e['sha256']}  {e.get('added', '')}  {url}")
    elif cmd == "remove" and rest:
        data = load()
        data["pins"].pop(rest[0], None) or sys.exit("Not pinned.")
        save(data)
    elif cmd == "suggest":
        cmd_suggest()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
