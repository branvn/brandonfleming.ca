+++
title = "Colophon"
draft = true

summary = "How this site is built, and how the contour map behind every page was made."

# DRAFT. Nothing publishes while draft = true.
#
# Written by Claude from the build itself, so every number here is measured
# rather than remembered. It is in my voice, not yours: read it, cut what feels
# overstated, and make the last section sound like you before setting
# draft = false.
#
# When you publish it, add a link in layouts/partials/footer.html. It belongs in
# the footer rather than the main nav, which should stay about planning.
+++

The background of every page on this site is a contour map of the Lower
Mainland. It isn't a photograph or a screenshot, and it isn't a map library
calling out to somebody's tile server. It's a single SVG file I generate from
provincial GIS data with a Python script in this repository.

This page explains how, partly because the decisions are more interesting than
the result, and partly because a map with no methodology is just decoration.

## The data

Three layers, from three sources, in three different coordinate systems:

- **Contours** from a provincial 25 m elevation model, contoured in ArcGIS Pro
  at a non-uniform interval. Geographic coordinates, NAD83 CSRS.
- **Land area** from the Metro Vancouver boundary, land only. UTM Zone 10N.
- **Hydrography** from the BC Freshwater Atlas, rivers and lakes. BC Albers.

Nothing is reprojected by hand. The script reads each file's own `.prj` and
transforms it on the way in, which is the only sane way to handle a folder where
every layer disagrees with the others.

An earlier version of the pipeline read a digital elevation model and derived
both the land mask and the contours from the raster. That approach is gone. It
required merging tile mosaics with missing squares, eroding the footprint to
hide tile boundaries, and it still produced a coastline inferred from where data
happened to exist. An authoritative land polygon is simply better input, and
dropping the raster removed three dependencies and took the runtime from minutes
to about four seconds.

## The contour interval is deliberately uneven

The levels are **10, 20, 35, 55, 80, 110, 150, 200, 260, 330, 410, 500, 600,
720, 850, 1000 and 1150 metres**. Seventeen of them, and the spacing widens as
it climbs.

This is the decision I would defend hardest. The first version used a uniform
35 m interval, which is what you get by default and what looks correct on paper.
It was badly misallocated. Nearly 40% of the land in this frame sits below 35 m,
and that 40% received two contour lines. Under 9% of the land sits above 400 m,
and that received twenty-three.

The result was a map where the North Shore was an unreadable mess of ink and the
Fraser delta, which is the part I actually study, was almost blank.

Lowering the interval uniformly makes this worse rather than better: it adds
lines everywhere, so the mountains fill in faster than the flats. The fix is to
bias the levels themselves. Under the current list, the ground below 80 m carries
57% of the ink on the map instead of 12.7%.

That matters beyond aesthetics. This is a region whose housing sits on a
floodplain. A map of Metro Vancouver that renders the delta as empty space is
making an argument, whether or not anyone intended it.

## Telling a shoreline from a line somebody drew

A land polygon is bounded partly by real coast and partly by administrative
fiction: the international border, the regional line east of Langley, the edge
of the export. Drawn as coastline, those read as a bug. A hard straight rule
across a map is the first thing that tells a reader not to trust it.

Length alone will not separate them, and this is the part that took two attempts.
The Fraser is dyked, so its banks run genuinely straight for two or three
kilometres. Cutting every long edge removed the borders and destroyed most of the
shoreline through Richmond and Delta at the same time.

What does separate them is that every administrative edge here was drawn along a
parallel or a meridian. The ten longest edges in the boundary layer all sit
within 1.3 degrees of an axis. Nothing real of comparable length is within six.
So the test is length **and** alignment, and it has to run after simplification,
because some of those boundaries arrive densified with a vertex every 50 metres
and look exactly like coast until Douglas-Peucker collapses them back.

## Colour by ink, not by elevation

Each band carries a colour from a hypsometric ramp, green at sea level through
sand and orange to near-white at the summits.

Assigning those colours by equal elevation intervals fails here. The bands above
400 m hold a few percent of the total line length and sit in a sliver at the top
of the frame that the crop then cuts off, so the warm end of the ramp is
effectively invisible. Instead the classification is a quantile break on
cumulative line length, blended with elevation position so the ordering still
means something. Every colour ends up with comparable presence on screen.

## What it costs

**1,116 paths. 199 KB of SVG, 77 KB gzipped.** Coordinates are written as
integers, because sub-pixel precision is meaningless on an image scaled to fill a
browser window and the decimals cost more than everything else combined.

The whole home page is about 127 KB gzipped: the map, the two typefaces, the
stylesheet and one small script. There are no third-party requests on any page.
No CDN, no analytics, no Google Fonts, nothing phoning anywhere.

## The one piece of interaction

Move the cursor up the page and a threshold rises with it. Every contour band at
or below that threshold lights up, taking its colour from the ramp. It reads as a
water line rising across the delta.

It is deliberately cheap. No canvas, no per-frame redraw, no reflow. Moving the
pointer only touches the page when the threshold actually crosses a band
boundary, which is at most a couple of dozen operations and usually none. On a
touchscreen there is no cursor, so scroll position drives it instead and the
water rises as you read down the page.

If you have reduced motion enabled, none of this happens. With JavaScript
switched off entirely, the map is still there. It is simply a map.

## Everything else

**Type** is Jost\*, a Futura revival, one variable file at 25 KB, for the whole
interface. The home page headline is Michroma, after Eurostile, at 17 KB. Futura
with Eurostile is the International Style pairing, and locally it is the Expo 86
pairing, which felt right for a site about this region. Both are served from this
domain.

**Long-form pages** put dark text on a paper-coloured panel over the dark shell.
Long text on a dark background is tiring to read, and photographs need a neutral
surround.

**Built with Hugo**, hand-written templates, no theme. Hosted on Cloudflare
Pages, rebuilt automatically on every push. The whole thing is a folder of flat
files: no database, no CMS, nothing to keep patched.

**The source is public.** The map generator is `scripts/make_plate.py`, and it
is commented at length, including the mistakes.
