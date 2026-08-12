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
  img/contours.svg  the background terrain
static/           files served as-is (PDFs, images, favicon)
data/             tracker entries and source list
scripts/          Bill 44 tracker collector
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

The background is a static SVG contour field generated from synthetic fractal
terrain. To swap in real terrain, generate contours from a Metro Vancouver DEM
and replace `assets/img/contours.svg`; the stylesheet expects `.maj` and `.min`
classes on the paths.

Long-form pages put dark text on a paper-coloured panel over the dark shell.
That's deliberate — long text on a dark background is tiring, and photographs
need a neutral surround.

Muted text sits at 72% opacity, not 50%, so body copy clears WCAG AA. If you
lighten it further, check the contrast ratio first.

## Still to write

- `content/work/bill-44-thesis.md` — thesis summary, especially preliminary findings
- `content/work/protest-to-policy.md` — ~400-word summary of the URB 660 paper
- Photographs
- A real `og-default.png` if you'd like something other than the generated card
