# brandonfleming.ca

Personal site — Hugo, hand-written layouts, no theme and no JavaScript.
Deployed on Cloudflare Pages. See [DEPLOY.md](DEPLOY.md) for setup and
publishing.

## Where things live

```
content/          the words — edit these
  _index.md         home page (hero lines are in the front matter)
  about.md
  work/             one .md per project
  writing/          blog posts
  photography/      drop .jpg files straight in here
  tracker/          Bill 44 tracker intro text
layouts/          the HTML templates
assets/
  css/main.css      the entire stylesheet
  js/terrain.js     the only JavaScript on the site
  img/plate.svg     contour plate (generated)
static/           files served as-is (PDFs, images, favicon)
data/             tracker entries and source list
scripts/          plate generator + Bill 44 tracker
```

## Common tasks

**Preview locally** — `hugo server`, then <http://localhost:1313>

**New project page**

```powershell
hugo new work/my-project.md
```

Uses `archetypes/work.md`, which lists every field with a comment. Set
`draft = false` to publish. `weight` controls ordering (lower = higher up).

**New blog post** — `hugo new writing/my-post.md`

**Add photos** — resize the long edge to ~2400px, drop the `.jpg` files into
`content/photography/`, add a `[captions."filename.jpg"]` block in that folder's
`_index.md`. Hugo makes the thumbnails.

> Resize *before* copying them in. Git stores every version of every binary
> forever — a 25 MB original stays in the repo permanently even after deletion.

**Take the site offline** — `underConstruction = true` in `hugo.toml`.

**Show the tracker in the nav** — `showTracker = true` in `hugo.toml`.

## Design notes

The palette is cartographic: deep trench blue, shallow water, vegetation green,
topographic sand. All colours are CSS custom properties at the top of
`assets/css/main.css` — change them there, nowhere else.

The background is a contour plate of the Lower Mainland, built from vector
layers only — there is no DEM in the pipeline. Contours come from a polyline
shapefile generated in ArcGIS Pro (17 levels on a non-uniform interval, 10 m to
1150 m); land area from the Metro Vancouver boundary; hydrography from the
Freshwater Atlas. `scripts/make_plate.py` emits `assets/img/plate.svg`, where
each band is a `<g class="b" data-e="…">` so `assets/js/terrain.js` can light
every band below the pointer's elevation — a water line rising across the delta.

Frame is 72 × 44 km at 1.63 aspect, kept near widescreen on purpose: the SVG
uses `preserveAspectRatio="slice"`, so a squarer plate loses its top and bottom
to the crop.

Three things that are easy to get wrong:

- **The contour interval is non-uniform, and deliberately so.** `10, 20, 35, 55,
  80, 110, 150, 200, 260, 330, 410, 500, 600, 720, 850, 1000, 1150`. Nearly 40%
  of the land here is under 35 m. A uniform interval spends its lines on the
  North Shore and leaves the delta — the actual subject — blank. Lowering a
  uniform interval makes that worse, not better; the fix is to bias the levels.
- **A land polygon is part shoreline and part administrative line.** The
  international border, the northern edge of the export and the regional line
  east of Langley are all just lines somebody drew. Rendered as coast they read
  as a bug. The script drops boundary edges that are both long and axis-aligned,
  which is what separates them from the dyked riverbanks that are also straight.
- **Simplify before testing edge length, not after.** Some administrative edges
  arrive densified — a straight line carrying a vertex every 50 m — and look
  exactly like shoreline until Douglas-Peucker collapses them back.

Home page is ~127 KB gzipped all in (77 KB plate, 25 KB Jost, 17 KB Michroma,
6 KB CSS, 1 KB JS); other pages ~110 KB without Michroma. A full pointer sweep
is 17 DOM writes; there is no per-frame redraw.

Regenerate — the frame is the `FRAME` dict at the top of the script:

```powershell
pip install -r scripts\requirements.txt
python scripts\make_plate.py ^
    --contours FINAL_DEM\Contour25m.shp ^
    --land FINAL_DEM\Boundary.shp ^
    --water FINAL_DEM\Rivers.shp FINAL_DEM\Lakes.shp
```

Takes about four seconds. Raise `--simplify` to shrink the file; past about 3
the coastline starts to facet visibly. If a straight line appears across the
map, lower `--max-edge`; if a real dyke or causeway disappears, raise it.

Long-form pages put dark text on a paper-coloured panel over the dark shell.
That's deliberate — long text on a dark background is tiring, and photographs
need a neutral surround.

Muted text sits at 72% opacity, not 50%, so body copy clears WCAG AA. If you
lighten it further, check the contrast ratio first.

## Typeface

**Jost\*** (Owen Earl / indestructible type\*, OFL) — a Futura revival. One
variable file, weights 100–900, 25 KB subsetted. Sets the entire interface.

**Michroma** (Vernon Adams, OFL) — after Eurostile/Microgramma, 1952. Squared,
wide, one weight, 17 KB. The home page hero and nothing else; it has no
small-size behaviour worth having.

Futura plus Eurostile is the International Style / Expo 86 pairing. Both live in
`static/fonts/`, served from your own domain — no Google Fonts request.

Two things to know if you change the hero face: Michroma sets **1.40× wider**
than Jost at the same size, which is why the hero caps at 4rem rather than
6.5rem, and why its tracking is −0.005em rather than −0.035em. Squared faces
fall apart when you tighten them.

Basteleur (Velvetyne) is still in `static/fonts/`, unreferenced. Delete it or
keep it — it costs nothing unless something links to it.

## Still to write

- `content/work/bill-44-thesis.md` — thesis summary, especially preliminary findings
- Photographs
- A real `og-default.png` if you'd like something other than the generated card
