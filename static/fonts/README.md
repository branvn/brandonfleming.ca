# Fonts

Self-hosted. No Google Fonts, no Fontshare CDN — one request to your own domain,
and nothing about your visitors leaves it.

## Basteleur

Download from **<https://velvetyne.fr/fonts/basteleur/>** (Keussel, SIL Open Font
License 1.1 — free for commercial use, self-hosting explicitly permitted).

Put these two files in this folder:

```
assets/fonts/Basteleur-Moonlight.woff2
assets/fonts/Basteleur-Bold.woff2
```

If the download only gives you `.otf` or `.ttf`, convert them first — woff2 is
roughly half the size and every browser since 2016 supports it:

- <https://cloudconvert.com/ttf-to-woff2>, or
- `pip install fonttools brotli` then
  `fonttools ttLib.woff2 compress Basteleur-Moonlight.otf`

Then uncomment the `@font-face` block at the top of `assets/css/main.css`.

## Where it's used

Basteleur is a display face — it belongs in headlines and nowhere else. The
stylesheet applies it only to:

- the hero on the home page
- page and article `h1`
- work card titles

Deliberately **not** applied to the nav, the brand mark, section labels, or any
body text. Those are small, uppercase and heavily tracked; a bastard serif there
is illegible and looks like a mistake.

## Licence note

Keep the OFL licence file that ships with the download in this folder. The OFL
requires the licence to travel with the font, including when you redistribute it
as part of a website.
