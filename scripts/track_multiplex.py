"""Count Vancouver multiplex permits, and write them to data/multiplex.json.

    python scripts/track_multiplex.py --facets      # FIRST: find the filter
    python scripts/track_multiplex.py --dry-run     # show what would be written
    python scripts/track_multiplex.py               # write data/multiplex.json

Why this replaced the Bill 44 tracker
-------------------------------------
The Surrey tracker worked, mechanically: 15 clean runs in 10 weeks, 29 entries
collected. What stopped was the part that needed a person. Every entry had to be
read and annotated before it would publish, and the last note was written in
July. The subject moving from Surrey to Vancouver was not the problem; the
weekly homework was.

So this one asks nothing of anybody. It counts permits. If Brandon never opens
it again it keeps being true, which is the only kind of automation worth leaving
switched on.

The source
----------
City of Vancouver open data, `issued-building-permits`, through the Opendatasoft
Explore v2.1 API. Public, no key, documented, and the same dataset the thesis
runs on. The current year is refreshed daily; prior years are static extracts.

What it measures
----------------
Permits issued for multiplexes since R1-1 came into force on 17 October 2023,
against the City's own stated expectation of about 150 projects a year. That
comparison is the whole point: a number the City published, next to what
actually happened.

IMPORTANT, read before trusting any output
------------------------------------------
Issued building permits are not multiplex *applications*. A permit is issued
late, after the application has worked through the queue, so this undercounts
recent activity and always will. The thesis handles that by dating from permit
application and weighting recent months; this page cannot, because the public
dataset is issuance-dated. Say so on the page rather than quietly conflating
them.
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "multiplex.json"

API = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/issued-building-permits/records"

# R1-1 came into force on this date. Everything is measured from here.
IN_FORCE = "2023-10-17"

# The City's stated expectation, from the Shape Your City FAQ. Used only as a
# line of comparison on the page, never as a target or a verdict.
CITY_EXPECTATION_PER_YEAR = 150

# ---------------------------------------------------------------------------
# THE FILTER. This is the one thing that cannot be worked out without running
# --facets against the live API, because it depends on the exact strings the
# City uses in its own fields. Nothing below is a guess that should be trusted
# until Brandon has confirmed it.
#
# Run:  python scripts/track_multiplex.py --facets
#
# then set these to the values that actually identify a multiplex. Leave a
# comment saying which you chose and why, because the next person to read this
# will wonder.
# Settled 26 October 2026 by running --compare. The evidence, permits per year:
#
#          2019  2020  2021  2022  2023   2024  2025  2026
#   A        78    90    89   157   118    145   381   250   category only
#   B         0     0     0     0     0     60   328   234   description  <-- this
#   C         0     0     0     0     0     10   134   173   low density + description
#   D         0     0     0     0     0     16   154   173   low density + category
#
# A is disqualified outright. It reports 78 to 157 permits a year before R1-1
# existed, because Vancouver calls an apartment block a "Multiple Dwelling"
# too. Spot checks on what A catches and B does not: a six-storey
# non-combustible building, a three-storey townhouse block. Not multiplexes.
#
# C and D have the right shape but are roughly half the size, because
# permitcategory is empty on a large share of records. They are not more
# precise than B, they are B with a hole in it.
#
# B is zero in all five pre-policy years and rises afterwards, which is the
# signature of the policy taking effect. It is free-text matching, so it is not
# perfect in either direction: of the 48 permits B catches that A misses, most
# read as multiplexes (one literally begins "R1-1 MULTIPLEX") but at least one
# is an infill single detached house whose description mentions the word. Treat
# the number as good to within a few percent, not exact, and say so on the page.
MULTIPLEX_FILTER = 'typeofwork = \'New Building\' AND search(projectdescription, "multiplex")'
# ---------------------------------------------------------------------------

TIMEOUT = 45


def api(params: dict) -> dict:
    """Query the API, and on failure say what the API actually complained about.

    Opendatasoft returns a JSON body on a 400 naming the offending clause.
    urllib raises HTTPError and throws that body away unless you read it, which
    turns a precise message into a bare "400 Bad Request" and costs a round of
    guessing.
    """
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "brandonfleming.ca tracker"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
            detail = detail.get("message") or detail.get("error_code") or detail
        except Exception:
            detail = "(no readable body)"
        raise RuntimeError(f"HTTP {e.code} from the API: {detail}\n    query: {params}") from None


# ------------------------------------------------------------------- discovery

def facets() -> int:
    """Print the distinct values of the fields that might identify a multiplex.

    This exists because the filter cannot be guessed. The dataset documentation
    names the fields (PropertyUse, TypeofWork, SpecificUseCategory,
    PermitCategory) but not the values inside them, and the difference between
    'Multiple Dwelling' and 'Multiple Conversion Dwelling' decides whether this
    whole page is right or wrong.
    """
    print(f"Fields on the first record, and the values in use since {IN_FORCE}.\n")

    try:
        sample = api({"limit": 1, "where": f"issuedate >= date'{IN_FORCE}'"})
    except Exception as e:
        print(f"Could not reach the API: {e}")
        return 1

    results = sample.get("results") or []
    if not results:
        print("The API returned no records. Check the date filter and the dataset name.")
        return 1

    print("ALL FIELDS on one record, so you can see what else is available:")
    for k, v in sorted(results[0].items()):
        shown = str(v)
        if len(shown) > 70:
            shown = shown[:67] + "..."
        print(f"    {k:28s} {shown}")

    for field in ("propertyuse", "typeofwork", "specificusecategory", "permitcategory"):
        print(f"\n--- {field} " + "-" * (60 - len(field)))
        try:
            page = api({
                "select": field,
                "where": f"issuedate >= date'{IN_FORCE}'",
                "limit": 100,
                "group_by": field,
            })
            rows = page.get("results") or []
            # No truncation. The first version of this cut the list at 40, and
            # since the values come back alphabetically that hid everything
            # from G onwards, including every value with "Multiple" in it.
            for row in rows:
                print("   ", row.get(field))
        except Exception:
            # group_by is not available on every Opendatasoft deployment, so
            # fall back to counting a sample rather than failing the whole run.
            try:
                page = api({"select": field, "where": f"issuedate >= date'{IN_FORCE}'", "limit": 100})
                counts = Counter(str(r.get(field)) for r in page.get("results") or [])
                for value, n in counts.most_common(25):
                    print(f"    {n:5d}  {value}")
                print("    (counts are from a 100-record sample, not the full set)")
            except Exception as e:
                print(f"    could not read this field: {e}")

    print("\nTell me which values mean 'multiplex' and I will write the filter.")
    return 0


# ---------------------------------------------------------------------- probe

CANDIDATES = [
    ("new build, Multiple Dwelling",
     "typeofwork = 'New Building' AND specificusecategory LIKE 'Multiple Dwelling'"),
    ("new build, Multiple Conversion Dwelling",
     "typeofwork = 'New Building' AND specificusecategory LIKE 'Multiple Conversion Dwelling'"),
    ("new build, anything with 'Multiple'",
     "typeofwork = 'New Building' AND specificusecategory LIKE 'Multiple'"),
    ("permitcategory: New Build - Low Density Housing",
     "permitcategory = 'New Build - Low Density Housing'"),
    ("description mentions multiplex",
     'search(projectdescription, "multiplex")'),
    ("new build + description mentions multiplex",
     'typeofwork = \'New Building\' AND search(projectdescription, "multiplex")'),
    ("new build, Dwelling Uses, any",
     "typeofwork = 'New Building' AND propertyuse LIKE 'Dwelling Uses'"),
]


def probe() -> int:
    """Count each candidate filter, so the choice is made on numbers.

    Everything here is a guess about ODSQL syntax as much as about the City's
    vocabulary, so each candidate is run separately and a failure is reported
    rather than raised. A candidate that errors tells us about the query
    language; a candidate that returns a plausible count tells us about the
    data.

    For scale: the City expected about 150 multiplex projects a year, and more
    than 600 applications had been filed by April 2026. A filter returning
    single digits or tens of thousands is the wrong filter.
    """
    print(f"Counting candidate filters, all since {IN_FORCE}.\n")

    for label, clause in CANDIDATES:
        where = f"issuedate >= date'{IN_FORCE}' AND ({clause})"
        try:
            page = api({"where": where, "limit": 3,
                        "select": "permitnumber,issuedate,typeofwork,specificusecategory,"
                                  "permitcategory,projectdescription,geolocalarea"})
        except Exception as e:
            msg = str(e)
            print(f"  {label}\n      FAILED: {msg[:140]}\n")
            continue

        total = page.get("total_count")
        print(f"  {label}\n      {total} permits")
        for r in (page.get("results") or [])[:2]:
            desc = str(r.get("projectdescription") or "")[:90]
            print(f"        {r.get('issuedate')}  {r.get('geolocalarea')}  "
                  f"{r.get('specificusecategory')}")
            print(f"           {desc}")
        print()

    print("Send me this whole block. The count that lands near the City's 150 a\n"
          "year, with descriptions that read like multiplexes, is the filter.")
    return 0


# -------------------------------------------------------------------- compare

FINALISTS = {
    "A  category only":
        "typeofwork = 'New Building' AND specificusecategory LIKE 'Multiple Dwelling'",
    "B  description only":
        'typeofwork = \'New Building\' AND search(projectdescription, "multiplex")',
    "C  low density + description":
        'typeofwork = \'New Building\' AND permitcategory = \'New Build - Low Density Housing\''
        ' AND search(projectdescription, "multiplex")',
    "D  low density + category":
        "typeofwork = 'New Building' AND permitcategory = 'New Build - Low Density Housing'"
        " AND specificusecategory LIKE 'Multiple Dwelling'",
}

DIFFS = {
    "in A but not B (category says Multiple Dwelling, description never says multiplex)":
        'typeofwork = \'New Building\' AND specificusecategory LIKE \'Multiple Dwelling\''
        ' AND NOT search(projectdescription, "multiplex")',
    "in B but not A (description says multiplex, category does not)":
        'typeofwork = \'New Building\' AND search(projectdescription, "multiplex")'
        ' AND NOT specificusecategory LIKE \'Multiple Dwelling\'',
}

YEARS = list(range(2019, datetime.now(timezone.utc).year + 1))


def count(where: str) -> int | str:
    # Errors come back as a short token, not a sentence. A full exception
    # string here is wider than the column and turns the table into soup.
    try:
        return api({"where": where, "limit": 1}).get("total_count")
    except Exception:
        return "err"


def compare() -> int:
    """Count each finalist per year, including years before R1-1 existed.

    This is the real test. R1-1 came into force in October 2023, so a filter
    that genuinely isolates R1-1 multiplexes should be close to nothing in
    2019-2022 and climb through 2024-2025. A filter showing a steady stream
    across every year is catching something else, most likely apartment
    buildings, which Vancouver also calls a Multiple Dwelling.
    """
    print("Permits per year. R1-1 came into force 17 October 2023, so the years\n"
          "before that are the control. Low numbers there mean the filter works.\n")

    head = "  " + "".join(f"{y:>7}" for y in YEARS) + "     total"
    print(head)
    print("  " + "-" * (len(head) - 2))

    for label, clause in FINALISTS.items():
        cells = []
        for y in YEARS:
            # Quoted: issueyear is text. Equality against a bare int is
            # coerced by the API, but relying on that is how the --dry-run
            # query ended up broken.
            cells.append(count(f"{clause} AND issueyear = '{y}'"))
        total = count(f"{clause} AND issuedate >= date'{IN_FORCE}'")
        row = "".join(f"{str(c):>7}" for c in cells)
        print(f"  {row}  {str(total):>8}   {label}")

    print("\n  (total column counts only permits issued since R1-1 came into force)\n")

    for label, clause in DIFFS.items():
        print(f"\n--- {label}")
        n = count(f"issuedate >= date'{IN_FORCE}' AND ({clause})")
        print(f"    {n} permits")
        try:
            page = api({"where": f"issuedate >= date'{IN_FORCE}' AND ({clause})", "limit": 4,
                        "select": "issuedate,geolocalarea,specificusecategory,projectdescription"})
            for r in page.get("results") or []:
                print(f"      {r.get('issuedate')}  {r.get('geolocalarea')}  "
                      f"{r.get('specificusecategory')}")
                print(f"         {str(r.get('projectdescription') or '')[:110]}")
        except Exception as e:
            print(f"    could not sample: {str(e)[:80]}")

    print("\nSend me the table. The filter whose pre-2023 numbers are near zero is\n"
          "the one that is actually measuring R1-1.")
    return 0


# ----------------------------------------------------------------- collection

def tally(where: str, field: str) -> dict[str, int]:
    """Count records grouped by one field, server side.

    The first version of this paged through every matching record and counted
    them here, which meant eight requests, an offset loop, and an order_by that
    the API rejected outright. The API will group and count for us in one
    request, so it does.
    """
    page = api({
        "where": where,
        "group_by": field,
        "select": f"{field}, count(*) as permits",
        "limit": 100,
    })
    out = {}
    for row in page.get("results") or []:
        key = row.get(field)
        if key is None:
            continue
        out[str(key)] = int(row.get("permits") or 0)
    return out


def build() -> dict:
    # Everything from 2019, not just from the policy date. The five empty years
    # before R1-1 are the most convincing thing on the page: they are what turn
    # a number into evidence that the number is about this policy.
    # Range-filter on issuedate, not issueyear. issueyear is a TEXT field, so
    # `issueyear >= 2019` is a text-to-int comparison and the API rejects it
    # outright. Equality happens to be coerced, which is why `issueyear = 2019`
    # worked in --compare and hid this.
    all_years = f"issuedate >= date'2019-01-01' AND ({MULTIPLEX_FILTER})"
    since_policy = f"issuedate >= date'{IN_FORCE}' AND ({MULTIPLEX_FILTER})"

    print(f"  filter: {MULTIPLEX_FILTER}")
    by_year = tally(all_years, "issueyear")
    by_month = tally(since_policy, "yearmonth")
    by_area = tally(since_policy, "geolocalarea")

    since = sum(by_month.values())
    print(f"  {since} permits since R1-1, {sum(by_year.values())} from 2019 onwards")

    # group_by returns no row at all for a count of zero, so the pre-policy
    # years come back missing rather than empty. Those five zeros are the
    # entire argument that this number is about R1-1 and not about Vancouver
    # building things in general, so put them back explicitly.
    this_year = datetime.now(timezone.utc).year
    for y in range(2019, this_year + 1):
        by_year.setdefault(str(y), 0)
    first = datetime.strptime(IN_FORCE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - first).days / 365.25

    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "City of Vancouver open data, issued building permits",
        "source_url": "https://opendata.vancouver.ca/explore/dataset/issued-building-permits/",
        "in_force": IN_FORCE,
        "filter": MULTIPLEX_FILTER,
        "total_since_in_force": since,
        "per_year": round(since / elapsed, 1) if elapsed > 0 else None,
        "city_expectation_per_year": CITY_EXPECTATION_PER_YEAR,
        # The gap between R1-1 coming into force and the first permit actually
        # being issued. A finding in its own right, and the clearest evidence
        # on the page that these are issuances rather than applications.
        "first_permit_month": min(by_month) if by_month else None,
        "years": [{"year": y, "permits": by_year[y]} for y in sorted(by_year)],
        "months": [{"month": m, "permits": by_month[m]} for m in sorted(by_month)],
        "areas": [{"area": a, "permits": n}
                  for a, n in sorted(by_area.items(), key=lambda kv: -kv[1])],
    }


# ---------------------------------------------------------------------- units
#
# How many homes each permit is for. There is no units field in the dataset, so
# the number has to come out of the City's free-text project description. That
# is only worth doing if the descriptions say it consistently, which is what
# --units is for: it shows what this pattern finds and, more usefully, what it
# misses. Do not put a unit breakdown on the page until that has been run.

UNIT_WORDS = {"three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
UNIT_RE = re.compile(
    r"\b(\d{1,2}|three|four|five|six|seven|eight)\b"      # the number
    r"(?:\s*\(\d{1,2}\))?"                                  # "six (6)"
    r"[\s-]*(?:new\s+)?(?:strata\s+|secured\s+rental\s+|rental\s+)?"
    r"(?:dwelling\s+|residential\s+)?units?\b", re.I)
PLEX_RE = re.compile(r"\b(three|four|five|six|seven|eight)plex\b", re.I)


def extract_units(desc: str | None) -> int | None:
    """Homes on one R1-1 permit, or None when the description does not say.

    R1-1 allows three to eight, so anything outside that range is something
    else in the text (a storey count, a parking count, a secondary suite) and
    is ignored rather than trusted.
    """
    text = desc or ""
    for m in UNIT_RE.finditer(text):
        raw = m.group(1).lower()
        n = UNIT_WORDS.get(raw) or (int(raw) if raw.isdigit() else None)
        if n and 3 <= n <= 8:
            return n
    m = PLEX_RE.search(text)
    return UNIT_WORDS[m.group(1).lower()] if m else None


def units_probe() -> int:
    where = f"issuedate >= date'{IN_FORCE}' AND ({MULTIPLEX_FILTER})"
    page = api({"where": where, "limit": 100,
                "select": "permitnumber,issuedate,projectdescription"})
    rows = page.get("results") or []
    found = [(r, extract_units(r.get("projectdescription"))) for r in rows]

    tally = Counter(n for _, n in found)
    print(f"Unit counts read from {len(rows)} of {page.get('total_count')} multiplex permits:\n")
    for n in sorted(k for k in tally if k):
        print(f"    {n} homes   {tally[n]:4d}")
    print(f"    not stated {tally[None]:4d}   <- the number that decides whether this is usable\n")

    print("FOUND, to check the pattern read them correctly:")
    for r, n in [x for x in found if x[1]][:4]:
        print(f"  [{n}]  {str(r.get('projectdescription'))[:220]}\n")
    print("MISSED, to see how else the City writes it:")
    for r, n in [x for x in found if not x[1]][:8]:
        print(f"  [-]  {str(r.get('projectdescription'))[:220]}\n")
    return 0


# ----------------------------------------------------------------------- news
#
# Headlines about R1-1 and multiplexes, gathered from three sources and stored
# as title, link, outlet and date. Never the article text: copying other
# people's reporting into this repo would be both a copyright problem and the
# wrong thing to publish. The description is read to decide whether a story
# matches, then discarded.
#
# Expect this to be sparse. On 14 November 2026 not one current Daily Hive
# Urbanized headline and not one BC Government housing release mentioned
# multiplexes. R1-1 makes the news in bursts, a few times a year. That is why
# matches accumulate across runs instead of being replaced each week: the feeds
# only ever show their latest twenty or thirty items, and a story that matched
# in March is still worth listing in November.
#
# Sources considered and rejected, so nobody re-adds them:
#   Google News search RSS  robots.txt disallows automated fetching
#   Business in Vancouver   /rss refused the request outright
#   CBC British Columbia    the old feed URL refused the request

NEWS_SOURCES = [
    # The City's own announcements. Not a feed, a server-rendered listing of
    # every news release, so links are read straight from the page. Everything
    # on it is about Vancouver, so no place check.
    {"name": "City of Vancouver", "kind": "html",
     "url": "https://vancouver.ca/news-calendar/all-news-listing.aspx",
     "link_contains": "/news-calendar/", "need_place": False},
    {"name": "Daily Hive", "kind": "rss",
     "url": "https://dailyhive.com/feed/urbanized", "need_place": True},
    {"name": "BC Government", "kind": "rss",
     "url": "https://news.gov.bc.ca/ministries/housing-and-municipal-affairs/feed",
     "need_place": True},
]

NEWS_KEEP = 30

TOPIC = re.compile(r"\br1-1\b|multiplex|missing[- ]middle|small[- ]scale multi[- ]unit"
                   r"|\bssmuh\b|fourplex|sixplex", re.I)
R1_1 = re.compile(r"\br1-1\b", re.I)
PLACE = re.compile(r"vancouver", re.I)
# A multiplex is also a cinema. Without this, a story about a new theatre
# complex would land on a page about housing.
NOT_HOUSING = re.compile(r"cinema|movie|theatre|theater|cineplex|imax", re.I)

UA = "Mozilla/5.0 (compatible; brandonfleming.ca R1-1 tracker; +https://brandonfleming.ca/tracker/)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def clean(text: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", htmllib.unescape(text)).strip()


def iso_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d")      # RSS
    except Exception:
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%Y-%m-%d")  # Atom
    except Exception:
        return None


def first_child(el, *names):
    """The first child whose local tag name is in names.

    Written out longhand because `el.find('a') or el.find('b')` is a trap: an
    ElementTree element with no children is falsy, so a perfectly good <title>
    with text in it fails the `or` and the fallback wins.
    """
    for name in names:
        for c in el:
            if c.tag.rsplit("}", 1)[-1] == name:
                return c
    return None


def parse_rss(raw: bytes) -> list[dict]:
    # The BC Government feed opens with a byte-order mark, which the parser
    # rejects as content before the XML declaration.
    root = ET.fromstring(raw.lstrip(b"\xef\xbb\xbf"))
    out = []
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] not in ("item", "entry"):
            continue
        t = first_child(el, "title")
        l = first_child(el, "link")
        d = first_child(el, "pubDate", "published", "updated")
        s = first_child(el, "description", "summary")
        link = ""
        if l is not None:
            link = (l.text or l.get("href") or "").strip()
        if not link:
            continue
        out.append({
            "title": clean(t.text if t is not None else ""),
            "url": link,
            "date": iso_date(d.text if d is not None else None),
            "_desc": clean(s.text if s is not None else ""),   # matching only
        })
    return out


def parse_listing(raw: bytes, base: str, link_contains: str) -> list[dict]:
    html = raw.decode("utf-8", "replace")
    out, seen = [], set()
    for href, inner in re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
        title = clean(inner)
        if len(title) < 12 or link_contains not in href:
            continue
        url = urllib.parse.urljoin(base, href)
        if url in seen:
            continue
        seen.add(url)
        # The listing carries no dates. See seed handling in collect_news.
        out.append({"title": title, "url": url, "date": None, "_desc": ""})
    return out


def matches(item: dict, need_place: bool) -> bool:
    text = f"{item['title']} {item['_desc']}"
    if NOT_HOUSING.search(text) or not TOPIC.search(text):
        return False
    if need_place and not (PLACE.search(text) or R1_1.search(text)):
        return False
    return True


def collect_news(previous: list[dict], seeding: bool) -> tuple[list[dict], list[str]]:
    """Merge this week's matches into everything matched before.

    Dates. RSS items carry their own. The City listing does not, so a City
    headline is dated the week it first appears here, which is accurate to
    within the week for anything new. The exception is the very first run,
    which picks up the City's whole back catalogue at once: stamping a 2023
    announcement with today's date would be a lie, so those are stored
    undated and shown without a date, at the bottom.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    kept = {n["url"]: n for n in previous}
    report = []

    for src in NEWS_SOURCES:
        try:
            raw = fetch(src["url"])
            items = (parse_rss(raw) if src["kind"] == "rss"
                     else parse_listing(raw, src["url"], src["link_contains"]))
        except Exception as e:
            report.append(f"{src['name']:18s} FAILED  {str(e)[:90]}")
            continue

        hits = [i for i in items if matches(i, src["need_place"])]
        new = 0
        for i in hits:
            if i["url"] in kept:
                continue     # keep the first record, and the date it was first seen
            date = i["date"] or (None if seeding else today)
            kept[i["url"]] = {"title": i["title"], "url": i["url"],
                              "outlet": src["name"], "date": date}
            new += 1
        report.append(f"{src['name']:18s} {len(items):4d} items  {len(hits):3d} match  {new:3d} new")

    news = sorted(kept.values(), key=lambda n: n.get("date") or "0000", reverse=True)
    return news[:NEWS_KEEP], report


def news_only() -> int:
    """Check every source and show what matched, without writing anything."""
    print("Checking news sources (nothing is written)...\n")
    news, report = collect_news([], seeding=True)
    for line in report:
        print("  " + line)
    print(f"\n{len(news)} matching headlines:\n")
    for n in news:
        print(f"  {n.get('date') or 'undated':10s}  {n['outlet']:18s}  {n['title'][:80]}")
    return 0



def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--facets", action="store_true",
                    help="print the distinct field values, to work out the filter")
    ap.add_argument("--probe", action="store_true",
                    help="count several candidate filters and show sample rows")
    ap.add_argument("--compare", action="store_true",
                    help="count the finalists per year, including before R1-1 existed")
    ap.add_argument("--units", action="store_true",
                    help="test reading unit counts out of the permit descriptions")
    ap.add_argument("--news", action="store_true",
                    help="check the news sources and list matches, writing nothing")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the result instead of writing data/multiplex.json")
    args = ap.parse_args(argv)

    if args.facets:
        return facets()

    if args.probe:
        return probe()

    if args.compare:
        return compare()

    if args.news:
        return news_only()

    if args.units:
        return units_probe()

    if not MULTIPLEX_FILTER:
        print("MULTIPLEX_FILTER is not set yet, so there is nothing to count.\n"
              "Run `python scripts/track_multiplex.py --facets` first and send me\n"
              "the output. Writing a guessed filter would produce a number on a\n"
              "public page that nobody could check.")
        return 2

    previous = {}
    if DATA_FILE.exists():
        try:
            previous = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}

    # Permits are the substance. If the City's API is down, stop without
    # touching the file, so last week's numbers stay up rather than vanishing.
    print("Counting Vancouver multiplex permits...")
    try:
        data = build()
    except Exception as e:
        print(f"Failed: {e}")
        return 1

    # News is a garnish and its sources come and go. A failure in one source,
    # or all of them, keeps the headlines already collected and carries on.
    print("\nGathering R1-1 headlines...")
    try:
        news, report = collect_news(previous.get("news") or [],
                                    seeding="news" not in previous)
        for line in report:
            print("  " + line)
        data["news"] = news
    except Exception as e:
        print(f"  news failed, keeping the previous {len(previous.get('news') or [])}: {e}")
        data["news"] = previous.get("news") or []

    if args.dry_run:
        print(json.dumps(data, indent=2)[:3000])
        return 0

    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {DATA_FILE.relative_to(ROOT)}: {data['total_since_in_force']} permits "
          f"since R1-1, about {data['per_year']} a year against the City's "
          f"{CITY_EXPECTATION_PER_YEAR}; {len(data['news'])} headlines.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
