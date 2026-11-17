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

def check_multiplex() -> None:
    """The permit counts behind /tracker/.

    Written by scripts/track_multiplex.py, refreshed weekly by a GitHub Action.
    The checks worth having are about the shape of the claim, not the shape of
    the JSON: the pre-R1-1 years must be present and must be zero, because
    those five zeros are the only evidence on the page that the filter is
    measuring this policy rather than apartment construction in general.
    """
    data = ROOT / "data" / "multiplex.json"
    if not data.exists():
        warn("data/multiplex.json is missing. Run scripts/track_multiplex.py. "
             "The tracker page renders a placeholder without it.")
        return
    try:
        store = json.loads(data.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"data/multiplex.json is not valid JSON: {exc}")
        return

    for field in ("updated", "total_since_in_force", "per_year", "years", "filter"):
        if field not in store:
            fail(f"data/multiplex.json has no {field!r}")

    years = {y.get("year"): y.get("permits") for y in store.get("years", [])}
    missing = [y for y in ("2019", "2020", "2021", "2022", "2023") if y not in years]
    if missing:
        fail(f"data/multiplex.json is missing the control years {', '.join(missing)}. "
             f"They are what show the filter is not catching apartment blocks.")
    nonzero = {y: n for y, n in years.items() if y < "2024" and n}
    if nonzero:
        fail(f"multiplex permits reported before R1-1 existed: {nonzero}. "
             f"The filter has stopped isolating multiplexes; re-run --compare.")

    # Projects. The grouping rule is re-scored against the projects whose
    # permits name their DP number on every run. If the City changes how it
    # numbers buildings, that score falls, and the project count on the page
    # stops being trustworthy without anything else looking wrong.
    rule = store.get("project_rule")
    if not rule:
        warn("data/multiplex.json has no project counts yet. Run "
             "scripts/track_multiplex.py; the page shows permits until then.")
    else:
        if rule.get("precision", 0) < 0.97:
            fail(f"project grouping precision fell to {rule['precision']:.0%} "
                 f"(was 100% when chosen): it is now joining different projects. "
                 f"Re-run --grouping before trusting the count.")
        if rule.get("recall", 0) < 0.75:
            fail(f"project grouping recall fell to {rule['recall']:.0%} "
                 f"(was 88% when chosen). Re-run --grouping.")
        share = store.get("homes_read_share")
        if share is not None and share < 0.95:
            fail(f"homes were read for only {share:.0%} of projects (100% when added). "
                 f"The City's wording has changed; run --units and look at the misses "
                 f"before the homes figure is trusted.")
        if share is not None:
            parts = (sum(s.get("projects", 0) for s in store.get("homes_by_size") or [])
                     + store.get("partial_projects", 0) + store.get("oversize_projects", 0))
            unread = round((1 - share) * store.get("projects_since_in_force", 0))
            if parts + unread != store.get("projects_since_in_force"):
                fail(f"homes breakdown covers {parts + unread} projects, not "
                     f"{store.get('projects_since_in_force')}")
        early = [y for y in store.get("project_years") or []
                 if y.get("year", "9999") < "2024" and y.get("projects")]
        if early:
            fail(f"multiplex projects counted before R1-1 existed: {early}")

    # Headlines are other people's reporting. Only the headline, link, outlet
    # and date may be stored; anything more is copied article text and does
    # not belong in this repo. A headline over 300 characters is not a
    # headline.
    allowed = {"title", "url", "outlet", "date"}
    for n in store.get("news") or []:
        extra = set(n) - allowed
        if extra:
            fail(f"news item stores {sorted(extra)}, which may be article text: {n.get('url')}")
        if len(n.get("title") or "") > 300:
            fail(f"news title is suspiciously long, is this body text? {n.get('url')}")
        for field in ("title", "url", "outlet"):
            if not n.get(field):
                fail(f"news item missing {field!r}: {n.get('url')}")

    lf = store.get("last_full_year") or {}
    print(f"  multiplex: {store.get('homes_since_in_force', '?')} homes, "
          f"{store.get('projects_since_in_force', '?')} projects from "
          f"{store.get('total_since_in_force')} permits since R1-1; {lf.get('projects', '?')} in "
          f"{lf.get('year', '?')}; {len(store.get('news') or [])} headlines")


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


# ------------------------------------------------------------------- research

def check_research() -> None:
    """The timeline in content/research/_index.md and the weekly paper list.

    The timeline is printed in the order it is written, with a heading each
    time the year changes, so an entry added out of order would put a 2019
    study under 2026. Hence the order check.
    """
    page = ROOT / "content" / "research" / "_index.md"
    if page.exists():
        matter = front_matter(page)
        prev_key, prev_label = (0, 0), None
        for e in matter.get("timeline", []):
            label = e.get("title", "?")[:50]
            if not isinstance(e.get("year"), int):
                fail(f"research timeline: {label!r} needs a year written as a number")
                continue
            if e.get("kind", "study") not in ("policy", "study", "thesis"):
                fail(f"research timeline: {label!r} kind must be policy, study or thesis")
            if e.get("access", "") not in ("", "free", "free copy", "paywalled"):
                fail(f"research timeline: {label!r} access must be free, free copy or paywalled")
            url = e.get("url", "")
            if url and not (url.startswith("http") or url.startswith("/")):
                fail(f"research timeline: {label!r} url must start with http or /")
            # Compared with the entry just before it, not the latest seen, so
            # one misplaced entry produces one message instead of a cascade.
            key = (e["year"], e.get("month", 0))
            if key < prev_key:
                fail(f"research timeline: {label!r} ({key[0]}) comes after "
                     f"{prev_label!r} ({prev_key[0]}); entries go oldest first")
            prev_key, prev_label = key, label

    data = ROOT / "data" / "research.json"
    if not data.exists():
        warn("data/research.json is missing. Run scripts/track_research.py; the "
             "research page hides its paper list without it.")
        return
    try:
        store = json.loads(data.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"data/research.json is not valid JSON: {exc}")
        return
    allowed = {"title", "authors", "journal", "date", "url"}
    for p in store.get("papers") or []:
        extra = set(p) - allowed
        if extra:
            fail(f"research paper stores {sorted(extra)}; abstracts belong to their "
                 f"publishers: {p.get('url')}")
        if not (p.get("title") and p.get("url")):
            fail(f"research paper missing title or url: {p}")
    print(f"  research: {len(store.get('papers') or [])} papers")


# ------------------------------------------------------------- house rules

def visible_text(path: Path) -> list[tuple[int, str]]:
    """Lines a visitor could read, with comments stripped.

    Content files: TOML comments and HTML comments removed. Templates: Hugo
    template comments and HTML comments removed. Line numbers are kept so a
    failure points at the right place.
    """
    import re
    t = path.read_text(encoding="utf-8")
    blank = lambda m: "\n" * m.group(0).count("\n")
    t = re.sub(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", blank, t, flags=re.S)
    t = re.sub(r"<!--.*?-->", blank, t, flags=re.S)
    out = []
    for n, line in enumerate(t.split("\n"), 1):
        if path.suffix in (".md", ".toml") and line.lstrip().startswith("#"):
            continue
        if path.suffix in (".md", ".toml") and " #" in line and "=" in line:
            line = line.split(" #", 1)[0]          # trailing TOML comment
        out.append((n, line))
    return out


def check_house_rules() -> None:
    """Brandon's standing rule: no em dashes, anywhere a visitor can see.

    En dashes in ranges (2025 – present, 24–85mm) are correct and allowed.
    Third-party text in data/ (headlines, paper titles) is not his writing and
    is not checked.
    """
    files = (sorted((ROOT / "content").rglob("*.md")) + sorted((ROOT / "layouts").rglob("*.html"))
             + [ROOT / "hugo.toml"])
    for f in files:
        for n, line in visible_text(f):
            if "\u2014" in line:
                fail(f"em dash in {f.relative_to(ROOT)} line {n}: {line.strip()[:70]}")


# ------------------------------------------------------------- page facts

WORK_FIELDS = ("summary", "year", "context", "role", "tools")


def check_pages() -> None:
    """Search descriptions that fit, and complete fact boxes on work pages."""
    for f in sorted((ROOT / "content").rglob("*.md")):
        try:
            matter = front_matter(f)
        except Exception:
            continue
        if matter.get("draft"):
            continue
        rel = f.relative_to(ROOT)
        desc = matter.get("description") or matter.get("summary") or ""
        if len(desc) > 160:
            warn(f"{rel}: search description is {len(desc)} characters; Google shows "
                 f"about 155. Add a shorter `description` to the front matter.")
        if rel.parts[:2] == ("content", "work") and f.name != "_index.md":
            missing = [k for k in WORK_FIELDS if not matter.get(k)]
            if missing:
                fail(f"{rel}: work page missing {', '.join(missing)}; the fact box "
                     f"and the card on /work/ both read these.")


# -------------------------------------------------------------------------- main

def main() -> int:
    print("Checking content and data...\n")
    check_boms()
    check_photography()
    check_image_sizes()
    check_multiplex()
    check_research()
    check_coordinates()
    check_house_rules()
    check_pages()

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
