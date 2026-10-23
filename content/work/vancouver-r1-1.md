+++
title = "Vancouver's Multiplex Reform"
date = 2026-10-22
weight = 10
draft = false

summary = "How many net homes did Vancouver's R1-1 rezoning actually add in its first 18 months, how did that vary with the capacity each lot gained, and how did builders respond?"

year    = "2025 – present"
context = "MA thesis, Master of Urban Studies, Simon Fraser University"
role    = "Sole researcher"
tools   = ["City of Vancouver open data", "BC Assessment data", "Difference-in-differences", "Machine learning", "Semi-structured interviews"]
status  = "in-progress"

# This page was "The Affordability Gap", a study of Bill 44 in Surrey, until
# October 2026. The thesis moved to Vancouver because Surrey's permit data was
# not detailed enough to date rebuilds properly. The alias keeps every link that
# was ever shared to the old address working.
aliases = ["/work/bill-44-thesis/"]

# Header coordinates: Vancouver City Hall, where Council approved R1-1 after the
# public hearing of 14 September 2023.
lat  =   49.2606
lng  = -123.1139
elev =   40.0

# thumb = "/images/r1-1-thumb.jpg"
+++

## The question

**How many net homes did Vancouver's R1-1 reform add in its first 18 months
compared with the 18 months before; how did that change vary with the capacity
each lot gained; and how did builders respond?**

Upzoning arguments usually stop at permission. Change the rules, the reasoning
goes, and the homes follow. But permission is only the first of several
constraints, and the distance between what a zone allows and what actually gets
built has a name in the literature: the say-do gap.

This thesis measures that gap for one reform, in one city, with the policy's own
stated aims as the yardstick rather than the housing crisis. The bylaw says R1-1
exists "to enable a variety of small-scale housing options while retaining the
single lot character of the area." That is a testable claim.

## The policy

Vancouver Council approved R1-1 after a public hearing on 14 September 2023, and
it came into force on 17 October. It collapsed nine single-family zones into
one, covering roughly 65,000 lots.

On a qualifying lot it permits a multiplex of three to six strata units, scaling
with lot size: four units at 306 m² and 10 m of width, five at 464 m² and
13.4 m, six at 557 m² and 15.1 m. Seven or eight are possible, but only if every
unit is secured rental. The form is capped at 1.0 FSR and three storeys, with no
parking minimum. The lot needs rear lane access, has to sit outside the
floodplain, and must have existed before the bylaw came into force.

Two details matter more than they look. Multiplexes are a **conditional** use
with fixed rules rather than an outright one, so there is a process between
permission and permit, and a faster multiplex stream was only added in October
2024. And floor area above 0.7 FSR carries a fixed-rate density bonus charge
that varies across three sub-areas, split at Oak Street and Fraser Street.

The City expected about 150 multiplex projects a year. An outside report for the
Province described the reform as "designed to be minimally viable", projecting
roughly 400 net new units annually.

**R1-1 is not Bill 44 in Vancouver.** It is the City's own reform, approved
before the Province's small-scale multi-unit requirements took effect, and it
largely satisfies them. The two run in parallel and are easy to confuse.

## Method

Three strands, plus a supporting comparison.

1. **Difference-in-differences on City of Vancouver open data.** Issued building
   permits, the property tax report and parcel data. Treated lots are R1-1;
   comparison lots are untreated RT two-family lots, excluding RT-7 and RT-9
   because those were themselves upzoned in June 2024.

   Rebuilds are dated by permit *application* rather than issue, with recent
   applications weighted up to account for permits still in the queue. The
   before window runs January 2021 to October 2023, excluding a late-2021 rush
   driven by an electric-heating deadline; the after window runs January 2024 to
   June 2025. The outcome is **net homes per 1,000 lots per year**: a rebuild
   counts its new homes minus the one it removed, a laneway house counts as one.

   Standard errors are clustered by 800 m grid cell, with robustness checks
   excluding transit areas and varying the baseline, the unit-count assumptions,
   the treatment of spillovers and the start-up months.

2. **Capacity, measured three ways.** Paper capacity is what the zone allows
   before conditions apply; regulatory capacity is what survives the lot size,
   lane and floodplain tests; realized uptake is what gets permitted. Each lot's
   *headroom* is the units now allowed minus the homes a pre-reform rebuild
   would likely have produced, estimated from a model trained on 2018–2023
   rebuilds. This is what lets the result be read against capacity gained rather
   than against a flat before-and-after.

3. **Land values, from licensed BC Assessment data.** Whether land lifted,
   whether the density bonus charge or the added capacity was priced in, what
   new multiplex units sold for, which lots were redeveloped, and what repeat
   sales of existing homes show.

   This data is licensed. The analysis runs on one machine, only aggregates
   leave it, and cells below ten are suppressed. No property-level result from
   it appears here or anywhere else.

4. **About six semi-structured interviews** with builders who built multiplexes,
   City planners, and housing experts, pending SFU research ethics approval.

A second test runs inside Vancouver itself: RT-7 and RT-9, about 1,100 Kitsilano
lots upzoned on 30 June 2024 under similar rules. A land-value comparison with
Burnaby and Surrey, which upzoned under Bill 44 in July 2024 and price added
density differently, is planned for the discussion.

## What I'm finding

**These results are preliminary. They are not peer reviewed, they rest on 18
months of data, and they will be rerun in 2027.**

**The reform more than doubled sellable homes without adding much legal capacity.**
Average legal homes per lot rose only modestly, from about 3.9 to 4.5. But
ownership units more than doubled, from about 1.9 to 4.3, because what R1-1
replaced was largely rental-only suites and laneway houses. No lot lost legal
homes.

**R1-1 lots added about 6.9 net homes per 1,000 lots per year** more than
comparison lots, with a 95% confidence interval of roughly 4 to 10, and about
6.6 with transit areas excluded. The effect is very unevenly spread: about 11.7
in the west of the city, 4.0 in the east, and 0.8 through the centre.

**It worked by changing what gets built, not how often.** The rate of
redevelopment did not rise. The same flow of rebuilds simply produced more homes
each, as houses gave way to multiplexes. That is a different mechanism from the
one upzoning arguments usually assume, and it puts a ceiling on the result: the
reform is bounded by how often lots turn over.

**Uptake has run ahead of the City's projection.** More than 600 multiplex
applications had been filed by mid-April 2026, against an expectation of about
150 projects a year.

**Small builders did nearly all of it.** Around 85% of rebuilds came from firms
with fewer than ten projects in three years, and about 77% from established
builders. Nobody used the eight-unit secured-rental option at all. Many projects
build fewer units than they are allowed.

**Land values did not move,** which is the most surprising result here. Neither
the density bonus charge nor the added capacity appears priced into land. That
is unusual: Auckland, Kelowna and Minneapolis show building *with* land lift,
and Coquitlam shows neither building nor lift. A null result is not proof of
zero, and it deserves the caveat more than any other finding on this page.

**Multiplexes went disproportionately to cheaper land,** even comparing lots of
the same size in the same part of the city.

**New multiplex units sold around $1.4M,** roughly half the price of a new
house at about $3.1M, on a small sample.

The Kitsilano test points the same way but faintly: about 5 net homes per 1,000
lots per year, not statistically significant, with slower uptake than R1-1 and
again no land lift.

Two conditions sit underneath all of this. These are permits rather than
completed homes, and the 2023–2025 window was a high interest rate market.

## What this doesn't measure

Worth stating plainly, because the question it most resembles is one it does not
answer. There are no incomes and no rents in this study, so it says nothing
about **affordability**. It also does not measure completed homes, displacement,
who ends up living in the new units, citywide price effects, pro forma
feasibility, or anything long-run.

It measures how much new housing a specific rule change produced in 18 months,
where, and through what mechanism.

## Why it matters

Every municipality in British Columbia is now writing small-scale multi-unit
housing into its zoning, and most are betting that permission is the binding
constraint. Vancouver's reform is far enough along to check that bet against
evidence rather than projection.

The early answer is more interesting than either side of the usual argument. The
reform did produce homes, ahead of the City's own projection, and it did so
without the land value increase that upzoning critics predict. But it produced
them by changing what gets built on lots that were going to turn over anyway,
which is a quieter mechanism than "remove the barriers and supply follows", and
one with a natural limit.

Prospectus December 2026. Interviews and data reruns through 2027, with the
defence targeted for the autumn.
