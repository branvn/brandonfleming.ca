#!/usr/bin/env python3
"""
Bill 44 tracker: candidate collector.

Polls the sources in data/tracker_sources.yaml, keeps anything whose headline
matches the keyword list, and merges new items into data/tracker.json as
UNREVIEWED candidates (note = "").

Nothing reaches the website until you open data/tracker.json and write a `note`
for the entry. That annotation is the whole point of the tracker: an unreviewed
feed is noise, and noise on a portfolio reads as a robot nobody is watching.

Only headline, URL, and date are stored; never article body text.

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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 brandonfleming.ca-tracker"
)


# ---------------------------------------------------------------- utilities

def entry_id(url: str) -> str:
    """Stable id so re-running never duplicates an item."""
    return hashlib.sha1(url.strip().lower().encode()).hexdigest()[:12]


def clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    text = unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()


def matches(text: str, keywords: list[str]) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keywords)


def parse_date(raw: str) -> str:
    """Best-effort date parse -> YYYY-MM-DD. Falls back to today."""
    raw = (raw or "").strip()
    formats = (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def fetch(url: str) -> str | None:
    """GET a URL, retrying once on a timeout or dropped connection."""
    for attempt in (1, 2):
        try:
            r = requests.get(
                url,
                timeout=TIMEOUT * attempt,
                headers={"User-Agent": USER_AGENT},
            )
            r.raise_for_status()
            return r.text
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == 1:
                print(f"    ... {type(exc).__name__}, retrying once")
                continue
            print(f"    ! unreachable: {exc}", file=sys.stderr)
        except requests.RequestException as exc:
            print(f"    ! unreachable: {exc}", file=sys.stderr)
            break
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
        if not link:
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
    """Scrape anchor text off a page."""
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


def from_escribe(portal_url: str, keywords: list[str], max_meetings: int = 5) -> list[dict]:
    """Poll meeting agenda pages from an Escribe portal."""
    found = []
    cal_html = fetch(f"{portal_url.rstrip('/')}/MeetingsCalendarView.aspx?FillWidth=1")
    if not cal_html:
        return found

    meeting_ids = list(dict.fromkeys(
        re.findall(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", cal_html, re.I)
    ))

    for uid in meeting_ids[:max_meetings]:
        agenda_url = f"{portal_url.rstrip('/')}/Meeting.aspx?Id={uid}&Agenda=Agenda&lang=English"
        m_html = fetch(agenda_url)
        if not m_html or "Runtime Error" in m_html:
            continue

        # Extract meeting date
        date_match = re.search(r"class=[\"'][^\"']*MeetingDate[^\"']*[\"'][^>]*>(.*?)<", m_html, re.I)
        if not date_match:
            date_match = re.search(r"([A-Za-z]+ \d{1,2}, \d{4})", m_html)
        meeting_date = parse_date(date_match.group(1)) if date_match else datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Extract meeting title
        title_match = re.search(r"<title\b[^>]*>(.*?)</title>", m_html, re.I | re.S)
        meeting_title = clean(title_match.group(1)) if title_match else "Council Meeting"

        # Parse text into agenda item statements
        clean_text = clean(m_html)
        items = re.findall(r"(\d+\.(?:\d+\.?)?\s+[^.]{10,140})", clean_text)
        
        seen_items = set()
        for it in items:
            it_clean = clean(it)
            if it_clean in seen_items or len(it_clean) < 15:
                continue
            seen_items.add(it_clean)

            if matches(it_clean, keywords):
                found.append({
                    "title": f"{meeting_title}: {it_clean}",
                    "url": agenda_url,
                    "date": meeting_date,
                })
    return found


# --------------------------------------------------------------------- main

def collect(sources: list[dict], keywords: list[str]) -> list[dict]:
    results = []
    for src in sources:
        print(f"  -> {src['name']}")
        mode = src.get("mode")
        if mode == "escribe":
            hits = from_escribe(src["url"], keywords)
        elif mode == "html":
            html = fetch(src["url"])
            hits = from_html(html, src["url"], keywords, src.get("link_contains")) if html else []
        else:
            html = fetch(src["url"])
            hits = from_rss(html, keywords) if html else []

        for hit in hits:
            hit.update({
                "id": entry_id(hit["url"] + hit["title"]),
                "source": src["name"],
                "jurisdiction": src.get("jurisdiction", ""),
                "type": src.get("type", ""),
                "note": "",
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

    print(f"Polling {len(sources)} source(s) for {len(keywords)} keyword(s)...")
    candidates = collect(sources, keywords)

    new = [c for c in candidates if c["id"] not in existing]
    print(f"\n{len(new)} new candidate(s).")

    if args.dry_run:
        for c in new:
            print(f"  [{c['date']}] {c['title']}  ({c['source']})")
        return 0

    if new:
        store["entries"] = sorted(
            list(existing.values()) + new, key=lambda e: e["date"], reverse=True
        )

    store["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    DATA_FILE.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    pending = sum(1 for e in store["entries"] if not e.get("note"))
    print(f"Wrote {DATA_FILE.relative_to(ROOT)}: {pending} awaiting your note.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
