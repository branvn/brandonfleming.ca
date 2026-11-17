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

    # Projects, not permits: a multiplex gets one permit per building, and the
    # City gives each building its own civic number. See the grouping section.
    rows = json.loads(fetch(EXPORT + "?" + urllib.parse.urlencode({
        "where": since_policy,
        "select": "address,projectdescription,issuedate"})).decode("utf-8"))
    ids = adjacency_groups(rows, PROJECT_NUM_GAP, PROJECT_DAY_GAP, use_dp=True)
    start: dict = {}
    for r, g in zip(rows, ids):
        d = str(r.get("issuedate"))[:10]
        if g not in start or d < start[g]:
            start[g] = d            # a project is dated by its first permit
    proj_year = Counter(d[:4] for d in start.values())
    proj_month = Counter(d[:7] for d in start.values())
    rule = {"num_gap": PROJECT_NUM_GAP, "day_gap": PROJECT_DAY_GAP,
            **score_rule(rows, PROJECT_NUM_GAP, PROJECT_DAY_GAP)}
    print(f"  {len(start)} projects (rule precision {rule['precision']:.0%}, "
          f"recall {rule['recall']:.0%} against {rule['known_projects']} known)")

    # group_by returns no row at all for a count of zero, so the pre-policy
    # years come back missing rather than empty. Those five zeros are the
    # entire argument that this number is about R1-1 and not about Vancouver
    # building things in general, so put them back explicitly.
    this_year = datetime.now(timezone.utc).year
    for y in range(2019, this_year + 1):
        by_year.setdefault(str(y), 0)
    first = datetime.strptime(IN_FORCE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - first).days / 365.25

    running, years_out = 0, []
    for y in range(2019, this_year + 1):
        running += proj_year.get(str(y), 0)
        years_out.append({"year": str(y), "projects": proj_year.get(str(y), 0),
                          "running_total": running})
    # The fair comparison with the City's expectation is a complete calendar
    # year. Averaging from October 2023 includes eight months before the first
    # permit was issued, which drags the rate down for reasons that are about
    # permit processing, not uptake.
    full = str(this_year - 1)

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
        "projects_since_in_force": len(start),
        "projects_per_year": round(len(start) / elapsed, 1) if elapsed > 0 else None,
        "last_full_year": {"year": full, "projects": proj_year.get(full, 0)},
        "project_years": years_out,
        "project_months": [{"month": m, "projects": proj_month[m]} for m in sorted(proj_month)],
        "project_rule": rule,
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


# Homes per PROJECT, not per permit. The first --units run (15 November)
# read a count from only 26% of permits, because the City describes buildings:
# "a three-storey 3-unit front building and a two-storey 1-unit rear building".
# Some projects put every building in one permit; some file one permit per
# building; some repeat the whole-project description on every permit. So
# each permit is read as a set of buildings by position (front, rear, east,
# west, or unplaced), and a project takes the largest figure seen for each
# position across its permits. Identical repeats then count once, and a front
# permit plus a rear permit add up.

UNIT_N = r"(\d|one|two|three|four|five|six|seven|eight|single)"
NUMS = {"one": 1, "single": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8}
POS = r"(front|rear|east|west|north|south)"

# Words that may sit between "unit" and "building": "Passive House",
# "***PART 5***", "for the". Never "with", "and" or "having", which start the
# next clause and would let one building's count attach to another.
GAP = r"(?:(?!(?:with|and|having)\b)[\w*()&]+\s+){0,3}?"
BUILDING_RE = re.compile(
    r"\b" + UNIT_N + r"[\s-]+(?:dwelling\s+)?units?\s+" + GAP +
    r"(?:" + POS + r"\s+(?:\(\w+\)\s+)?)?(buildings?)", re.I)
# "Building 2 - To construct two dwelling units": a per-building permit that
# never says front or rear. The building number stands in for the position.
DWELLING_RE = re.compile(r"\b" + UNIT_N + r"[\s-]+dwelling\s+units?\b", re.I)
LABEL_RE = re.compile(r"\bBuilding\s+(\d)\b", re.I)
# How many of a plural building, read from just before it: "two, three-story
# 2-unit front buildings". Found after the building, not as part of one
# pattern: when it was a single pattern, the words allowed between the count
# and the building could swallow the count itself, and DP-2024-00034 read as
# 3 homes instead of 6. "two-storey" is a height, never a count.
MULTIPLIER_RE = re.compile(
    r"\b(two|three|four|2|3|4)\b(?!\s*-?\s*stor(?:e)?y),?\s+(?:[a-z0-9-]+\s+){0,3}$", re.I)
FAMILY_RE = re.compile(
    r"\b(one|two|single|1|2)[\s-]+family\s+dwelling(?:\s+building)?"
    r"(?:\s+(?:building\s+)?(?:at|in)\s+the\s+" + POS + r")?", re.I)
CONTAINING_RE = re.compile(
    r"(?:building|multiplex\W*)\s+containing\s+" + UNIT_N +
    r"[\s-]+(?:(?:dwelling|strata)\s+units?|units?|dwellings)"
    r"(?:\s+(?:at|in)\s+the\s+" + POS + r")?", re.I)
WHOLE_RE = re.compile(r"\b" + UNIT_N + r"[\s-]+units?\s+(?:multiple\s+dwelling|multiplex)", re.I)
TOTAL_RE = re.compile(r"total\s+of\s+" + UNIT_N + r"\s+(?:dwelling\s+|strata\s+|residential\s+)?units?", re.I)


def _n(word: str) -> int:
    w = word.lower()
    return NUMS.get(w) or (int(w) if w.isdigit() else 0)


def read_buildings(desc: str | None) -> tuple[dict[str, int], int]:
    """({position: homes}, stated total) for one permit description."""
    text = " ".join((desc or "").replace("“", '"').replace("”", '"').split())
    found: dict[str, int] = {}

    def put(pos, homes):
        key = (pos or "unplaced").lower()
        found[key] = max(found.get(key, 0), homes)

    for m in BUILDING_RE.finditer(text):
        n, pos, plural = m.group(1), m.group(2), m.group(3)
        k = 1
        if plural.lower().endswith("s"):
            before = MULTIPLIER_RE.search(text[max(0, m.start() - 45):m.start()])
            if before:
                k = _n(before.group(1))
        put(pos, k * _n(n))
    for m in FAMILY_RE.finditer(text):
        put(m.group(2), _n(m.group(1)))
    for m in CONTAINING_RE.finditer(text):
        put(m.group(2), _n(m.group(1)))
    if not found:
        label = LABEL_RE.search(text)
        for m in DWELLING_RE.finditer(text):
            put(f"building {label.group(1)}" if label else None, _n(m.group(1)))
    if not found:
        for m in WHOLE_RE.finditer(text):
            put(None, _n(m.group(1)))
    if not found:
        n = extract_units(text)          # "with 5 units", "a sixplex"
        if n:
            put(None, n)
    total = max([_n(m.group(1)) for m in TOTAL_RE.finditer(text)] or [0])
    return found, total


def project_homes(descs: list[str]) -> int:
    """Homes in one project, from all of its permits' descriptions.

    Two ways a project's permits can be written, and they need different
    arithmetic:

      * one permit describes the whole project ("a 3-unit front building and
        a 1-unit rear building"). Then that description is the count, and any
        other permit for one of those buildings must not be added on top. On
        17 November that mistake produced two 10-home projects: a whole-project
        permit plus a "Building 2" permit that matched neither front nor rear.
      * each permit describes one building. Then the buildings add up, taking
        the largest figure per position so identical repeats count once.
    """
    by_pos: dict[str, int] = {}
    stated, whole = 0, 0
    for d in descs:
        found, total = read_buildings(d)
        stated = max(stated, total)
        if len(found) >= 2:                       # describes several buildings
            whole = max(whole, sum(found.values()))
        for pos, homes in found.items():
            by_pos[pos] = max(by_pos.get(pos, 0), homes)
    if stated or whole:
        return max(stated, whole)
    return sum(by_pos.values())


def units_probe() -> int:
    """How many homes per project, and how many projects that can be read for.

    Probe only. Nothing here reaches the page until the share of projects
    with a plausible reading (3 to 8 homes, R1-1's range) is known, and the
    misses have been looked at.
    """
    where = f"issuedate >= date'{IN_FORCE}' AND ({MULTIPLEX_FILTER})"
    rows = json.loads(fetch(EXPORT + "?" + urllib.parse.urlencode({
        "where": where, "select": "address,projectdescription,issuedate"})).decode("utf-8"))
    ids = adjacency_groups(rows, PROJECT_NUM_GAP, PROJECT_DAY_GAP, use_dp=True)
    projects: dict = {}
    for r, g in zip(rows, ids):
        projects.setdefault(g, []).append(r.get("projectdescription") or "")
    homes = {g: project_homes(d) for g, d in projects.items()}

    n = len(homes)
    read = [h for h in homes.values() if h]
    plausible = [h for h in read if 3 <= h <= 8]
    dist = Counter(homes.values())
    print(f"{len(rows)} permits, {n} projects.\n")
    print(f"  projects with a home count read     {len(read):4d}  ({len(read)/n:.0%})")
    print(f"  of those, 3 to 8 homes (plausible)   {len(plausible):4d}  ({len(plausible)/n:.0%} of all projects)")
    print(f"  homes in the plausible projects      {sum(plausible):4d}\n")
    print("  homes per project:")
    for k in sorted(dist):
        print(f"    {('not read' if k == 0 else str(k)):>8}  {dist[k]:4d}")

    def show(label, test, limit=6):
        print(f"\n{label}")
        shown = 0
        for g, h in homes.items():
            if test(h) and shown < limit:
                shown += 1
                for d in projects[g][:2]:
                    print(f"   [{h}]  {' '.join(d.split())[:170]}")
                print()
    show("NOT READ, to see how else the City writes it:", lambda h: h == 0)

    # The halves: projects of 1 or 2 homes are mostly a front or rear building
    # whose other half landed in a different project. Show where and when, so
    # the reason the grouping missed them can be seen rather than guessed.
    print("\nHALVES (1 or 2 homes): address, date and what each permit describes")
    rows_by_group: dict = {}
    for r, g in zip(rows, ids):
        rows_by_group.setdefault(g, []).append(r)
    shown = 0
    for g, h in homes.items():
        if 1 <= h <= 2 and shown < 12:
            shown += 1
            for r in rows_by_group[g][:2]:
                found, _ = read_buildings(r.get("projectdescription"))
                print(f"   [{h}]  {str(r.get('issuedate'))[:10]}  {(r.get('address') or '(no address)')[:44]:44s}  {found}")
    print("   (addresses are printed here only; nothing is written or published)")
    show("OUTSIDE 3 TO 8, to check whether the reading or the project is odd:", lambda h: h and not 3 <= h <= 8)
    print("Send me this. Coverage decides whether homes per project goes on the page.")
    return 0

# ------------------------------------------------------------------- projects
#
# Building permits are per building. The --units run on 15 November showed it
# plainly: DP-2024-00603 had one permit for "a three-storey 3-unit front
# building and a two-storey 1-unit rear building" and a second for "a
# two-storey 1-unit rear building". A typical multiplex is a front building
# plus a rear one, so counting permits counts buildings, and setting that
# against the City's expectation of 150 *projects* a year overstated uptake.
#
# --projects measures the gap two independent ways: distinct addresses (one
# lot, one project) and distinct development permit numbers (DP-YYYY-NNNNN,
# which the City uses for the project as a whole). If they agree, either can
# replace the permit count.

EXPORT = API.replace("/records", "/exports/json")
DP_RE = re.compile(r"\bDP-\d{4}-\d{5}\b")


def projects_probe() -> int:
    where = f"issuedate >= date'{IN_FORCE}' AND ({MULTIPLEX_FILTER})"
    url = EXPORT + "?" + urllib.parse.urlencode({
        "where": where, "select": "address,projectdescription,issuedate,permitnumber"})
    rows = json.loads(fetch(url).decode("utf-8"))
    print(f"{len(rows)} multiplex building permits since R1-1.\n")

    by_addr: dict[str, list] = {}
    for r in rows:
        by_addr.setdefault((r.get("address") or "?").strip().upper(), []).append(r)
    dps = [DP_RE.search(r.get("projectdescription") or "") for r in rows]
    dp_ids = {m.group(0) for m in dps if m}

    per = Counter(len(v) for v in by_addr.values())
    print(f"  distinct addresses             {len(by_addr):5d}")
    print(f"  permits naming a DP number     {sum(1 for m in dps if m):5d} of {len(rows)}")
    print(f"  distinct DP numbers named      {len(dp_ids):5d}\n")
    print("  permits per address:")
    for k in sorted(per):
        print(f"    {k} permit{'s' if k > 1 else ' '}  {per[k]:5d} addresses")

    # Projects per year, dated by each address's first permit.
    first = Counter(min(str(r.get("issuedate"))[:4] for r in v) for v in by_addr.values())
    print("\n  projects (distinct addresses) by year of first permit:")
    for y in sorted(first):
        print(f"    {y}  {first[y]:4d}")

    print("\nTHREE ADDRESSES WITH MORE THAN ONE PERMIT, to check they are one project:")
    shown = 0
    for addr, v in by_addr.items():
        if len(v) < 2 or shown == 3:
            continue
        shown += 1
        print(f"\n  {addr}")
        for r in v:
            print(f"    {r.get('issuedate')}  {str(r.get('projectdescription'))[:150]}")
    # The decisive test. Address grouping and DP grouping disagreed on
    # 15 November (644 addresses for 650 permits, but 101 DP numbers for 161
    # permits). If one DP's permits sit at different addresses, the address
    # count is hiding multi-building projects and the DP ratio is the truth.
    by_dp: dict[str, list] = {}
    for r in rows:
        m = DP_RE.search(r.get("projectdescription") or "")
        if m:
            by_dp.setdefault(m.group(0), []).append(r)
    multi = {dp: v for dp, v in by_dp.items() if len(v) > 1}
    same = sum(1 for v in multi.values()
               if len({(r.get("address") or "?").strip().upper() for r in v}) == 1)
    print(f"\nDP NUMBERS WITH MORE THAN ONE PERMIT: {len(multi)}")
    print(f"  all permits at the same address   {same:4d}")
    print(f"  permits at different addresses    {len(multi) - same:4d}   <- if large, addresses undercount projects")
    for dp, v in list(multi.items())[:5]:
        print(f"\n  {dp}")
        for r in v:
            print(f"    {(r.get('address') or '(no address)')[:48]:48s}  {str(r.get('projectdescription'))[60:140]}")

    print("\nNothing here is written or published. Addresses stay on your machine.")
    return 0


# ------------------------------------------------------------------- grouping
#
# --projects on 15 November settled what a project looks like in this data:
# of 49 development permits with more than one building permit, 48 had their
# permits at DIFFERENT addresses. The City gives each building its own civic
# number, so one multiplex at 5963-5969 Granville is four permits at four
# addresses. Address counting cannot see that.
#
# Only 161 of 650 permits name their DP number, so DP grouping alone cannot
# count projects either. --grouping tests a rule that can: same street,
# civic numbers within NUM_GAP of each other, issued within DAY_GAP days. It
# is scored against the 101 DP projects whose answer is already known, before
# it is trusted on the 489 permits that name no DP.

# Chosen by --grouping on 15 November 2026, scored against the 101 projects
# whose permits name their development permit:
#
#   civic gap  days   precision  recall   all-permit estimate
#        2      120      100%      78%         380
#        4      120      100%      88%         373   <-- this
#        8      120       99%      88%         368
#       12      365       99%      88%         362
#
# Gap 4 is the widest that never joins two different projects; widening it
# finds nothing more and starts making mistakes. Recall below 100% means some
# multi-building projects stay split, so the project count runs slightly
# high, never low. The rule is re-scored on every run and stored with the
# data, and check_site.py fails if it degrades.
PROJECT_NUM_GAP = 4
PROJECT_DAY_GAP = 120

ADDR_RE = re.compile(r"^\s*(\d+)[A-Z]?\s+([^,]+)", re.I)


def parse_addr(addr: str | None) -> tuple[int, str] | None:
    m = ADDR_RE.match(addr or "")
    return (int(m.group(1)), " ".join(m.group(2).upper().split())) if m else None


def adjacency_groups(rows: list[dict], num_gap: int, day_gap: int,
                     use_dp: bool) -> list[int]:
    """Group permits into projects. Returns a project id per row.

    Union-find: two permits join when they share a DP number (if use_dp), or
    sit on the same street within num_gap civic numbers and day_gap days.
    """
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        parent[find(a)] = find(b)

    if use_dp:
        seen = {}
        for i, r in enumerate(rows):
            m = DP_RE.search(r.get("projectdescription") or "")
            if m:
                if m.group(0) in seen:
                    union(i, seen[m.group(0)])
                else:
                    seen[m.group(0)] = i

    by_street: dict[str, list] = {}
    for i, r in enumerate(rows):
        a = parse_addr(r.get("address"))
        if a:
            d = datetime.strptime(str(r.get("issuedate"))[:10], "%Y-%m-%d")
            by_street.setdefault(a[1], []).append((a[0], d, i))
    for items in by_street.values():
        items.sort()
        for j, (n1, d1, i1) in enumerate(items):
            for n2, d2, i2 in items[j + 1:]:
                if n2 - n1 > num_gap:
                    break
                if abs((d2 - d1).days) <= day_gap:
                    union(i1, i2)
    return [find(i) for i in range(len(rows))]


def pairs(ids: list) -> set:
    by: dict = {}
    for k, g in enumerate(ids):
        by.setdefault(g, []).append(k)
    return {(a, b) for v in by.values() for x, a in enumerate(v) for b in v[x + 1:]}


def score_rule(rows: list[dict], num_gap: int, day_gap: int) -> dict:
    """How well the address rule reproduces the projects known from DP numbers."""
    known = [r for r in rows if DP_RE.search(r.get("projectdescription") or "")]
    truth_ids = [DP_RE.search(r["projectdescription"]).group(0) for r in known]
    truth = pairs(truth_ids)
    pred = pairs(adjacency_groups(known, num_gap, day_gap, use_dp=False))
    hit = len(pred & truth)
    return {"known_projects": len(set(truth_ids)),
            "precision": round(hit / len(pred), 3) if pred else 1.0,
            "recall": round(hit / len(truth), 3) if truth else 1.0}


def grouping_probe() -> int:
    where = f"issuedate >= date'{IN_FORCE}' AND ({MULTIPLEX_FILTER})"
    url = EXPORT + "?" + urllib.parse.urlencode({
        "where": where, "select": "address,projectdescription,issuedate"})
    rows = json.loads(fetch(url).decode("utf-8"))

    known = [r for r in rows if DP_RE.search(r.get("projectdescription") or "")]
    truth_ids = [DP_RE.search(r["projectdescription"]).group(0) for r in known]
    truth = pairs(truth_ids)
    print(f"{len(rows)} permits. Scoring the address rule against {len(known)} permits "
          f"whose project is known from their DP number ({len(set(truth_ids))} projects).\n")
    print("  civic gap  days    projects found   precision  recall    all-650 estimate")
    print("             apart   (truth {:>3})".format(len(set(truth_ids))))

    for num_gap in (2, 4, 8, 12):
        for day_gap in (30, 120, 365):
            guess = adjacency_groups(known, num_gap, day_gap, use_dp=False)
            pred = pairs(guess)
            hit = len(pred & truth)
            prec = hit / len(pred) if pred else 1.0
            rec = hit / len(truth) if truth else 1.0
            total = len(set(adjacency_groups(rows, num_gap, day_gap, use_dp=True)))
            print(f"  {num_gap:>6}    {day_gap:>4}    {len(set(guess)):>8}        "
                  f"{prec:6.0%}    {rec:6.0%}       {total:>5}")

    print("\nPrecision: of the pairs the rule joins, how many really are one project.")
    print("Recall: of the real one-project pairs, how many the rule finds.")
    print("Pick the row where both are high; its last column is the project count.")
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
#   City of Vancouver news  the best source in principle. Its listing allows
#                           crawling but returns 403 to this script. Getting
#                           past that means disguising the script as a web
#                           browser, which is evading a site's bot blocking,
#                           so it is not done. Re-add only if the City
#                           publishes a feed.
#   Google News search RSS  robots.txt disallows automated fetching
#   Business in Vancouver   /rss refused the request outright
#   CBC British Columbia    the old feed URL refused the request
#   Vancouver Is Awesome    refused the request
#   CityNews Vancouver      blocked

NEWS_SOURCES = [
    # The Tyee tags every story with subject keywords (dc:subject), which are
    # read alongside the headline. A story tagged "Vancouver condo market" is
    # caught by the place check even when its headline never says Vancouver.
    {"name": "The Tyee", "kind": "rss",
     "url": "https://thetyee.ca/rss2.xml", "need_place": True},
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
    # The BC Government feed opens with a byte-order mark. ElementTree accepts
    # it; an earlier version of this comment claimed otherwise and stripped it
    # for nothing. test_trackers.py keeps a BOM-prefixed feed in the tests.
    root = ET.fromstring(raw)
    out = []
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] not in ("item", "entry"):
            continue
        t = first_child(el, "title")
        l = first_child(el, "link")
        d = first_child(el, "pubDate", "published", "updated")
        s = first_child(el, "description", "summary")
        # Subject and category tags. The Tyee's are precise ("BC Bill 44",
        # "Vancouver condo market"); BC Government's are just the ministry.
        tags = " ".join((c.text or "") for c in el
                        if c.tag.rsplit("}", 1)[-1] in ("subject", "category"))
        link = ""
        if l is not None:
            link = (l.text or l.get("href") or "").strip()
        if not link:
            continue
        out.append({
            "title": clean(t.text if t is not None else ""),
            "url": link,
            "date": iso_date(d.text if d is not None else None),
            "_desc": clean((s.text if s is not None else "") + " " + tags),  # matching only
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


def collect_news(previous: list[dict], seeded: set[str]) -> tuple[list[dict], list[str]]:
    """Merge this week's matches into everything matched before.

    Dates. RSS items carry their own. The City listing does not, so a City
    headline is dated the week it first appears here, which is accurate to
    within the week for anything new. The exception is the very first run,
    which picks up the City's whole back catalogue at once: stamping a 2023
    announcement with today's date would be a lie, so those are stored
    undated and shown without a date, at the bottom.

    "First run" is per source, tracked in `seeded`. It used to be per file,
    which broke the first time a source failed on the first run: the file
    then existed, so when that source came back its whole back catalogue
    would have been stamped with the day it recovered. Only undated sources
    are affected, and all the current ones carry dates, but the next one
    added might not.
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
            date = i["date"] or (None if src["name"] not in seeded else today)
            kept[i["url"]] = {"title": i["title"], "url": i["url"],
                              "outlet": src["name"], "date": date}
            new += 1
        seeded.add(src["name"])
        report.append(f"{src['name']:18s} {len(items):4d} items  {len(hits):3d} match  {new:3d} new")

    news = sorted(kept.values(), key=lambda n: n.get("date") or "0000", reverse=True)
    return news[:NEWS_KEEP], report


def news_only() -> int:
    """Check every source and show what matched, without writing anything."""
    print("Checking news sources (nothing is written)...\n")
    news, report = collect_news([], seeded=set())
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
    ap.add_argument("--grouping", action="store_true",
                    help="score the address-adjacency rule against known DP projects")
    ap.add_argument("--projects", action="store_true",
                    help="count distinct multiplex projects, not building permits")
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

    if args.projects:
        return projects_probe()

    if args.grouping:
        return grouping_probe()

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
        seeded = set(previous.get("news_seeded") or [])
        news, report = collect_news(previous.get("news") or [], seeded)
        data["news_seeded"] = sorted(seeded)
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
    # newline="\n": Windows would otherwise write CRLF, Git would warn on every
    # commit, and a local run and the weekly Linux run would differ by bytes.
    DATA_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    lf = data["last_full_year"]
    print(f"\nWrote {DATA_FILE.relative_to(ROOT)}: {data['projects_since_in_force']} projects "
          f"from {data['total_since_in_force']} permits since R1-1; {lf['projects']} projects "
          f"in {lf['year']} against the City's {CITY_EXPECTATION_PER_YEAR}; "
          f"{len(data['news'])} headlines.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
