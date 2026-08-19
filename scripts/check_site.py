#!/usr/bin/env python3
"""
Pre-push sanity check.

Catches the things that break quietly: a photo with no caption, a filter chip
pointing at a category nothing uses, a 20 MB original that would enter the Git
history permanently, a byte-order mark that stops Hugo parsing a data file,
malformed JSON that fails the Cloudflare build.

None of this replaces `hugo server`. A template error can only be found by
building. This catches the content and data problems that a build will happily
sail past.

    python scripts/check_site.py

Exits 0 if everything passes, 1 if anything failed. Warnings do not fail.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import tomllib as toml          # Python 3.11+
except ModuleNotFoundError:         # pragma: no cover
    import tomli as toml

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "content" / "photography"
MAX_IMAGE_BYTES = 2 * 1024 * 1024   # anything larger never belongs in a commit

fails: list[str] = []
warns: list[str] = []


def fail(msg: str) -> None:
    fails.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


def front_matter(path: Path) -> dict:
    """Parse the TOML block between the +++ fences."""
    return toml.loads(path.read_text(encoding="utf-8").split("+++")[1])


# --------------------------------------------------------------- byte order marks

def check_boms() -> None:
    """A BOM is invisible in an editor and stops Hugo's YAML parser dead.

    PowerShell 5.1's `Set-Content -Encoding utf8` writes one every time, so this
    keeps coming back whenever a file is generated from a terminal.
    """
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(p in path.parts for p in (".git", "public", "resources", "_preview")):
            continue
        if path.suffix.lower() not in {".md", ".toml", ".yaml", ".yml", ".json", ".py", ".html", ".css", ".js"}:
            continue
        if path.read_bytes()[:3] == b"\xef\xbb\xbf":
            fail(f"byte-order mark at the start of {path.relative_to(ROOT)}")


# ------------------------------------------------------------------- photography

def check_photography() -> None:
    index = PHOTOS / "_index.md"
    if not index.exists():
        fail("content/photography/_index.md is missing")
        return

    fm = front_matter(index)
    caps = fm.get("captions", {})
    cats = set(fm.get("categories", []))
    media = set(fm.get("media", []))
    files = {p.name for p in PHOTOS.glob("*.jpg")}

    for name in sorted(files - set(caps)):
        fail(f"photo has no caption block: {name}")
    for name in sorted(set(caps) - files):
        fail(f"caption block has no photo: {name}")

    for name, m in sorted(caps.items()):
        if not m.get("alt"):
            fail(f"no alt text: {name}")
        if m.get("category") not in cats:
            fail(f"category {m.get('category')!r} is not in `categories`: {name}")
        if m.get("medium") not in media:
            fail(f"medium {m.get('medium')!r} is not in `media`: {name}")
        if not m.get("place"):
            warn(f"no place set: {name}")

    # A chip with nothing behind it renders an empty tab, which is the one thing
    # the gallery was designed to avoid.
    for axis, allowed in (("category", cats), ("medium", media)):
        used = {m.get(axis) for m in caps.values()}
        for value in sorted(allowed - used):
            fail(f"filter {value!r} has no photos behind it")

    orders = [m.get("order") for m in caps.values() if m.get("order") is not None]
    if len(orders) != len(set(orders)):
        warn("two photos share an `order`; ties fall back to filename")


# ------------------------------------------------------------------ image weight

def check_image_sizes() -> None:
    """Git keeps every version of a binary forever. An oversized file committed
    once is in the history permanently, even after it is deleted."""
    for path in (ROOT / "content").rglob("*.jpg"):
        size = path.stat().st_size
        if size > MAX_IMAGE_BYTES:
            fail(f"{path.relative_to(ROOT)} is {size / 1e6:.1f} MB, resize to 2200px "
                 f"on the long edge before committing")


# ----------------------------------------------------------------------- tracker

def check_tracker() -> None:
    data = ROOT / "data" / "tracker.json"
    if not data.exists():
        fail("data/tracker.json is missing")
        return
    try:
        store = json.loads(data.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"data/tracker.json is not valid JSON: {exc}")
        return

    entries = store.get("entries", [])
    for e in entries:
        for field in ("id", "title", "url", "date", "note"):
            if field not in e:
                fail(f"tracker entry missing {field!r}: {e.get('title', e.get('id', '?'))}")
        # Only headline, URL, date and match metadata are ever stored. Anything
        # longer than a title suggests document text crept in.
        if len(e.get("title", "")) > 300:
            fail(f"tracker title is suspiciously long, is this body text? {e.get('id')}")

    annotated = sum(1 for e in entries if e.get("note"))
    print(f"  tracker: {len(entries)} candidates, {annotated} annotated")

    if (ROOT / "data").glob("tracker_sources.yaml"):
        for stray in (ROOT / "data").glob("tracker_*"):
            if stray.name != "tracker.json":
                fail(f"{stray.relative_to(ROOT)} should live in scripts/, not data/. "
                     f"Hugo parses everything in data/ on every build.")


# -------------------------------------------------------------------------- main

def main() -> int:
    print("Checking content and data...\n")
    check_boms()
    check_photography()
    check_image_sizes()
    check_tracker()

    if warns:
        print("\nWarnings (not failures):")
        for w in warns:
            print(f"  ~ {w}")

    if fails:
        print("\nFailures:")
        for f in fails:
            print(f"  ! {f}")
        print(f"\n{len(fails)} problem(s). Fix before pushing.")
        return 1

    print("\nAll checks passed. Still run `hugo server` before you push: a "
          "template error can only be caught by building.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
