# Bill 44 tracker — work handoff

Everything a fresh session needs to take over the tracker. Written August 2026.
The rest of `brandonfleming.ca` is finished and live; this is the one unfinished
system in it.

Read `HANDOFF.md` first for the site as a whole. This document covers only the
tracker, and assumes you have the repo checked out.

---

## What it is

Bill 44 requires BC municipalities to permit small-scale multi-unit housing
(SSMUH) on most single-family lots. Implementation is happening one council
agenda at a time across Metro Vancouver, and almost none of it is reported.

The tracker is a running record of that. A script surfaces **candidates** from
municipal agendas and regional news; Brandon reads each one and writes a
**note**; only annotated entries are published.

**The note is the product.** The automation only finds things to read. A page of
unreviewed headlines is a feed, and a feed on a portfolio site reads as a robot
nobody is watching. This distinction drives the whole design and you should not
erode it for convenience.

Brandon is a Master of Urban Studies student applying for municipal planning
co-ops. The audience for this page is Registered Professional Planners. It is
better for the tracker to have six sharp entries than sixty limp ones.

---

## Hard rules

These are not preferences.

1. **Never write a `note`.** Not a draft in the file, not a placeholder, not a
   "suggested" note committed for later editing. Notes are Brandon's, in his
   voice, and a note in the file is indistinguishable from a published one —
   the templates publish on `note != ""`. Propose text in chat; never in the repo.
2. **Never store article body text.** Only headline, URL, and date. Storing
   article text is someone else's copyright. `from_rss` and `from_html` both
   already respect this; keep it that way if you rewrite them.
3. **No secrets in the repo.** Bot tokens and chat IDs go in GitHub Actions
   secrets. If you touch the workflow, reference them as `${{ secrets.NAME }}`.
4. **Don't flip `showTracker` until the page has real annotated entries.** An
   empty tracker in the nav is worse than no tracker.

---

## Current state, precisely

| Thing | State |
|---|---|
| `data/tracker.json` | 26 candidates, all with an empty `note` |
| Sources configured | 6: four news/provincial RSS, two Surrey report listings |
| Municipal sources | Surrey corporate reports and planning reports, both working |
| Documents evaluated | 100, cached in `scripts/tracker_cache.json` |
| `showTracker` in `hugo.toml` | `false` — not in the nav |
| GitHub Action | Scheduled weekly, has not yet run on its own |
| Rail on home page | Renders nothing (correctly) when no annotated entries |
| `/tracker/` page | Renders "No reviewed entries yet." until a note exists |

The pipeline works. Top candidates are R149 on inclusionary housing in
transit-oriented areas (98 hits), R162 on the SSMUH review framework (86), and
the Old Yale Road houseplex planning report (44).

**What is left is Brandon's, not yours: the notes.** Nothing publishes without
them. After that, Telegram delivery and `showTracker = true`.

Two findings worth not rediscovering. Council report titles are just application
numbers, so keyword matching runs against the linked PDF text, which is why
`pypdf` is a hard dependency. And Surrey's own word for a small-scale multi-unit
building is **houseplex**, which no journalist ever writes.

---

## File map

```
scripts/track_bill44.py            the collector
scripts/requirements.txt           requests, PyYAML (plus the plate's deps)
scripts/tracker_sources.yaml       keywords + source list  <- most of your work
data/tracker.json                  the store; notes written by hand
layouts/partials/tracker-rail.html home page rail, top 4 annotated entries
layouts/tracker/list.html          the /tracker/ page
content/tracker/_index.md          intro copy for that page
.github/workflows/track-bill44.yml weekly run, commits back
hugo.toml                          showTracker flag (line ~38)
```

### Entry schema

Every entry in `data/tracker.json` is:

```json
{
  "id": "sha1 of the url, first 12 chars",
  "title": "headline or link text, as published",
  "url": "https://…",
  "date": "YYYY-MM-DD",
  "source": "name from scripts/tracker_sources.yaml",
  "jurisdiction": "Surrey",
  "type": "council | news | provincial",
  "note": ""
}
```

`id` is derived from the URL, so re-running never duplicates an item, and a
merge preserves every note already written. `updated` at the top of the file is
set on every run regardless of whether anything was found.

### How to run

```powershell
pip install -r scripts\requirements.txt
python scripts\track_bill44.py --dry-run   # show what would be added, write nothing
python scripts\track_bill44.py             # poll and merge into tracker.json
python scripts\track_bill44.py --review    # list entries still awaiting a note
```

`--dry-run` is your main tool. Use it constantly while tuning sources; it makes
no changes.

---

## Task 1 — municipal agenda sources

This is the reason the tracker is worth building. Nobody else aggregates
Metro Vancouver council agendas by topic.

### The municipalities

Metro Vancouver has 21 member municipalities, plus Electoral Area A and
Tsawwassen First Nation:

> Anmore · Belcarra · Bowen Island · Burnaby · Coquitlam · Delta · Langley City ·
> Langley Township · Lions Bay · Maple Ridge · New Westminster ·
> North Vancouver City · North Vancouver District · Pitt Meadows ·
> Port Coquitlam · Port Moody · Richmond · Surrey · Vancouver · West Vancouver ·
> White Rock

**Verify this before doing the work:** SSMUH obligations under Bill 44 are
understood to apply to municipalities above a population threshold (commonly
cited as 5,000), which would exempt Anmore, Belcarra, Lions Bay and possibly
Bowen Island. Confirm against the current legislation and the Province's SSMUH
policy manual rather than taking this paragraph's word for it. If it holds, the
work drops from 21 municipalities to about 17, and you should say so in the
source file's comments so nobody re-adds them.

Sensible order to work in, by relevance to Brandon's thesis and by size:
**Surrey first** (his case study), then New Westminster, Burnaby, Vancouver,
Richmond, Coquitlam, Delta, Langley Township, North Vancouver District.

### What to produce

Entries in `scripts/tracker_sources.yaml`:

```yaml
  - name: "City of Surrey — Council Agendas"
    jurisdiction: "Surrey"
    type: "council"
    mode: "html"
    url: "https://…"
    link_contains: "agenda"
```

Two such blocks already exist, commented out, at the bottom of that file. Their
URLs are unverified guesses from a previous session — check them, don't trust
them.

### The obstacle

`mode: "html"` scrapes anchor tags with a regex. Most municipalities do not
serve their agendas that way. In this region you will mostly meet:

- **Escribe** (`pub-<city>.escribemeetings.com`) — very common in BC.
- **CivicWeb** (`<city>.civicweb.net`) — also common.
- **Legistar / Granicus**, and a few bespoke pages.

Several render the meeting list with JavaScript, which the current scraper
cannot see at all, and some put the agenda topics inside a PDF rather than in
the link text — which means a link-text keyword match will never fire even
though the agenda is full of SSMUH items.

**Check whether these platforms expose a feed or a JSON endpoint before writing
any scraping.** Escribe and CivicWeb both have machine-readable surfaces in some
deployments. One working endpoint is worth more than ten fragile scrapers, and
`mode: "rss"` already handles feeds with no new code.

---

## Task 2 — make collection robust

Current state of the two collectors:

- `from_rss` — a regex over `<item>`/`<entry>`. Fine. Handles RSS and Atom,
  avoids a feedparser dependency. Leave it unless it actually breaks.
- `from_html` — a regex over `<a href…>`. Cannot execute JavaScript, cannot read
  PDFs, and has no notion of a meeting date (it stamps everything with today).

Things worth doing, roughly in value order:

1. **Give HTML sources a real date.** Every scraped item currently gets today's
   date, so `/tracker/` would sort council items wrongly against news. Parse the
   date out of the link text or a sibling element where possible.
2. **Handle agenda PDFs.** If a council link points at a PDF, the keywords need
   to be tested against the document text, not the link text. Note rule 2: you
   may read a PDF to decide whether it matches, but only headline, URL and date
   go in the store.
3. **Add a per-source `mode`** for whichever platform API you find, rather than
   bolting more special cases onto `from_html`.
4. **Fail loudly per source, not silently.** `fetch()` prints and returns `None`;
   a source that has been broken for a month currently looks identical to a
   source with no news. Consider recording a per-source last-success date.

`fetch()` already retries once on timeout or connection error, with a doubled
timeout, and deliberately does not retry a 404 — a 404 means the feed moved and
only a human editing the YAML will fix it. Keep that distinction.

---

## Task 3 — keyword tuning

Current list (12): `bill 44`, `ssmuh`, `small-scale multi-unit`, `small scale
multi unit`, `small-scale multi unit`, `housing statutes amendment`, `upzoning`,
`upzone`, `multiplex`, `fourplex`, `sixplex`, `transit-oriented area`.

Matching is a plain case-insensitive substring test against the title only.

The problem is that these are the words *journalists* use. A council agenda item
is more likely to read "Zoning Amendment Bylaw No. 20456" or "Official Community
Plan Amendment — Residential Infill". Keywords that work for news will not fire
on agendas, and vice versa.

Worth considering: per-source keyword lists, or a broader agenda-side list
accepting more false positives, since Brandon is reviewing everything by hand
anyway. **Over-matching is much cheaper than under-matching here** — an entry he
discards costs him ten seconds; an entry he never sees is invisible.

Test with `--dry-run` against real feeds before committing a list.

---

## Task 4 — Telegram delivery

Brandon wants pending candidates pushed to him so he can review on his phone and
write notes, rather than remembering to open `tracker.json`. He already runs
bots through **OpenClaw**, which has a Telegram channel
([docs](https://docs.openclaw.ai/channels/telegram)).

Ask him which of these he wants before building either:

**Option A — the Action posts to Telegram directly.** After the poll step, a
short step calls the Telegram Bot API with the pending list. No dependency on
OpenClaw being up. Roughly ten lines. Needs two repo secrets,
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, set under the repo's
Settings → Secrets and variables → Actions.

**Option B — route through his existing OpenClaw gateway.** Reuses the setup he
already has, and gives him a bot he can converse with rather than a one-way
notification. More moving parts, and the tracker then depends on that gateway
running.

Either way the message should contain, per pending entry: date, jurisdiction,
title, URL. That is enough to decide whether an item is worth a note. Keep it
under Telegram's 4096-character limit — chunk if the list is long, and lead with
a count.

`python scripts/track_bill44.py --review` already prints exactly this list and
is the natural thing to shell out to or reimplement.

**Do not** build a path that lets a note be written from Telegram back into the
repo without Brandon editing the file. See rule 1.

---

## Task 5 — switch it on

Only after the above produce real, annotated entries.

1. `python scripts\track_bill44.py` for real, so `data/tracker.json` has content.
2. Brandon writes notes on the entries worth keeping; deletes the rest.
3. `hugo server` — check `/tracker/` renders the entries, and check the rail
   appears beside the hero on a window wider than 1100px. The rail shows the
   4 most recent annotated entries; it is hidden below 1100px by design.
4. Set `showTracker = true` in `hugo.toml` to put it in the nav.
5. Commit and push. Cloudflare rebuilds in a minute or two.
6. Trigger the Action manually from the repo's **Actions** tab
   (`workflow_dispatch` is enabled) and confirm it commits cleanly and that the
   push from the Action doesn't fail on permissions.

The Action runs Mondays at 14:00 UTC. Its commit will trigger a Cloudflare
rebuild, so anything it adds goes live — which is exactly why unreviewed entries
must never render.

---

## Gotchas

- **`hugo server` is the source of truth.** `_preview/build.py` re-implements the
  templates and drifts. A caption bug survived from the first commit because it
  was only ever checked in `_preview/`. Do not verify anything there.
- **TOML front matter:** a `[table]` header captures every bare key below it.
  Keep bare keys above tables. This has bitten this repo before.
- **The Action pushes to `main`.** If Brandon has local commits when it fires,
  his next push is rejected; `git pull --rebase` then push. Warn him if you
  change the schedule to something more frequent.
- **`HUGO_VERSION` is `0.147.7`** in Cloudflare Pages. Match it locally.
- **Python on Brandon's machine is 3.14**, installed per-user; its Scripts
  directory is not on PATH. `pip install` warns about this and it's harmless.
- Brandon works in **PowerShell on Windows 11**, does not consider himself a
  programmer, and is strong at GIS. Give him commands he can paste, and explain
  what a change does rather than only that it works.

---

## Definition of done

- Agenda sources for the Metro Vancouver municipalities that Bill 44 actually
  binds, each verified to return matches with `--dry-run`.
- A collector that survives a JavaScript-rendered meeting portal, or a
  documented decision not to support one and why.
- Pending candidates arriving on Brandon's phone weekly.
- `/tracker/` showing entries he wrote the notes for, `showTracker = true`, and
  the Action having committed at least once on its own.
