#!/usr/bin/env python3
"""
Build the contour plate for the site background.

Reads vector layers only — no DEM, no raster — and writes a single SVG:

    assets/img/plate.svg

Structure of the output. This matters, because assets/js/terrain.js drives it:

    <g id="coast">                          coastline + lake and river shores
    <g class="b" data-e="10" style="--c:…">   contour band, elevation in metres
    <g class="b" data-e="20" style="--c:…">
    ...

The bands are separate groups so the cursor can light everything below a given
elevation. Nothing else in the SVG is interactive.

Inputs:
    --contours  polyline shapefile with an elevation field. The levels and the
                generalisation are whatever was chosen in GIS.
    --land      polygon shapefile of land area. Must exclude water — see the
                note on administrative edges below.
    --water     polygon layers subtracted from land (rivers, lakes). Their
                shores become part of the coast outline.

This used to read a DEM and derive both the land mask and the contours from it.
It no longer does. A DEM gave us a land mask with tile-boundary artefacts, an
inset/erosion dance to hide them, and a hard dependency on rasterio and scipy.
An authoritative land polygon is simply better input, and the contour shapefile
was already the preferred source for the lines themselves.

Administrative edges
--------------------
A land polygon is bounded partly by real shoreline and partly by lines someone
drew: a regional boundary, the international border, the edge of the export.
Drawn as coast, those read as a bug — a hard straight rule across the map.

They are separable by geometry, on two properties together. Every one of them
was drawn along a parallel or a meridian, and each runs for kilometres. Real
features that long — the dyked banks of the Fraser, the Roberts Bank causeway,
the Point Grey cliffs — all run diagonal. Cutting edges that are both longer
than --max-edge and within 3 degrees of an axis removes the boundaries and
touches nothing else. Cutting on length alone shreds the dykes; see
split_admin_edges.

Sources used to build the shipped plate:
    Contours  provincial 25 m DEM, contoured in ArcGIS Pro at a non-uniform
              interval — dense low, sparse high (see --levels)
    Land      Metro Vancouver boundary, land area only
    Water     Freshwater Atlas Rivers + Lakes, BC Data Catalogue

Usage:
    python scripts/make_plate.py --contours FINAL_DEM/Contour25m.shp \
        --land FINAL_DEM/Boundary.shp \
        --water FINAL_DEM/Rivers.shp FINAL_DEM/Lakes.shp
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img" / "plate.svg"

# Frame, in lon/lat, fitted to the extent of the contour export.
#
# Aspect is 1.63. The SVG uses preserveAspectRatio="slice", so the plate fills
# the viewport and crops rather than letterboxing; a squarer frame loses its top
# and bottom on a widescreen monitor. Keep this between about 1.6 and 1.75, and
# widen the longitude span rather than the latitude if you want more ground —
# latitude is what holds the North Shore at one end and White Rock at the other.
FRAME = dict(west=-123.354, east=-122.356, south=49.003, north=49.403)

MEAN_LAT = 49.203          # for the equirectangular scale factor
M_PER_DEG_LAT = 110950.0


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------

def load_polygons(paths, target=4326):
    """Union polygon shapefiles into one geometry in lon/lat.

    Reprojects per file — the layers in a single folder are routinely in three
    different CRSs (UTM 10N, BC Albers, geographic CSRS) and that is fine.
    """
    import shapefile
    from shapely.geometry import shape
    from shapely.ops import unary_union, transform
    from pyproj import CRS, Transformer

    geoms = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            print(f"    ! missing, skipped: {p}", file=sys.stderr)
            continue
        prj = p.with_suffix(".prj")
        src = CRS.from_wkt(prj.read_text()) if prj.exists() else CRS.from_epsg(target)
        fwd = None
        if not src.equals(CRS.from_epsg(target)):
            fwd = Transformer.from_crs(src, CRS.from_epsg(target), always_xy=True).transform

        n = 0
        for sh in shapefile.Reader(str(p)).iterShapes():
            if sh.shapeType == 0 or not sh.points:
                continue
            g = shape(sh.__geo_interface__)
            if not g.is_valid:
                g = g.buffer(0)
            if g.is_empty:
                continue
            geoms.append(transform(fwd, g) if fwd else g)
            n += 1
        print(f"    {p.name}: {n} polygons")

    if not geoms:
        return None
    return unary_union(geoms)


def to_pixels(coords, frame, W, H):
    """Equirectangular lon/lat -> canvas pixels. Origin top-left."""
    a = np.asarray(coords, float)
    x = (a[:, 0] - frame["west"]) / (frame["east"] - frame["west"]) * W
    y = (frame["north"] - a[:, 1]) / (frame["north"] - frame["south"]) * H
    return np.column_stack([x, y])


def split_admin_edges(px, limit, max_offaxis=3.0):
    """Break a polyline at edges that are both long and axis-aligned.

    This is what removes administrative boundaries from the coast, and it needs
    both halves of the test.

    Length alone is not enough. The Fraser is dyked, so its banks run straight
    for two or three kilometres at a stretch, and a plain length cut shreds them
    along with the boundaries. But every administrative edge here was drawn
    along a parallel or a meridian — the international border, the northern edge
    of the export, the regional line east of Langley — while the dykes, the
    causeways and the cliffs all run diagonal. In the shipped data the ten
    longest edges are all within 1.3 degrees of an axis, and nothing real of
    comparable length is within 6.

    Run this *after* simplification, not before. Some of those boundaries are
    densified — a straight line carrying a vertex every 50 m — and as raw
    geometry they look exactly like shoreline. Douglas-Peucker collapses each
    run back into the single long edge it really is, and only then does the test
    mean anything.

    Angles are measured in canvas space, where a parallel is still horizontal
    and a meridian still vertical, so the axis test survives the projection.
    """
    if len(px) < 2:
        return []
    v = px[1:] - px[:-1]
    d = np.hypot(*v.T)
    offaxis = np.abs(np.degrees(np.arctan2(v[:, 1], v[:, 0]))) % 90.0
    offaxis = np.minimum(offaxis, 90.0 - offaxis)
    cuts = np.where((d > limit) & (offaxis < max_offaxis))[0]
    if not len(cuts):
        return [px]
    out, start = [], 0
    for c in cuts:
        if c + 1 - start >= 2:
            out.append(px[start:c + 1])
        start = c + 1
    if len(px) - start >= 2:
        out.append(px[start:])
    return out


def split_at_frame(px, W, H, pad=2):
    """Break a polyline where it leaves the frame.

    Without this, a line that exits and re-enters gets a straight chord drawn
    across the whole plate.
    """
    inside = ((px[:, 0] >= -pad) & (px[:, 0] <= W + pad) &
              (px[:, 1] >= -pad) & (px[:, 1] <= H + pad))
    out, start = [], None
    for i in range(len(px) + 1):
        if i < len(px) and inside[i]:
            if start is None:
                start = i
        elif start is not None:
            if i - start >= 2:
                out.append(px[start:i])
            start = None
    return out


def rdp(pts, eps):
    """Douglas-Peucker. Iterative, so a 40,000-vertex ring can't blow the stack."""
    pts = np.asarray(pts, float)
    if len(pts) < 3:
        return pts
    keep = np.zeros(len(pts), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        ab = b - a
        L = float(np.hypot(*ab))
        seg = pts[i + 1:j]
        d = (np.hypot(*(seg - a).T) if L < 1e-9
             else np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / L)
        k = int(np.argmax(d))
        if d[k] > eps:
            k += i + 1
            keep[k] = True
            stack += [(i, k), (k, j)]
    return pts[keep]


def emit(seg):
    """One polyline -> SVG path data, integer coordinates.

    Sub-pixel precision is pointless on a plate scaled to fill a viewport, and
    the decimals cost more than everything else in the file put together.
    """
    return "M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in seg)


# --------------------------------------------------------------------------
# layers
# --------------------------------------------------------------------------

def build_coast(land, water, frame, W, H, eps, max_edge_px, min_pts):
    """Outline of land-minus-water, with administrative edges removed."""
    from shapely.geometry import MultiLineString

    if water is not None:
        land = land.difference(water)

    lines = land.boundary
    lines = lines.geoms if hasattr(lines, "geoms") else [lines]

    out, dropped = [], 0
    for ln in lines:
        if ln.is_empty or len(ln.coords) < 2:
            continue
        px = rdp(to_pixels(list(ln.coords), frame, W, H), eps)
        for run in split_admin_edges(px, max_edge_px):
            for seg in split_at_frame(run, W, H):
                if len(seg) < min_pts:
                    dropped += 1
                    continue
                out.append(emit(seg))
    print(f"  coast: {len(out)} paths kept, {dropped} too short")
    if not out:
        sys.exit("coast is empty — check --land covers the frame and --max-edge "
                 "is not so small that it is cutting real shoreline")
    return out


def build_bands(path, frame, W, H, eps, min_pts, levels=None):
    """Contour polylines -> {elevation: [svg path data, ...]}."""
    import shapefile
    from pyproj import CRS, Transformer

    path = Path(path)
    r = shapefile.Reader(str(path))
    fields = [f[0] for f in r.fields[1:]]
    key = next((f for f in fields
                if f.lower() in ("contour", "elev", "elevation", "level")), None)
    if key is None:
        sys.exit(f"{path.name}: no elevation field found in {fields}")
    ki = fields.index(key)

    prj = path.with_suffix(".prj")
    src = CRS.from_wkt(prj.read_text()) if prj.exists() else CRS.from_epsg(4326)
    tr = None
    if not src.equals(CRS.from_epsg(4326)):
        tr = Transformer.from_crs(src, CRS.from_epsg(4326), always_xy=True)

    want = set(levels) if levels else None
    out, kept, dropped, skipped = {}, 0, 0, 0

    for sr in r.iterShapeRecords():
        sh = sr.shape
        if sh.shapeType == 0 or not sh.points:
            continue
        lvl = float(sr.record[ki])
        if want is not None and lvl not in want:
            skipped += 1
            continue

        pts = sh.points
        if tr is not None:
            xs, ys = tr.transform([q[0] for q in pts], [q[1] for q in pts])
            pts = list(zip(xs, ys))
        px = to_pixels(pts, frame, W, H)

        for seg in split_at_frame(px, W, H):
            if len(seg) < min_pts:
                dropped += 1
                continue
            seg = rdp(seg, eps)
            if len(seg) < 3:
                dropped += 1
                continue
            out.setdefault(lvl, []).append(emit(seg))
            kept += 1

    note = f", {skipped} off-list" if want is not None else ""
    print(f"  {path.name}: {len(out)} levels, {kept} paths kept, "
          f"{dropped} too short{note}")
    if not out:
        sys.exit(f"{path.name}: no contours fell inside the frame")
    return out


# --------------------------------------------------------------------------
# colour
# --------------------------------------------------------------------------

# Hypsometric ramp, used for the *lit* state only. Unlit bands stay a uniform
# faint teal so the plate reads as a map rather than a heatmap; colour arrives
# only as the pointer's water line passes each band.
RAMP = [
    (0.00, (0x4f, 0xc9, 0xa6)),   # sea level — green-teal
    (0.22, (0x8f, 0xd0, 0x7a)),   # low slopes — green
    (0.42, (0xd9, 0xc4, 0x6a)),   # yellow
    (0.62, (0xdd, 0xa1, 0x5e)),   # sand
    (0.80, (0xd2, 0x70, 0x3f)),   # orange
    (0.92, (0xc9, 0x50, 0x3f)),   # red
    (1.00, (0xf4, 0xef, 0xe6)),   # summit — near white
]


def ramp_hex(t: float) -> str:
    t = min(max(t, 0.0), 1.0)
    for i in range(1, len(RAMP)):
        if t <= RAMP[i][0]:
            (p0, c0), (p1, c1) = RAMP[i - 1], RAMP[i]
            f = (t - p0) / (p1 - p0 or 1)
            return "#%02x%02x%02x" % tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
    return "#%02x%02x%02x" % RAMP[-1][1]


def band_colours(bands, ink_weight=0.70):
    """Assign each level a ramp colour.

    Equal-interval on elevation looks correct on paper and fails here. The
    levels above 400 m hold a few percent of the total line length and sit in a
    sliver at the top of the frame that `slice` then crops, so the warm end of
    the ramp is effectively invisible.

    Classifying by cumulative ink instead — a quantile break — gives every
    colour comparable presence. Blended with the elevation position so the
    ordering still means something rather than being purely cosmetic. The
    elevation term is square-rooted because the level list is itself non-uniform
    and bottom-heavy; a linear term would push almost every band into the first
    tenth of the ramp.
    """
    lo, hi = min(bands), max(bands)
    ink = {lvl: sum(d.count("L") for d in ds) for lvl, ds in bands.items()}
    total = sum(ink.values()) or 1
    run, out = 0.0, {}
    for lvl in sorted(bands):
        q = run / total
        run += ink[lvl]
        e = ((lvl - lo) / (hi - lo)) ** 0.5 if hi > lo else 0.0
        out[lvl] = ramp_hex(ink_weight * q + (1 - ink_weight) * e)
    return out


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--contours", type=Path, required=True,
                    help="polyline shapefile with an elevation field")
    ap.add_argument("--land", type=Path, nargs="+", required=True,
                    help="polygon shapefile(s) of land area")
    ap.add_argument("--water", type=Path, nargs="*", default=[],
                    help="polygon layers subtracted from land")
    ap.add_argument("--levels", type=float, nargs="*", default=None,
                    help="keep only these elevations; default is every level "
                         "present in the shapefile")
    ap.add_argument("--width", type=int, default=1600,
                    help="canvas width in SVG units; height follows the frame")
    ap.add_argument("--simplify", type=float, default=1.6,
                    help="Douglas-Peucker tolerance in canvas units; raise to "
                         "shrink the file, past ~3 the coastline facets visibly")
    ap.add_argument("--max-edge", type=float, default=3500.0,
                    help="drop land-boundary edges longer than this many metres "
                         "that also run within 3 degrees of an axis; this is what "
                         "removes administrative lines from the coast")
    ap.add_argument("--min-area", type=float, default=2e4,
                    help="drop land polygons smaller than this many square metres")
    ap.add_argument("--frame", type=float, nargs=4, default=None,
                    metavar=("WEST", "EAST", "SOUTH", "NORTH"),
                    help="override the frame, in degrees")
    args = ap.parse_args()

    frame = dict(FRAME)
    if args.frame:
        frame = dict(zip(("west", "east", "south", "north"), args.frame))

    # Height from the frame, so ground distance stays square on the canvas.
    dlon = frame["east"] - frame["west"]
    dlat = frame["north"] - frame["south"]
    km_x = dlon * M_PER_DEG_LAT * math.cos(math.radians(MEAN_LAT)) / 1000
    km_y = dlat * M_PER_DEG_LAT / 1000
    W = args.width
    H = round(W * km_y / km_x)
    m_per_px = km_x * 1000 / W
    print(f"frame: {km_x:.1f} x {km_y:.1f} km, aspect {km_x/km_y:.2f}, "
          f"{W}x{H} canvas, {m_per_px:.0f} m/px")
    if not 1.5 <= km_x / km_y <= 1.85:
        print("  ! aspect is outside 1.5–1.85; preserveAspectRatio=\"slice\" "
              "will crop hard on some screens", file=sys.stderr)

    print("land…")
    land = load_polygons(args.land)
    if land is None:
        sys.exit("no land polygons loaded")
    # The export carries a long tail of zero-area slivers. Deg^2 -> m^2 is
    # approximate and only needs to be right to an order of magnitude here.
    deg2_to_m2 = (M_PER_DEG_LAT ** 2) * math.cos(math.radians(MEAN_LAT))
    parts = list(land.geoms) if hasattr(land, "geoms") else [land]
    kept = [g for g in parts if g.area * deg2_to_m2 >= args.min_area]
    print(f"    {len(kept)} of {len(parts)} polygons above {args.min_area/1e4:.0f} ha")
    if kept:
        from shapely.ops import unary_union
        land = unary_union(kept)

    print("water…")
    water = load_polygons(args.water) if args.water else None

    print("coast…")
    coast = build_coast(land, water, frame, W, H,
                        args.simplify * 0.8, args.max_edge / m_per_px, 4)

    print("contours…")
    bands = build_bands(args.contours, frame, W, H, args.simplify, 10, args.levels)
    lv = sorted(bands)
    print(f"  levels: {', '.join(f'{v:.0f}' for v in lv)}")

    colours = band_colours(bands)
    parts = [
        # "slice" = CSS background-size: cover. The plate fills the viewport and
        # crops rather than letterboxing on wide monitors.
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'preserveAspectRatio="xMidYMid slice" aria-hidden="true">',
        '<g id="coast">' + "".join(f'<path d="{d}"/>' for d in coast) + "</g>",
    ]
    for lvl in lv:
        parts.append(f'<g class="b" data-e="{lvl:.0f}" style="--c:{colours[lvl]}">'
                     + "".join(f'<path d="{d}"/>' for d in bands[lvl]) + "</g>")
    parts.append("</svg>")
    svg = "".join(parts)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")

    import gzip
    npaths = sum(len(v) for v in bands.values()) + len(coast)
    print(f"wrote {OUT.relative_to(ROOT)}  {len(svg)/1024:.0f} KB raw, "
          f"{len(gzip.compress(svg.encode()))/1024:.0f} KB gzipped, {npaths} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
