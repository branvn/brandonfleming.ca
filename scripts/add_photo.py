"""Prepare a photograph for content/photography/.

    python scripts/add_photo.py content/photography/D75_2313.jpg crescent-beach-lightning

Three jobs, none of them interesting, all of them easy to forget:

  1. Resize to 2200px on the long edge. The gallery template only ever serves
     1400px in the grid and 2000px in the lightbox, so anything larger is bytes
     committed to the repo that no visitor ever downloads. A straight-off-the-
     camera D750 frame is 3840px and about a megabyte.

  2. Rename to a slug. Every photo on the page is keyed by filename in
     _index.md, so D75_2313.jpg would have to appear in the front matter too.

  3. Keep the EXIF. Pillow drops it on save unless you hand it back explicitly,
     and these files carry Artist and Copyright fields worth keeping.

The original is moved to _originals/, which is gitignored, rather than deleted.
It must not stay in content/photography/: Hugo publishes every resource in a
page bundle whether or not anything references it, so a stray original ships at
full size and shows up on the page with no caption.

Prints the shooting data afterwards so the caption block can be filled in
without opening the file in anything else.
"""

from __future__ import annotations

import shutil
import sys
from fractions import Fraction
from pathlib import Path

from PIL import ExifTags, Image

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "content" / "photography"
ORIGINALS = ROOT / "_originals"

LONG_EDGE = 2200
QUALITY = 86


def shutter(seconds: float) -> str:
    """Write an exposure the way a photographer would, not the way EXIF does."""
    if seconds >= 1:
        return f"{seconds:g}s"
    return f"1/{Fraction(1 / seconds).limit_denominator(8000)}"


def report(img: Image.Image) -> None:
    exif = img.getexif()
    tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
    sub = {ExifTags.TAGS.get(k, k): v for k, v in exif.get_ifd(0x8769).items()}

    print("\nShooting data, for the caption block in _index.md:\n")

    # EXIF writes these shouting: Make is "NIKON CORPORATION" and Model is
    # "NIKON D750", so pasting both together gets you "Nikon NIKON D750".
    make = (tags.get("Make") or "").split()[:1]
    make = make[0].title() if make else ""
    model = str(tags.get("Model") or "").strip()
    if make and model.upper().startswith(make.upper()):
        camera = model.title()
    else:
        camera = f"{make} {model}".strip()
    print(f'    camera   = "{camera}"')

    lens = sub.get("LensModel")
    print(f'    lens     = "{lens}"' if lens
          else "    lens     = ...        # not in EXIF, you have to know this one")

    bits = []
    if "FocalLength" in sub:
        bits.append(f"{float(sub['FocalLength']):g}mm")
    if "FNumber" in sub:
        bits.append(f"f/{float(sub['FNumber']):g}")
    if "ExposureTime" in sub:
        bits.append(shutter(float(sub["ExposureTime"])))
    if "ISOSpeedRatings" in sub:
        bits.append(f"ISO {sub['ISOSpeedRatings']}")
    if bits:
        print(f'    settings = "{" · ".join(bits)}"')

    if "DateTimeOriginal" in sub:
        print(f'\n    taken {sub["DateTimeOriginal"]}')


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2

    src = Path(argv[0])
    if not src.is_absolute():
        src = ROOT / src
    slug = argv[1].removesuffix(".jpg")
    dest = PHOTOS / f"{slug}.jpg"

    if not src.exists():
        print(f"No such file: {src}")
        return 1
    if dest.exists() and dest.resolve() != src.resolve():
        print(f"{dest.relative_to(ROOT)} already exists. Pick another slug.")
        return 1

    img = Image.open(src)
    before = img.size, src.stat().st_size

    # Hand the EXIF back on save. Pillow will not carry it across on its own.
    exif = img.info.get("exif")

    if max(img.size) > LONG_EDGE:
        img.thumbnail((LONG_EDGE, LONG_EDGE), Image.LANCZOS)

    img.save(dest, "JPEG", quality=QUALITY, optimize=True,
             progressive=True, **({"exif": exif} if exif else {}))

    ORIGINALS.mkdir(exist_ok=True)
    if src.resolve() != dest.resolve():
        shutil.move(str(src), str(ORIGINALS / src.name))

    (w, h), size = before
    print(f"{src.name}  {w}x{h}, {size / 1024:.0f} KB")
    print(f"  -> content/photography/{dest.name}  "
          f"{img.size[0]}x{img.size[1]}, {dest.stat().st_size / 1024:.0f} KB")
    print(f"  -> original moved to _originals/{src.name}")

    report(Image.open(dest))

    print(f"\nNow add a [captions.\"{dest.name}\"] block to "
          f"content/photography/_index.md, then run scripts/check_site.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
