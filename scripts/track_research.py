"""Newest open-access research on upzoning, for /research/.

    python scripts/track_research.py --dry-run    # show what would be written
    python scripts/track_research.py              # write data/research.json

Source: OpenAlex (api.openalex.org), an open index of scholarly work built to
be queried by scripts like this one. No key, and no email address is sent: the
"polite pool" asks for one, but this makes one request a week and does not
need it. OpenAlex reports a nominal per-request cost in its responses; one
request a week is negligible.

What gets listed
----------------
Articles with "upzoning" in the title or abstract, open access, newest first,
and then two stricter tests applied here, because a research list on a
researcher's own site reads as an endorsement:

  * the primary source must be a journal, which drops preprint servers and
    university repositories (peer review is the point), and
  * the primary location itself must be free to read, so the link goes to the
    published version and not to a paywall with a free copy elsewhere.

On 15 November 2026 that kept 6 of the 10 newest results: Urban Studies,
JAPA, Urban Policy and Research, Economic Inquiry and others, and dropped a
Zenodo preprint, two repository working papers and a paywalled version.

The trap this is built around
-----------------------------
A malformed OpenAlex query does not return an error. It silently drops the
filter and returns everything in the index, newest first, which on the day
this was written meant veterinary case reports and a fruit-fly proteome dated
2050. An unattended job would have published those. So the response is
checked before anything is used: a filter that worked returns tens of
results, a dropped one returns hundreds of millions, and anything over
MAX_PLAUSIBLE stops the run without touching the file.

Only title, authors, journal, date and link are stored. Never the abstract:
OpenAlex carries abstracts, but they belong to their publishers.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "research.json"

API = "https://api.openalex.org/works"
QUERY = {
    "filter": "title_and_abstract.search:upzoning,is_oa:true,type:article",
    "sort": "publication_date:desc",
    "per-page": "50",
    "select": "id,title,publication_date,doi,authorships,primary_location",
}

KEEP = 12
MAX_PLAUSIBLE = 5000      # a working filter returned 65; a dropped one, 328 million
TIMEOUT = 45
UA = "brandonfleming.ca research list (+https://brandonfleming.ca/research/)"


def fetch() -> dict:
    url = API + "?" + urllib.parse.urlencode(QUERY)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from OpenAlex: {e.read()[:300]!r}") from None


def authors(work: dict) -> str:
    names = [a.get("author", {}).get("display_name") for a in work.get("authorships") or []]
    names = [n for n in names if n]
    if not names:
        return ""
    surname = lambda n: n.split()[-1]
    if len(names) == 1:
        return surname(names[0])
    if len(names) == 2:
        return f"{surname(names[0])} and {surname(names[1])}"
    return f"{surname(names[0])} et al."


def build(payload: dict) -> list[dict]:
    count = (payload.get("meta") or {}).get("count")
    if count is None or count > MAX_PLAUSIBLE:
        raise RuntimeError(
            f"OpenAlex matched {count} works. A working filter matches tens; this "
            f"looks like the filter was silently dropped. Not writing anything.")

    out = []
    for w in payload.get("results") or []:
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        if src.get("type") != "journal" or not loc.get("is_oa"):
            continue
        url = loc.get("landing_page_url") or w.get("doi")
        if not (w.get("title") and url):
            continue
        out.append({
            "title": " ".join(w["title"].split()),
            "authors": authors(w),
            "journal": src.get("display_name") or "",
            "date": w.get("publication_date") or "",
            "url": url,
        })
        if len(out) == KEEP:
            break
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print, do not write")
    args = ap.parse_args(argv)

    print("Asking OpenAlex for open-access upzoning research...")
    try:
        payload = fetch()
        papers = build(payload)
    except Exception as e:
        print(f"Failed, keeping the previous list: {e}")
        return 1

    print(f"  {payload['meta']['count']} matched, {len(papers)} kept after the journal "
          f"and free-to-read checks")
    for p in papers:
        print(f"    {p['date']}  {p['journal'][:28]:28s}  {p['title'][:60]}")

    data = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "source": "OpenAlex", "papers": papers}
    if args.dry_run:
        return 0
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    print(f"Wrote {DATA_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
