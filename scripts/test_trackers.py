"""Offline tests for the weekly scripts. No network, runs in about a second.

    python scripts/test_trackers.py

The weekly GitHub Action runs this before it fetches anything, so a change
that breaks a filter, a guard or the project grouping fails the job instead
of quietly publishing a wrong number.

Almost every test here is a mistake that actually happened, or nearly did,
while these scripts were being built in October and November 2026. The
comment on each says which. If one fails, read that comment before "fixing"
the test.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tm = load("track_multiplex")
tr = load("track_research")


def permit(addr, date, dp=None, text="To construct a Multiple Dwelling Multiplex"):
    return {"address": addr, "issuedate": date,
            "projectdescription": (f"Building Permit for {dp} " if dp else "") + text}


# ---------------------------------------------------------------- the filter

class Filter(unittest.TestCase):
    def test_filter_is_the_description_search(self):
        # The category filter (specificusecategory LIKE 'Multiple Dwelling')
        # counted 78-157 permits a year BEFORE R1-1 existed, because Vancouver
        # calls apartment blocks Multiple Dwellings too. Only the description
        # filter read zero in every pre-policy year.
        self.assertIn('search(projectdescription, "multiplex")', tm.MULTIPLEX_FILTER)
        self.assertIn("typeofwork = 'New Building'", tm.MULTIPLEX_FILTER)
        self.assertNotIn("specificusecategory", tm.MULTIPLEX_FILTER)

    def test_grouping_rule_is_the_scored_one(self):
        # Chosen by --grouping: gap 4 / 120 days gave 100% precision, 88% recall.
        self.assertEqual((tm.PROJECT_NUM_GAP, tm.PROJECT_DAY_GAP), (4, 120))


# ---------------------------------------------------------------- projects

class Grouping(unittest.TestCase):
    def ids(self, rows, use_dp=False):
        return tm.adjacency_groups(rows, tm.PROJECT_NUM_GAP, tm.PROJECT_DAY_GAP, use_dp=use_dp)

    def test_one_project_four_buildings_four_addresses(self):
        # DP-2024-00034: one multiplex, four permits at 5963-5969 Granville.
        # Address counting saw four projects; this is the case that proved it.
        rows = [permit(f"{n} GRANVILLE STREET, Vancouver", "2025-02-10") for n in (5963, 5965, 5967, 5969)]
        self.assertEqual(len(set(self.ids(rows))), 1)

    def test_further_along_the_same_street_stays_separate(self):
        rows = [permit("5963 GRANVILLE STREET, Vancouver", "2025-02-10"),
                permit("6100 GRANVILLE STREET, Vancouver", "2025-02-10")]
        self.assertEqual(len(set(self.ids(rows))), 2)

    def test_neighbours_years_apart_stay_separate(self):
        rows = [permit("3301 E 22ND AVENUE, Vancouver", "2025-06-01"),
                permit("3303 E 22ND AVENUE, Vancouver", "2027-06-01")]
        self.assertEqual(len(set(self.ids(rows))), 2)

    def test_postcode_and_letter_suffix_do_not_split_a_street(self):
        # DP-2024-00272's two permits differ only in a missing postcode.
        rows = [permit("1573 W 49TH AVENUE, Vancouver, BC", "2025-05-02"),
                permit("1575 W 49TH AVENUE, Vancouver, BC V6M 2R6", "2025-05-02"),
                permit("1577A W 49TH AVENUE, Vancouver", "2025-05-03")]
        self.assertEqual(len(set(self.ids(rows))), 1)

    def test_dp_number_joins_permits_with_no_address(self):
        # DP-2024-00552: front and rear permits, both with a blank address.
        rows = [permit(None, "2025-04-09", "DP-2024-00552", "2 storey 1-unit REAR building"),
                permit(None, "2025-04-09", "DP-2024-00552", "3 storey 2-unit FRONT building")]
        self.assertEqual(len(set(self.ids(rows, use_dp=True))), 1)
        self.assertEqual(len(set(self.ids(rows, use_dp=False))), 2)

    def test_score_rule_against_known_dp_projects(self):
        rows = [permit("2284 E BROADWAY, Vancouver", "2025-03-01", "DP-2024-00603"),
                permit("2286 E BROADWAY, Vancouver", "2025-03-20", "DP-2024-00603"),
                permit("900 C STREET, Vancouver", "2025-06-01", "DP-2024-00999")]
        s = tm.score_rule(rows, 4, 120)
        self.assertEqual(s["known_projects"], 2)
        self.assertEqual((s["precision"], s["recall"]), (1.0, 1.0))


class Build(unittest.TestCase):
    """build() end to end, with the City's API replaced by fixtures."""

    def setUp(self):
        now = datetime.now(timezone.utc).year
        self.full = str(now - 1)
        y0 = str(now - 2)
        rows = [permit(f"{n} GRANVILLE STREET, Vancouver", f"{y0}-08-10", "DP-2024-00034") for n in (5963, 5965, 5967, 5969)]
        rows += [permit("100 MAIN STREET, Vancouver", f"{y0}-09-01")]
        rows += [permit("2284 E BROADWAY, Vancouver", f"{self.full}-01-10", "DP-2024-00603"),
                 permit("2286 E BROADWAY, Vancouver", f"{self.full}-03-01", "DP-2024-00603")]
        rows += [permit(f"{a}, Vancouver", f"{self.full}-06-01") for a in ("10 A STREET", "500 B STREET", "900 C STREET")]
        self.rows = rows
        self._fetch, self._tally = tm.fetch, tm.tally
        tm.fetch = lambda url: json.dumps(rows).encode()
        months = {}
        for r in rows:
            months[r["issuedate"][:7]] = months.get(r["issuedate"][:7], 0) + 1
        years = {}
        for r in rows:
            years[r["issuedate"][:4]] = years.get(r["issuedate"][:4], 0) + 1
        tm.tally = lambda where, field: {"issueyear": years, "yearmonth": months}.get(field, {"Kerrisdale": 1})

        import builtins
        self._print = builtins.print
        builtins.print = lambda *a, **k: None       # build() narrates; tests don't need it

    def tearDown(self):
        import builtins
        builtins.print = self._print
        tm.fetch, tm.tally = self._fetch, self._tally

    def test_counts_projects_not_permits(self):
        d = tm.build()
        self.assertEqual(d["total_since_in_force"], 10)
        self.assertEqual(d["projects_since_in_force"], 6)

    def test_city_comparison_uses_the_last_full_year(self):
        # Averaging from October 2023 includes eight months before the first
        # permit was issued; the comparison is a complete calendar year.
        d = tm.build()
        self.assertEqual(d["last_full_year"], {"year": self.full, "projects": 4})

    def test_pre_policy_years_are_present_and_zero(self):
        # group_by returns no row for a zero, so the permit years went missing
        # once. Both series must carry all five control years.
        d = tm.build()
        permits = {y["year"]: y["permits"] for y in d["years"]}
        projects = {y["year"]: y["projects"] for y in d["project_years"]}
        for y in ("2019", "2020", "2021", "2022", "2023"):
            with self.subTest(year=y):
                self.assertEqual(permits.get(y), 0)
                self.assertEqual(projects.get(y), 0)

    def test_running_total_never_falls(self):
        totals = [y["running_total"] for y in tm.build()["project_years"]]
        self.assertEqual(totals, sorted(totals))


# ---------------------------------------------------------------- units

class Units(unittest.TestCase):
    def test_reads_unit_counts_and_ignores_storeys_and_parking(self):
        cases = [
            ('To construct a Multiple Dwelling "Multiplex" with a total of 6 dwelling units', 6),
            ("To construct a two-storey Multiple Dwelling containing four (4) strata units", 4),
            ("New 3 storey multiplex with 5 units and 2 parking spaces", 5),
            ("To construct a sixplex with secured rental", 6),
            ("To construct a 3-storey building with 8 secured rental units", 8),
            ("Building Permit for BP-2024-02264", None),
            ("To construct a 2 storey one-family dwelling with 1 secondary suite", None),
            ("Multiplex with 12 parking stalls", None),
        ]
        for text, want in cases:
            with self.subTest(text=text):
                self.assertEqual(tm.extract_units(text), want)


# ---------------------------------------------------------------- news

TYEE = '''<?xml version="1.0" encoding="utf-8"?><rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>
<item><title><![CDATA[Two Years of Small Buildings]]></title><link>https://thetyee.ca/x/</link>
<description><![CDATA[What changed on the east side.]]></description><pubDate>Fri, 13 Nov 2026 08:00:00 +0000</pubDate>
<dc:subject><![CDATA[ multiplex housing ]]></dc:subject><dc:subject><![CDATA[ City of Vancouver ]]></dc:subject></item>
<item><title><![CDATA[Doerkson Invited Young People to Stay]]></title><link>https://thetyee.ca/y/</link>
<description><![CDATA[Keep what works.]]></description><pubDate>Wed, 11 Nov 2026 08:40:00 +0000</pubDate>
<dc:subject><![CDATA[ BC Bill 44 ]]></dc:subject></item>
</channel></rss>'''.encode()


class News(unittest.TestCase):
    def test_matcher(self):
        cases = [("Vancouver multiplex permits hit record", True),
                 ("Burnaby approves fourplexes on every lot", False),   # topic, not Vancouver
                 ("R1-1 zoning: two years on", True),                    # R1-1 needs no place
                 ("Vancouver's new IMAX multiplex", False),             # a cinema
                 ("Vancouver housing starts fall", False)]              # place, no topic
        for title, want in cases:
            with self.subTest(title=title):
                self.assertEqual(tm.matches({"title": title, "_desc": ""}, True), want)

    def test_subject_tags_count_towards_a_match(self):
        items = tm.parse_rss(TYEE)
        self.assertEqual([tm.matches(i, True) for i in items], [True, False])

    def test_byte_order_mark_is_tolerated(self):
        # The BC Government feed starts with a byte-order mark. ElementTree
        # copes; this keeps it that way if the parser is ever swapped.
        raw = ("﻿" + '<?xml version="1.0" encoding="utf-8"?><rss><channel><item>'
               '<title>T</title><link>https://x/</link><pubDate>Tue, 10 Nov 2026 14:00:00 -0700</pubDate>'
               '</item></channel></rss>').encode("utf-8")
        self.assertEqual(tm.parse_rss(raw)[0]["date"], "2026-11-10")

    def test_first_child_survives_childless_elements(self):
        # An element with no children is falsy, so `find(a) or find(b)` skips
        # a perfectly good <title>. first_child must not fall for that.
        import xml.etree.ElementTree as ET
        el = ET.fromstring("<item><title>Kept</title><link>u</link></item>")
        self.assertEqual(tm.first_child(el, "title").text, "Kept")

    def test_only_metadata_is_stored(self):
        # Article text belongs to its publisher.
        self._run({"T": TYEE}, sources=[{"name": "T", "kind": "rss", "url": "T", "need_place": True}])
        for n in self.news:
            self.assertEqual(set(n), {"title", "url", "outlet", "date"})

    def test_a_failing_source_seeds_nothing(self):
        # The first-ever run had the City's listing return 403. Under the old
        # per-file seeding, its back catalogue would have been stamped with
        # the date it recovered.
        listing = b'<a href="/news-calendar/a.aspx">Vancouver speeds up multiplex permits to expedite missing middle housing</a>'
        src = [{"name": "S", "kind": "html", "url": "S", "link_contains": "/news-calendar/", "need_place": False}]
        seeded = set()
        self._run({"S": urllib.error.URLError("403")}, sources=src, seeded=seeded)
        self.assertEqual(seeded, set())
        self._run({"S": listing}, sources=src, seeded=seeded)
        self.assertIsNone(self.news[0]["date"])        # back catalogue: undated
        self.assertEqual(seeded, {"S"})                 # and now it counts as seeded
        newer = listing + b'<a href="/news-calendar/b.aspx">City reports multiplex uptake two years in</a>'
        self.news, _ = self._collect({"S": newer}, src, seeded, previous=self.news)
        fresh = [n for n in self.news if n["url"].endswith("/b.aspx")][0]
        self.assertEqual(fresh["date"], datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    def _run(self, feeds, sources, seeded=None):
        self.news, self.report = self._collect(feeds, sources, seeded if seeded is not None else set())

    def _collect(self, feeds, sources, seeded, previous=()):
        saved = (tm.fetch, tm.NEWS_SOURCES)

        def fake(url):
            v = feeds[url]
            if isinstance(v, Exception):
                raise v
            return v
        tm.fetch, tm.NEWS_SOURCES = fake, sources
        try:
            return tm.collect_news(list(previous), seeded)
        finally:
            tm.fetch, tm.NEWS_SOURCES = saved


# ---------------------------------------------------------------- research

def work(title, oa, stype, authors=("A B",)):
    return {"title": title, "publication_date": "2026-11-01", "doi": "https://doi.org/x",
            "authorships": [{"author": {"display_name": a}} for a in authors],
            "primary_location": {"is_oa": oa, "landing_page_url": "https://doi.org/x",
                                 "source": {"type": stype, "display_name": "Urban Studies"}}}


class Research(unittest.TestCase):
    def test_refuses_a_silently_dropped_filter(self):
        # A malformed OpenAlex query returns the whole index, not an error.
        # On 15 November 2026 that was 328 million works, newest first:
        # veterinary case reports dated 2050.
        with self.assertRaises(RuntimeError):
            tr.build({"meta": {"count": 328064067}, "results": [work("A cat", True, "journal")]})

    def test_refuses_a_response_with_no_count(self):
        with self.assertRaises(RuntimeError):
            tr.build({"meta": {}, "results": []})

    def test_keeps_only_free_peer_reviewed_journal_articles(self):
        kept = tr.build({"meta": {"count": 65}, "results": [
            work("Journal and free", True, "journal"),
            work("Preprint server", True, "repository"),
            work("Journal but paywalled", False, "journal")]})
        self.assertEqual([p["title"] for p in kept], ["Journal and free"])

    def test_stores_no_abstract(self):
        kept = tr.build({"meta": {"count": 1}, "results": [work("T", True, "journal")]})
        self.assertEqual(set(kept[0]), {"title", "authors", "journal", "date", "url"})

    def test_author_formatting(self):
        self.assertEqual(tr.authors(work("", True, "journal", ("Ka Shing Cheung",))), "Cheung")
        self.assertEqual(tr.authors(work("", True, "journal", ("Ryan Greenaway-McGrevy", "Peter Phillips"))),
                         "Greenaway-McGrevy and Phillips")
        self.assertEqual(tr.authors(work("", True, "journal", ("A Cheung", "B Monkkonen", "C Yiu"))), "Cheung et al.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
