#!/usr/bin/env python3
"""
Bill 44 tracker: candidate collector.

Polls the sources in scripts/tracker_sources.yaml, tests either titles or linked
PDF documents against targeted keywords, and merges new items into
data/tracker.json as UNREVIEWED candidates (note = "").

Nothing reaches the website until you open data/tracker.json and write a `note`
for the entry.

Only headline/title, URL, date, hit counts, and matched query terms are stored;
never article or document body text.

Usage
-----
python scripts/track_bill44.py                       # poll and merge
python scripts/track_bill44.py --dry-run             # show what would be added
python scripts/track_bill44.py --dry-run --limit 5   # test first 5 documents per source
python scripts/track_bill44.py --recheck             # ignore seen-cache for this run
python scripts/track_bill44.py --review              # list entries awaiting a note
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests
import yaml
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
# Only tracker.json lives in data/, because that is the one Hugo genuinely
# reads. Hugo parses every file in data/ on every build whether a template
# touches it or not, so a typo in the scraper's own config or its URL-hash
# cache would break the website. Keep script-only files out of there.
SOURCES_FILE = ROOT / "scripts" / "tracker_sources.yaml"
DATA_FILE = ROOT / "data" / "tracker.json"
CACHE_FILE = ROOT / "scripts" / "tracker_cache.json"

TIMEOUT = 25
USER_AGENT = (
    "brandonfleming.ca Bill 44 tracker "
    "(+https://brandonfleming.ca/tracker/; contact@brandonfleming.ca)"
)
MAX_DOC_CHARS = 250_000

MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}"
STATUS = r"(?:Active|Approved|Closed|Pending|In Progress|Completed|Deferred)"


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


def clean_surrey_title(raw_text: str) -> str:
    """Clean and format Surrey corporate and planning report titles."""
    text = clean(raw_text)
    text = re.split(r"\bPagination\b", text, flags=re.I)[0].strip()

    # Strip leading date
    text = re.sub(rf"^{MONTH}\s*", "", text, flags=re.I).strip()

    # Corporate reports: truncate abstract at boundary phrase
    abstract_split = re.split(
        r"\s+(?:The (?:intent|purpose) of this [A-Za-z ]*report|This report)\b",
        text,
        maxsplit=1,
        flags=re.I,
    )
    text = abstract_split[0].strip()

    # Planning reports: strip trailing repeated date(s) and status word
    text = re.sub(rf"(?:\s*{MONTH})*\s*{STATUS}\s*$", "", text, flags=re.I).strip()

    # Planning reports: insert comma after report number(s) if missing
    m_plr = re.match(r"^(Planning Report\s+[\d\-]+(?:\s+and\s+[\d\-]+)*)\s+(.*)$", text, re.I)
    if m_plr:
        prefix = m_plr.group(1).strip()
        rest = m_plr.group(2).strip()
        if not rest.startswith(","):
            text = f"{prefix}, {rest}"

    # Clean trailing punctuation
    text = re.sub(r"[\s\-\,\:\.]+$", "", text).strip()

    # Truncate on word boundaries if needed
    if len(text) > 160:
        truncated = text[:157]
        last_space = truncated.rfind(" ")
        if last_space > 80:
            text = truncated[:last_space].rstrip() + "..."
        else:
            text = truncated.rstrip() + "..."

    return text


def compute_keywords_hash(config: dict) -> str:
    """Compute a stable hash of all active keywords across global and source scopes."""
    all_kw = set(config.get("keywords", []))
    for src in config.get("sources", []):
        all_kw.update(src.get("keywords", []))
    normalized = sorted(k.strip().lower() for k in all_kw if k.strip())
    return hashlib.sha1(json.dumps(normalized).encode()).hexdigest()[:12]


def fetch_text(url: str) -> str | None:
    """GET a text URL with retry on transient network errors."""
    for attempt in (1, 2):
        try:
            r = requests.get(url, timeout=TIMEOUT * attempt, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            return r.text
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == 1:
                time.sleep(1)
                continue
            print(f"    ! unreachable: {exc}", file=sys.stderr)
        except requests.RequestException as exc:
            print(f"    ! unreachable: {exc}", file=sys.stderr)
            break
    return None


def fetch_pdf_text(url: str) -> str:
    """Fetch PDF into memory and extract text across readable pages."""
    extracted = []
    try:
        time.sleep(0.5)  # Rate limit requests to municipal servers
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()

        reader = PdfReader(io.BytesIO(r.content), strict=False)
        char_count = 0

        try:
            for page in reader.pages:
                try:
                    t = page.extract_text()
                    if t:
                        extracted.append(t)
                        char_count += len(t)
                        if char_count >= MAX_DOC_CHARS:
                            break
                except Exception:
                    continue
        except Exception:
            pass

        return " ".join(extracted).lower()
    except Exception as exc:
        print(f"    ! failed reading PDF {url}: {exc}", file=sys.stderr)
        return " ".join(extracted).lower()


def score_text(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    """Return (total hit count, matched keywords list)."""
    low = text.lower()
    matched = [k for k in keywords if k.lower() in low]
    hits = sum(low.count(k.lower()) for k in matched)
    return hits, matched


# ------------------------------------------------------------------ sources

def from_rss(xml: str, keywords: list[str], limit: int | None = None) -> list[dict]:
    found = []
    items = re.findall(r"<(?:item|entry)\b.*?</(?:item|entry)>", xml, re.S | re.I)
    if limit is not None:
        items = items[:limit]

    for item in items:
        def tag(name: str) -> str:
            m = re.search(rf"<{name}\b[^>]*>(.*?)</{name}>", item, re.S | re.I)
            return clean(m.group(1)) if m else ""

        title = tag("title")
        if not title:
            continue

        hits, matched = score_text(title, keywords)
        if hits == 0:
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
            "hits": hits,
            "matched": matched,
        })
    return found


def from_drupal(html: str, base_url: str, keywords: list[str],
                match_target: str, seen_ids: set[str],
                new_seen_ids: set[str], limit: int | None = None) -> list[dict]:
    found = []
    blocks = re.split(r'<div\b[^>]*class=["\'][^"\']*views-row[^"\']*["\'][^>]*>', html, flags=re.I)
    eval_count = 0

    for b in blocks[1:]:
        if limit is not None and eval_count >= limit:
            break

        link_m = re.search(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', b, re.I)
        if not link_m:
            continue
        pdf_url = urljoin(base_url, link_m.group(1))
        item_id = entry_id(pdf_url)

        if item_id in seen_ids:
            continue

        eval_count += 1
        new_seen_ids.add(item_id)

        date_m = re.search(r'<time\b[^>]*datetime=["\']([^"T\s]+)', b, re.I)
        item_date = parse_date(date_m.group(1)) if date_m else datetime.now(timezone.utc).strftime("%Y-%m-%d")

        b_clean = re.sub(r'<div\b[^>]*class=["\'][^"\']*listing-view__item-link[^"\']*["\'].*?</div>', " ", b, flags=re.S | re.I)
        display_title = clean_surrey_title(b_clean)

        if match_target == "document":
            doc_text = fetch_pdf_text(pdf_url)
            hits, matched = score_text(doc_text, keywords)
        else:
            hits, matched = score_text(display_title, keywords)

        if hits > 0:
            found.append({
                "id": item_id,
                "title": display_title,
                "url": pdf_url,
                "date": item_date,
                "hits": hits,
                "matched": matched,
            })
    return found


def from_html(html: str, base_url: str, keywords: list[str],
              link_contains: str | None, limit: int | None = None) -> list[dict]:
    found = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    anchors = re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I)
    eval_count = 0

    for href, inner in anchors:
        if limit is not None and eval_count >= limit:
            break

        text = clean(inner)
        if not text or len(text) < 12:
            continue
        if link_contains and link_contains.lower() not in href.lower():
            continue

        eval_count += 1
        hits, matched = score_text(text, keywords)
        if hits == 0:
            continue

        found.append({
            "title": text,
            "url": urljoin(base_url, href),
            "date": today,
            "hits": hits,
            "matched": matched,
        })
    return found


# --------------------------------------------------------------------- main

def collect(sources: list[dict], default_keywords: list[str],
            seen_ids: set[str], new_seen_ids: set[str],
            limit: int | None = None) -> list[dict]:
    results = []
    for src in sources:
        print(f"  -> {src['name']}")
        keywords = src.get("keywords") or default_keywords
        match_target = src.get("match", "title")
        mode = src.get("mode")

        html = fetch_text(src["url"])
        if not html:
            continue

        if mode == "drupal":
            hits = from_drupal(html, src["url"], keywords, match_target, seen_ids, new_seen_ids, limit=limit)
        elif mode == "html":
            hits = from_html(html, src["url"], keywords, src.get("link_contains"), limit=limit)
        else:
            hits = from_rss(html, keywords, limit=limit)

        for hit in hits:
            if "id" not in hit:
                hit["id"] = entry_id(hit["url"])
            hit.update({
                "source": src["name"],
                "jurisdiction": src.get("jurisdiction", ""),
                "type": src.get("type", ""),
                "note": "",
            })
        print(f"    {len(hits)} match{'' if len(hits) == 1 else 'es'}")
        results.extend(hits)
    return results


def load_cache(current_hash: str, recheck: bool = False) -> set[str]:
    if recheck:
        print("  ! --recheck flag active: bypassing seen-cache.")
        return set()
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            cached_hash = data.get("keywords_hash", "")
            if cached_hash != current_hash:
                print("  ! Keywords updated: invalidating seen-cache to re-evaluate sources.")
                return set()
            return set(data.get("seen", []))
        except Exception:
            return set()
    return set()


def save_cache(current_hash: str, seen_ids: set[str]) -> None:
    CACHE_FILE.write_text(
        json.dumps({
            "keywords_hash": current_hash,
            "seen": sorted(seen_ids)
        }, indent=2) + "\n",
        encoding="utf-8"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="don't write tracker.json or update cache")
    ap.add_argument("--review", action="store_true", help="list entries awaiting a note")
    ap.add_argument("--recheck", action="store_true", help="bypass seen-cache for this run")
    ap.add_argument("--limit", "-n", type=int, default=None, help="limit documents evaluated per source")
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
            hits_info = f" (hits: {e.get('hits', 0)}, matched: {', '.join(e.get('matched', []))})" if e.get("hits") else ""
            print(f"  [{e['date']}] {e['title']}{hits_info}\n      {e['url']}\n")
        return 0

    config = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))
    default_keywords = config.get("keywords", [])
    sources = [s for s in config.get("sources", []) if s.get("url")]
    current_hash = compute_keywords_hash(config)

    print(f"Polling {len(sources)} source(s) [keywords hash: {current_hash}]...")
    cached_ids = load_cache(current_hash, recheck=args.recheck)
    seen_ids = set(existing.keys()).union(cached_ids)
    new_seen_ids: set[str] = set()

    candidates = collect(sources, default_keywords, seen_ids, new_seen_ids, limit=args.limit)
    new = [c for c in candidates if c["id"] not in existing]
    print(f"\n{len(new)} new candidate(s).")

    if args.dry_run:
        for c in sorted(new, key=lambda x: x.get("hits", 0), reverse=True):
            hits_str = f" [hits: {c.get('hits', 0)} | {', '.join(c.get('matched', []))}]"
            print(f"  [{c['date']}]{hits_str} {c['title']} ({c['source']})")
        return 0

    if new:
        store["entries"] = sorted(
            list(existing.values()) + new, key=lambda e: e["date"], reverse=True
        )

    store["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    DATA_FILE.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    save_cache(current_hash, seen_ids.union(new_seen_ids))

    pending = sum(1 for e in store["entries"] if not e.get("note"))
    print(f"Wrote {DATA_FILE.relative_to(ROOT)}: {pending} awaiting your note.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
