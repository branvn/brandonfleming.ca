#!/usr/bin/env python3
"""
Bill 44 tracker — candidate collector.

Polls the sources in data/tracker_sources.yaml, keeps anything whose headline
matches the keyword list, and merges new items into data/tracker.json as
UNREVIEWED candidates (note = "").

Nothing reaches the website until you open data/tracker.json and write a `note`
for the entry. That annotation is the whole point of the tracker: an unreviewed
feed is noise, and noise on a portfolio reads as a robot nobody is watching.

Only headline, URL, and date are stored — never article body text.

Usage
-----
    python scripts/track_bill44.py            # poll and merge
    python scripts/track_bill44.py --dry-run  # show what would be added
    python scripts/track_bill44.py --review   # list entries awaiting a note

Runs on a schedule via .github/workflows/track-bill44.yml, but works fine
locally too.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "data" / "tracker_sources.yaml"
DATA_FILE = ROOT / "data" / "tracker.json"

TIMEOUT = 25
USER_AGENT = (
    "brandonfleming.ca Bill 44 tracker "
    "(+https://brandonfleming.ca/tracker/; contact@brandonfleming.ca)"
)


# ---------------------------------------------------------------- utilities


def entry_id(url: str) -> str:
    """Stable id so re-running never duplicates an item."""
    return hashlib.sha1(url.strip().lower().encode()).hexdigest()[:12]


def clean(text: str) -> str:
    text = unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def matches(text: str, keywords: list[str]) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keywords)


def parse_date(raw: str) -> str:
    """Best-effort date parse -> YYYY-MM-DD. Falls back to today."""
    raw = (raw or "").strip()
    formats = (
        "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def fetch(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text
    except requests.RequestException as exc:
        print(f"    ! unreachable: {exc}", file=sys.stderr)
        return None


# ------------------------------------------------------------------ sources


def from_rss(xml: str, keywords: list[str]) -> list[dict]:
    """Minimal RSS/Atom reader. Avoids a feedparser dependency."""
    found = []
    items = re.findall(r"<(?:item|entry)\b.*?</(?:item|entry)>", xml, re.S | re.I)

    for item in items:
        def tag(name: str) -> str:
            m = re.search(rf"<{name}\b[^>]*>(.*?)</{name}>", item, re.S | re.I)
            return clean(m.group(1)) if m else ""

        title = tag("title")
        if not title or not matches(title, keywords):
            continue

        link = tag("link")
        if not link:  # Atom puts the URL in an attribute
            m = re.search(r'<link[^>]+href="([^"]+)"', item, re.I)
            link = m.group(1) if m else ""
        if not link:
            continue

        found.append({
            "title": title,
            "url": link,
            "date": parse_date(tag("pubDate") or tag("published") or tag("updated")),
        })
    return found


def from_html(html: str, base_url: str, keywords: list[str],
              link_contains: str | None) -> list[dict]:
    """Scrape anchor text off a page. Fragile by nature — verify occasionally."""
    found = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for href, inner in re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
        text = clean(inner)
        if not text or len(text) < 12:
            continue
        if link_contains and link_contains.lower() not in href.lower():
            continue
        if not matches(text, keywords):
            continue
        found.append({"title": text, "url": urljoin(base_url, href), "date": today})
    return found


# --------------------------------------------------------------------- main


def collect(sources: list[dict], keywords: list[str]) -> list[dict]:
    results = []
    for src in sources:
        print(f"  → {src['name']}")
        html = fetch(src["url"])
        if not html:
            continue

        if src.get("mode") == "html":
            hits = from_html(html, src["url"], keywords, src.get("link_contains"))
        else:
            hits = from_rss(html, keywords)

        for hit in hits:
            hit.update({
                "id": entry_id(hit["url"]),
                "source": src["name"],
                "jurisdiction": src.get("jurisdiction", ""),
                "type": src.get("type", ""),
                "note": "",              # <- you write this
            })
        print(f"    {len(hits)} match{'' if len(hits) == 1 else 'es'}")
        results.extend(hits)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="don't write tracker.json")
    ap.add_argument("--review", action="store_true", help="list entries awaiting a note")
    args = ap.parse_args()

    store = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    existing = {e["id"]: e for e in store.get("entries", [])}

    if args.review:
        pending = [e for e in existing.values() if not e.get("note")]
        if not pending:
            print("Nothing awaiting review.")
            return 0
        print(f"{len(pending)} entr{'y' if len(pending) == 1 else 'ies'} awaiting a note:\n")
        for e in sorted(pending, key=lambda x: x["date"], reverse=True):
            print(f"  [{e['date']}] {e['title']}\n      {e['url']}\n")
        return 0

    config = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))
    keywords = config.get("keywords", [])
    sources = [s for s in config.get("sources", []) if s.get("url")]

    print(f"Polling {len(sources)} source(s) for {len(keywords)} keyword(s)…")
    candidates = collect(sources, keywords)

    new = [c for c in candidates if c["id"] not in existing]
    print(f"\n{len(new)} new candidate(s).")

    if args.dry_run:
        for c in new:
            print(f"  [{c['date']}] {c['title']}  ({c['source']})")
        return 0

    if new:
        # Newest first, and preserve every note already written.
        store["entries"] = sorted(
            list(existing.values()) + new, key=lambda e: e["date"], reverse=True
        )

    store["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    DATA_FILE.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")

    pending = sum(1 for e in store["entries"] if not e.get("note"))
    print(f"Wrote {DATA_FILE.relative_to(ROOT)} — {pending} awaiting your note.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
