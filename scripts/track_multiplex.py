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
import json
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
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
MULTIPLEX_FILTER = None   # e.g. "propertyuse LIKE 'Multiple Dwelling'"
# ---------------------------------------------------------------------------

TIMEOUT = 45


def api(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "brandonfleming.ca tracker"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


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
            for row in rows[:40]:
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


# ----------------------------------------------------------------- collection

def fetch_all(where: str) -> list[dict]:
    """Page through every matching record. Opendatasoft caps limit at 100."""
    out, offset = [], 0
    while True:
        page = api({
            "where": where,
            "limit": 100,
            "offset": offset,
            "order_by": "issuedate",
        })
        rows = page.get("results") or []
        out.extend(rows)
        if len(rows) < 100:
            return out
        offset += 100
        if offset > 20000:        # a stop, so a bad filter cannot run forever
            print("  ! stopped at 20,000 records. The filter is probably too broad.")
            return out


def build() -> dict:
    where = f"issuedate >= date'{IN_FORCE}' AND ({MULTIPLEX_FILTER})"
    print(f"  where: {where}")
    rows = fetch_all(where)
    print(f"  {len(rows)} permits")

    by_month: Counter = Counter()
    for r in rows:
        issued = str(r.get("issuedate") or "")[:7]
        if issued:
            by_month[issued] += 1

    months = sorted(by_month)
    first = datetime.strptime(IN_FORCE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    years = (datetime.now(timezone.utc) - first).days / 365.25

    return {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "City of Vancouver open data, issued building permits",
        "source_url": "https://opendata.vancouver.ca/explore/dataset/issued-building-permits/",
        "in_force": IN_FORCE,
        "filter": MULTIPLEX_FILTER,
        "total": len(rows),
        "per_year": round(len(rows) / years, 1) if years > 0 else None,
        "city_expectation_per_year": CITY_EXPECTATION_PER_YEAR,
        "months": [{"month": m, "permits": by_month[m]} for m in months],
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--facets", action="store_true",
                    help="print the distinct field values, to work out the filter")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the result instead of writing data/multiplex.json")
    args = ap.parse_args(argv)

    if args.facets:
        return facets()

    if not MULTIPLEX_FILTER:
        print("MULTIPLEX_FILTER is not set yet, so there is nothing to count.\n"
              "Run `python scripts/track_multiplex.py --facets` first and send me\n"
              "the output. Writing a guessed filter would produce a number on a\n"
              "public page that nobody could check.")
        return 2

    print("Counting Vancouver multiplex permits...")
    try:
        data = build()
    except Exception as e:
        print(f"Failed: {e}")
        return 1

    if args.dry_run:
        print(json.dumps(data, indent=2)[:2000])
        return 0

    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {DATA_FILE.relative_to(ROOT)}: {data['total']} permits, "
          f"about {data['per_year']} a year against the City's {CITY_EXPECTATION_PER_YEAR}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
