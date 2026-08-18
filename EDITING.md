# Editing the words on brandonfleming.ca

A plain-language guide to changing any text a visitor can see. Written for you,
not for a developer.

You do not need to understand Hugo to use this. You need to know which file to
open, and the three commands at the end that put your change online.

---

## The one rule

**Edit files in `content/`. Leave `layouts/` alone.**

`content/` holds the words. `layouts/` holds the machinery that arranges them.
Almost everything you will ever want to change lives in `content/`, and a
mistake there breaks one page at worst. A mistake in `layouts/` can break the
whole site.

There is a short list at the bottom of things that unavoidably live in
`layouts/`. Treat that list as the exception.

---

## Where is the text I want to change?

| What you see on the site | File to open |
|---|---|
| The big headline on the home page | `content/_index.md` |
| The three paragraphs under it | `content/_index.md` |
| Everything on the About page | `content/about.md` |
| A project page | `content/work/<that-project>.md` |
| The blurb at the top of the Work page | `content/work/_index.md` |
| The blurb at the top of the Writing page | `content/writing/_index.md` |
| The blurb at the top of the Photography page | `content/photography/_index.md` |
| Photo captions, Film | `content/photography/film/_index.md` |
| Photo captions, Digital | `content/photography/digital/_index.md` |
| The Bill 44 tracker intro text | `content/tracker/_index.md` |
| Tracker entry notes | `data/tracker.json` |
| Your name, tagline, email, LinkedIn | `hugo.toml` |
| The menu at the top (Work, Writing, ...) | `hugo.toml` |

The four project pages are:

```
content/work/bill-44-thesis.md            The Affordability Gap
content/work/alc-land-loss.md             Land Lost to ALC Applications
content/work/townhouses-before-transit.md Townhouses Before Transit
content/work/protest-to-policy.md         Protest to Policy
```

---

## How a content file is built

Every file in `content/` has two parts.

```
+++
title = "The Affordability Gap"
summary = "Does small-scale upzoning actually produce affordable housing?"
weight = 10
+++

## The question

This is the actual body text. Write normally.
```

**The part between the `+++` lines is the settings.** Title, summary, dates,
which order things appear in. Each line is `name = "value"` and the value needs
its quotes.

**Everything after the closing `+++` is the page text.** Write it like an email.
A blank line starts a new paragraph.

### Formatting the body

```
## A heading

**bold text** and *italic text*

- a bullet
- another bullet

[a link](https://example.com)
```

That is Markdown, and that is essentially all of it.

---

## Settings you will actually touch

Not every file has all of these. Open one and see.

| Setting | What it does |
|---|---|
| `title` | The page heading, and the browser tab |
| `summary` | One sentence. Shows on cards and in Google results |
| `weight` | Sort order. **Lower numbers appear first** |
| `draft` | `true` hides the page from the live site completely |
| `date` | Publication date |

On project pages you also get:

| Setting | What it does |
|---|---|
| `year` | The year shown on the card, e.g. `"2025 – present"` |
| `context` | Where the work was done, e.g. the course and university |
| `role` | Your role, e.g. `"Sole researcher"` |
| `tools` | A list in square brackets: `["ArcGIS Pro", "Excel"]` |
| `status` | Set to `"in-progress"` to show the orange tag. Blank for nothing |

On photography sections:

| Setting | What it does |
|---|---|
| `gear` | The camera line under the heading |
| `cover` | Which photo is the thumbnail for that gallery |
| `[captions."file.jpg"]` | The caption block for one photo, explained below |

---

## Common jobs

### Change the home page headline

Open `content/_index.md`. The headline is split in two so the second half can be
the colour that fades to teal:

```
heroLead   = "Land use policy in Metro Vancouver,"
heroAccent = "read through the data it leaves behind."
```

Keep both short. The typeface used there is very wide, and a long line will wrap
awkwardly on a phone.

### Reorder the project cards

Open each project file and change `weight`. Lower shows first.

```
weight = 10    <- appears first
weight = 20
weight = 30
```

### Hide a page without deleting it

Set `draft = true` in its settings. It vanishes from the live site. To see draft
pages while previewing, run `hugo server -D` instead of `hugo server`.

### Add a new project page

```powershell
hugo new work/my-new-project.md
```

That creates the file with every setting listed and explained. Fill it in and
set `draft = false` when you want it live.

**The filename becomes the web address.** `my-new-project.md` becomes
`brandonfleming.ca/work/my-new-project/`. Use lowercase and hyphens, never
spaces. Renaming the file later breaks any link anyone has saved.

### Add a photo

1. **Resize it first.** Long edge about 2200 pixels. This matters more than it
   sounds: Git keeps every version of every file forever, so a 25 MB original
   stays in the repository permanently even if you delete it afterwards.
2. Drop the `.jpg` into `content/photography/film/` or `.../digital/`.
3. Add a caption block in that folder's `_index.md`:

```toml
  [captions."granville-bridge.jpg"]
    caption = "What the photo is"
    place   = "Where it was taken"
    alt     = "A description for someone who cannot see the image"
```

The filename in quotes must match the actual file exactly, including `.jpg`.
If it does not match, the caption silently does not appear.

`alt` is not optional in spirit. It is what a screen reader announces, and it is
what Google indexes.

### Write a tracker note

`data/tracker.json` is the one file here that is not Markdown. It looks like:

```json
{
  "title": "R162: Small-Scale Multi-Unit Housing Review Framework",
  "note": ""
}
```

Type your note between the quotes of `"note"`. **An entry only appears on the
site once its note is not empty.** That is deliberate.

Two things to watch, because JSON is fussier than Markdown:

- If your note contains a double quote, write it as `\"`.
- Do not remove or add commas between entries.

After editing, check it before publishing:

```powershell
python -c "import json;json.load(open('data/tracker.json',encoding='utf-8'));print('valid')"
```

If that prints `valid`, you are fine. If it prints an error, it tells you the
line number.

### Change your tagline, email, or LinkedIn

These are in `hugo.toml` under `[params]`, and they appear in several places at
once, so changing them here changes them everywhere:

```toml
fullName = "Brandon Fleming"
tagline  = "Urban Studies Graduate Student | GIS & Policy Analysis"
location = "Surrey, British Columbia"
email    = "contact@brandonfleming.ca"
linkedin = "https://www.linkedin.com/in/brandon-fleming-/"
resume   = "/documents/brandon-fleming-resume.pdf"
```

The coordinates in the top right corner are `lat`, `lng` and `elev` in the same
block. They point at a public civic landmark, not your home.

### Rename or reorder the menu

Also `hugo.toml`, near the bottom:

```toml
[[menu.main]]
  name = "Work"
  pageRef = "/work"
  weight = 10
```

Change `name` to rename it. Change `weight` to reorder it. Lower comes first.

### Replace your résumé

Save the new PDF over `static/documents/brandon-fleming-resume.pdf`, keeping the
same filename. Every link to it keeps working, including ones already sent out
on job applications.

### Take the whole site offline temporarily

In `hugo.toml`, set `underConstruction = true`. A holding card covers
everything. Set it back to `false` to restore.

---

## Seeing your change before anyone else does

```powershell
cd "$env:USERPROFILE\Desktop\brandonfleming.ca"
hugo server
```

Open <http://localhost:1313>. It reloads the moment you save a file. Press
`Ctrl+C` in the terminal to stop it.

**Always do this before publishing.** It costs ten seconds and catches almost
everything.

If it reports an error, read the last line. It names the file and the line
number, and it is nearly always a missing quote in the settings block.

---

## Publishing

Three commands, every time:

```powershell
git add .
git commit -m "Describe what you changed"
git push
```

The live site updates itself a minute or two later. You can watch it under your
Cloudflare Pages project, in Deployments.

If a build fails, the previous version stays up. You cannot break the live site
by pushing a typo; you can only fail to update it.

---

## Four traps worth knowing

**1. In the settings block, keep plain lines above bracketed ones.**

This one has bitten this site before. In TOML, a heading in square brackets
swallows everything after it.

```toml
title = "My Project"      <- fine, above the bracket
[download]
  url = "/documents/x.pdf"
summary = "..."           <- BROKEN. Now belongs to [download], invisible
```

Put every plain `name = "value"` line **above** the first `[bracketed]` heading.

**2. The filename is the web address.** Renaming a file changes its URL and
breaks any existing link to it.

**3. Photos must be resized before they go in**, not after. See above.

**4. No em dashes.** Use a comma, a colon, or a full stop. This is a house style
choice and the whole site follows it.

---

## Text that is not in `content/`

A few phrases are built into the page templates rather than the content files.
Changing these means editing `layouts/`, which is the one place worth being
careful. Preview with `hugo server` before publishing any of them.

| Text | File |
|---|---|
| "Selected work" and "Recent writing" | `layouts/index.html` |
| "Read more →" on project cards | `layouts/partials/work-card.html` |
| "View →" on gallery cards | `layouts/photography/list.html` |
| "All work →" | `layouts/index.html` |
| "Based in", "Focus", "Contact" | `layouts/partials/footer.html` |
| "Housing policy, agricultural land use, and spatial analysis" | `layouts/partials/footer.html` |
| "Off the map" and the 404 text | `layouts/404.html` |
| "Year", "Context", "Role", "Tools", "Status" labels | `layouts/work/single.html` |
| "In progress" tag | `layouts/partials/work-card.html` |
| "Bill 44 Tracker" in the menu | `layouts/partials/header.html` |

Each of these is plain text sitting between HTML tags. Change the words, leave
the surrounding `<p>`, `<h2>` and `{{ }}` alone.

---

## If something goes wrong

**A page vanished.** Check `draft = true` in its settings.

**A caption is not showing.** The filename in `[captions."..."]` does not match
the actual file. Check the spelling and the `.jpg`.

**A setting seems ignored.** It is probably below a `[bracketed]` heading. See
trap 1.

**The site did not update.** Check the commit reached GitHub, then check
Deployments in Cloudflare. If both look right, hard refresh with
`Ctrl+Shift+R`.

**You want the previous version back.** Nothing is ever lost. Every change is
saved in Git, and any past version can be restored.
