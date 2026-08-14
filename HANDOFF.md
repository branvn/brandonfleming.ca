# Handoff

Everything a new session needs to pick this up. Written August 2026.

---

## What this is

`brandonfleming.ca` — a personal site for **Brandon Fleming**, a Master of Urban
Studies student at SFU doing an Advanced Certificate in GIS at BCIT. He's
applying for graduate co-op terms in municipal planning in Metro Vancouver.
The site's job is to get him interviews at planning departments.

Domain registered at **Porkbun**, to be hosted on **Cloudflare Pages**, built
with **Hugo**. Nothing is deployed yet — the repo has never been pushed.

He works on **Windows 11** in PowerShell. He does not consider himself a
programmer; he built the first version with an LLM. He *is* strong at GIS
(ArcGIS Pro, ArcMap, FME) and is handling all GIS work himself from here.

---

## State: what's done

**Live at https://brandonfleming.ca**, built by Cloudflare Pages from
`github.com/branvn/brandonfleming.ca` on push to `main`.

- **Home** — hero, four work cards, Bill 44 tracker rail (hidden below 1100px)
- **Work** — 4 project pages, all written
- **Photography** — Film (13 photos) and Digital (2), all captioned
- **About**, **404**, RSS, sitemap, JSON-LD, Open Graph
- **Bill 44 tracker** — scaffolded, switched off (`showTracker = false`)
- **Email** — `contact@brandonfleming.ca` forwarding confirmed working. Settled.

## State: what's outstanding

1. **`content/work/bill-44-thesis.md` has no "What I'm finding" section.** The
   page runs question, method, why it matters, and is accurate to thesis
   proposal 2.1 — but the preliminary findings are the part a planner actually
   reads, and they are missing. Only Brandon can write them. Do not write them
   for him; he asked explicitly to do it himself, twice. An HTML comment sits in
   the file where the section belongs.

   **He set himself a deadline of 28 August 2026** for getting this up.
3. **Bill 44 tracker is still inert.** `showTracker = false`, `tracker.json`
   empty. The dry run polls four sources cleanly but has matched nothing yet.

---

## Repo layout

```
content/          the words
  _index.md         home; hero lines are in front matter
  about.md
  work/             one .md per project, `weight` orders them
  writing/          empty
  photography/
    film/           11 .jpg + captions in _index.md
    digital/        empty; D750 + 24-85mm
  tracker/          Bill 44 tracker intro
layouts/          hand-written templates, no theme
assets/
  css/main.css      the entire stylesheet, ~700 lines, heavily commented
  js/terrain.js     the ONLY JavaScript on the site
  img/plate.svg     generated contour plate (77 KB gz)
static/
  fonts/            Jost + Michroma (+ unused Basteleur)
  documents/        résumé and two PDFs
data/             tracker.json + tracker_sources.yaml
scripts/
  make_plate.py     the contour plate generator
  track_bill44.py   Bill 44 news/agenda collector
_preview/         gitignored; build.py renders static previews without Hugo
```

`README.md` covers design decisions. `DEPLOY.md` covers shipping.

---

## Design decisions worth not re-litigating

**Palette** is cartographic — deep trench `#051014`, teal, vegetation green,
topographic sand `#dda15e`. All CSS custom properties at the top of `main.css`.

**Type** is Jost\* (Futura revival, variable, 25 KB) for the whole interface,
with Michroma (after Eurostile, 17 KB) on the home hero only. Futura + Eurostile
is the International Style / Expo 86 pairing — that was a deliberate brief from
Brandon after rejecting a medieval-rooted serif as wrong for a planner.
Self-hosted, no Google Fonts request. Michroma sets **1.40× wider** than Jost,
which is why the hero caps at 4rem with −0.005em tracking rather than 6.5rem at
−0.035em. Squared faces fall apart when tightened.

**Long-form pages** put dark text on a paper-coloured panel over the dark shell.
Deliberate: long text on dark is tiring, and photographs need a neutral surround.

**Muted text** is 72% opacity, not 50%. (Correction on the record: the original
50% measured 4.75:1, which *passes* AA — I initially claimed it failed. The
change is still worth it at 8.9:1, but it wasn't a compliance fix.)

**Photography** uses masonry CSS columns, not a square grid — these are 3:2 and
2:3 film frames and square-cropping throws away the composition. Photo surround
is neutral `#0b0b0c` so the teal palette can't tint a B&W print.

**Positioning:** the site says "Urban Studies Graduate Student | GIS & Policy
Analysis", not "Junior Urban Planner". In BC, *planner* carries professional
designation weight (RPP/MCIP via PIBC) and the audience is RPPs. Don't reinstate
it. Similarly there's no "available for freelance" — he's seeking a co-op term,
and the two stories conflict.

---

## The background plate — how it works

`assets/img/plate.svg` is a contour map of the Lower Mainland, inlined by
`layouts/partials/background.html` so it paints on first response.

Structure, which is the entire contract between generator and JS:

```html
<g id="coast">              coastline, lake and river shores
<g class="b" data-e="-2" style="--c:#4fc9a6">    contour band, metres
<g class="b" data-e="33" style="--c:#70cd8f">
```

`assets/js/terrain.js` reads `data-e`, and on pointer move adds `.lit` to every
band at or below a threshold derived from cursor Y. Lit bands take their `--c`
from a hypsometric ramp. Reads as a water line rising across the delta —
substantive for a region whose housing sits on a floodplain.

Cheap by construction: no canvas, no per-frame redraw. A full pointer sweep is
~35 className writes. Disabled under `prefers-reduced-motion` and on coarse
pointers. With JS off it's simply a map.

**Current build:** 72 × 44 km, 1.63 aspect, 1,116 paths, 77 KB gzipped,
17 bands, 92 coast paths. Generates in about four seconds.

### Regenerating

Source layers live in `FINAL_DEM/` on the Desktop — outside the repo, which is
deliberate: they are 14 MB and Git keeps every version of a binary forever.
Despite the folder name **there is no DEM in it**, and none is needed.

```powershell
pip install -r scripts\requirements.txt
python scripts\make_plate.py ^
    --contours FINAL_DEM\Contour25m.shp ^
    --land FINAL_DEM\Boundary.shp ^
    --water FINAL_DEM\Rivers.shp FINAL_DEM\Lakes.shp
```

Frame is the `FRAME` dict at the top of the script, in lon/lat.

### The pipeline is vector-only now

It used to read a DEM and derive the land mask, and optionally the contours,
from it. It no longer does. That removed rasterio, scipy and matplotlib from the
dependency list, cut the runtime from minutes to seconds, and deleted three of
the five traps below outright — they were all artefacts of inferring a coastline
from a raster footprint. An authoritative land polygon is simply better input.

The old traps, kept only so nobody reintroduces the raster path: DEMs merge
rather than replace, and the two old LidarBC exports were 30% and 34% land alone
but 44% together; coast had to be clipped to the *raw* DEM footprint rather than
the eroded one, and getting that wrong silently produced zero coast paths; and
the old land layer was the Metro Vancouver RGS *land-use designations*, which
cover water, so rivers ran through Industrial and General Urban.

### Traps that still apply

1. **A land polygon is part shoreline, part administrative line.** The
   international border, the northern edge of the export, and the regional line
   east of Langley are lines somebody drew. Rendered as coast they read as a
   hard straight rule across the map.

   Length alone will not separate them, because the Fraser is dyked and its
   banks run straight for two to three kilometres. What separates them is that
   every administrative edge here was drawn along a parallel or meridian: the
   ten longest edges all sit within 1.3° of an axis, and nothing real of
   comparable length is within 6°. Hence `--max-edge` **plus** the 3° axis test.
2. **Simplify before you test edge length.** Some of those boundaries arrive
   densified — a straight line carrying a vertex every 50 m — and as raw
   geometry they are indistinguishable from shoreline. Douglas-Peucker collapses
   each run back into the single long edge it actually is. Testing first and
   simplifying second leaves them on the map; this was hit once.
3. **`preserveAspectRatio="slice"`** means the plate fills the viewport and crops.
   Keep the frame aspect near widescreen (~1.6–1.75) or the top and bottom get
   cut on a wide monitor. Widen longitude, not latitude — latitude is what holds
   the North Shore and White Rock. The script warns if you leave 1.5–1.85.
4. **The three source layers are in three different CRSs** — Boundary in UTM 10N,
   contours in geographic CSRS, rivers and lakes in BC Albers. This is normal and
   handled per file. Don't "fix" it by reprojecting them all in ArcGIS first.

Also: raise `--simplify` to shrink the file; past about 3.0 the coastline facets
visibly. Coordinates are emitted as integers — sub-pixel precision is pointless
on a plate scaled to fill a viewport.

### Settled: the contour interval

This was the open question in the previous handoff and it is now closed. The old
export was uniform 35 m, 35 levels, −2 to 1188 m, and badly misallocated: nearly
40% of the land sits under 35 m and got two lines, while under 9% sits above
400 m and got twenty-three. The delta was blank and the North Shore was mush.

Brandon re-exported on the recommended non-uniform list, dense low:

```
10, 20, 35, 55, 80, 110, 150, 200, 260, 330, 410, 500, 600, 720, 850, 1000, 1150
```

| | Old (uniform 35 m) | New (non-uniform) |
|---|---|---|
| Levels below 35 m | 2 | 3 |
| Share of ink below 35 m | 12.7% | 34.6% |
| Share of ink below 80 m | — | 57.0% |
| Total levels | 35 | 17 |

The recommendation also carried **2 m and 5 m**, which are not in this export.
They are the levels that would draw the floor of Richmond and Delta, so if the
plate ever gets revisited that is the first thing to add. A `--levels` flag now
exists to subset a denser export without re-exporting, so the route is: export
uniform 5 m, then select in code.

Colour classification is a **quantile/ink blend, not equal-interval** — equal
interval put orange and red on a few percent of the ink, in a sliver that `slice`
then cropped off screen, so the warm end was effectively invisible. The blend
carried over to the new level list unchanged and needed no retuning.

---

## Bill 44 tracker

`scripts/track_bill44.py` polls RSS feeds and municipal agenda pages listed in
`data/tracker_sources.yaml`, and writes candidates into `data/tracker.json` with
an **empty `note`**. Nothing publishes until Brandon writes that note by hand —
the annotation is the point; an unreviewed feed reads as a robot nobody watches.
Only headline, URL and date are stored, never article text.

`.github/workflows/track-bill44.yml` runs it weekly and commits back. Currently
inert: `data/tracker.json` is empty and `showTracker = false` in `hugo.toml`.

The rail on the home page renders **nothing** when there are no reviewed entries,
so it can never show as an empty box. The entries visible in `_preview/` are
sample data injected by `_preview/build.py` only.

---

## Working notes

- **`hugo server` is the source of truth.** `_preview/build.py` is a stopgap that
  re-implements enough of the templates to review design without Hugo; it drifts.
  It was written because the sandbox couldn't install Hugo (its binaries download
  from GitHub releases, which was blocked).
- **Set `HUGO_VERSION` = `0.147.7`** as a Cloudflare Pages environment variable
  or the build fails with confusing template errors. This is what the live site
  is built with — confirm against `hugo version` locally before changing it, and
  change both together.
- **Check where email forwarding lives** before moving nameservers. If
  `contact@brandonfleming.ca` is forwarded at Porkbun, switching to Cloudflare
  nameservers breaks it — and that address is already on job applications.
- **TOML front matter:** a `[table]` header captures every bare key below it.
  `sources = [...]` placed after `[download]` silently became `download.sources`
  and the template never saw it. Keep bare keys above tables.
- Hugo derives URLs from **filenames**, not titles, unless `slug` is set.
- Brandon pushes back well and is right often. He caught the missing Fraser
  segment and the sliced North Shore before I did. Show him renders rather than
  describing them.

---

## Things I got wrong, so they don't get repeated

- Spent roughly two hours iterating on background data while the thesis summary
  sat unwritten. The background is now good; it was never the priority.
- Claimed 50% muted text failed WCAG AA. It measured 4.75:1 and passed.
- Broke the coastline with a "fix" that made `coast_ok` unreachable, and shipped
  a render before checking it.
- Built a font comparison page with seven near-identical grotesques and called it
  a range. Brandon correctly said they all looked the same.
- Shipped photo captions that never rendered. The template looked up
  `captions[pageName]` instead of `captions[filename]`, so the figcaption and the
  alt text were both silently skipped. It survived from the very first commit
  because `_preview/build.py` re-implements the templates and happened to get it
  right — so the design reviews all showed captions the real site never had.
  Anything verified only in `_preview/` is not verified.
- Told Brandon his broken mobile layout was probably a browser setting. It was a
  grid blowout in the CSS, which he'd already suspected by sending the screenshot
  in the first place. The live HTML looked correct, so I reasoned from the markup
  instead of loading the page at a phone width.
- On the vector rewrite, cut administrative edges on length alone. It removed the
  boundaries and also shredded every dyked riverbank in Richmond and Delta —
  which is to say most of the coastline that matters here. The map looked plainly
  wrong at a glance, which is the only reason it got caught. Render and look;
  the path counts in the console said nothing useful either way.
