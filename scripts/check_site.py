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


# ------------------------------------------------------------------- coordinates

def check_coordinates() -> None:
    """The header coordinate readout, and the frame it is measured against.

    Three things go wrong here and none of them announce themselves. A sign
    dropped off a longitude puts Surrey in China and Hugo builds it happily. A
    value written `49` instead of `49.0` parses as an integer, and Hugo's `ge`
    then compares an int against a float when deciding whether the point is on
    the plate. And the frame in hugo.toml can drift from the FRAME in
    make_plate.py, after which the OFF FRAME line starts lying.
    """
    config = toml.loads((ROOT / "hugo.toml").read_text(encoding="utf-8"))
    params = config.get("params", {})

    frame = params.get("frame")
    if not frame:
        fail("hugo.toml has no params.frame. The header cannot tell whether a "
             "coordinate falls on the contour plate without it.")
        return

    # The frame must match the generator that draws the plate, or the OFF FRAME
    # line is measured against a box the background does not actually cover.
    plate = ROOT / "scripts" / "make_plate.py"
    if plate.exists():
        text = plate.read_text(encoding="utf-8")
        for edge in ("west", "east", "south", "north"):
            marker = f"{edge}="
            if marker in text:
                raw = text.split(marker, 1)[1]
                number = raw.split(",")[0].split(")")[0].strip()
                try:
                    if abs(float(number) - float(frame[edge])) > 1e-9:
                        fail(f"frame.{edge} is {frame[edge]} in hugo.toml but "
                             f"{number} in make_plate.py. The header would "
                             f"measure OFF FRAME against the wrong box.")
                except ValueError:
                    pass

    def check_point(where: str, values: dict, required: bool) -> None:
        present = [k for k in ("lat", "lng", "elev") if k in values]
        if not present:
            if required:
                fail(f"{where} sets no coordinates and nothing to inherit from.")
            return
        if len(present) != 3:
            missing = sorted({"lat", "lng", "elev"} - set(present))
            fail(f"{where} sets {', '.join(present)} but not "
                 f"{', '.join(missing)}. Set all three or none: a page that "
                 f"sets only latitude inherits a longitude from somewhere else "
                 f"and points at open ocean.")
            return

        for key in ("lat", "lng", "elev"):
            if isinstance(values[key], bool) or not isinstance(values[key], float):
                fail(f"{where}: {key} = {values[key]!r} must be a float. "
                     f"Write 49.0, not 49, so Hugo's comparisons stay honest.")

        lat, lng = values["lat"], values["lng"]
        if isinstance(lat, float) and not -90.0 <= lat <= 90.0:
            fail(f"{where}: latitude {lat} is outside -90..90.")
        if isinstance(lng, float) and not -180.0 <= lng <= 180.0:
            fail(f"{where}: longitude {lng} is outside -180..180.")

        # Everywhere this site talks about is either western North America or
        # western Europe. A positive longitude in the Americas means a dropped
        # minus sign, which is the single most common way to get this wrong.
        if isinstance(lat, float) and isinstance(lng, float):
            if 20.0 < lat < 75.0 and 100.0 < lng < 150.0:
                fail(f"{where}: longitude {lng} looks like a dropped minus "
                     f"sign. West is negative.")

    check_point("hugo.toml [params]", params, required=True)

    for path in sorted((ROOT / "content").rglob("*.md")):
        try:
            matter = front_matter(path)
        except Exception:
            continue
        check_point(str(path.relative_to(ROOT)), matter, required=False)


# -------------------------------------------------------------------------- main

def main() -> int:
    print("Checking content and data...\n")
    check_boms()
    check_photography()
    check_image_sizes()
    check_tracker()
    check_coordinates()

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
