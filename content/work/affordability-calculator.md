+++
title = "What Rent Does a Sixplex Need?"
date = 2026-08-18
weight = 50
draft = true

summary = "An interactive pro forma for small-scale multi-unit housing in Surrey. Move the inputs and watch the gap between viable rent and affordable rent open and close."

year    = "2026"
context = "Illustrative tool, built alongside the Bill 44 thesis"
role    = "Sole author"
tools   = ["Residual land value method", "CMHC affordability threshold", "Vanilla JavaScript"]

# Loads assets/js/proforma.js. Nothing else on the site uses this.
calculator = true

# DRAFT. Nothing publishes while draft = true.
#
# TODO (Brandon): the defaults in assets/js/proforma.js are plausible starting
# points I chose, NOT modelled findings. Before this goes live, replace them
# with your own figures and check the framing below still matches what you are
# willing to claim. The numbers I most need from you are listed at the bottom
# of this file in a comment.
+++

Bill 44 lets a builder put six units on a lot that used to hold one. The policy
assumes that permission is the binding constraint, and that once it is lifted
the units follow and prices ease.

A pro forma is the arithmetic that decides whether they actually do. It works
backwards: take the cost of the land, the cost of building, the cost of
borrowing, and the return the builder needs, and solve for the rent that makes
those numbers meet. If that rent is higher than what people in the neighbourhood
can pay, the building either does not get built or it gets built for someone
else.

Move the inputs below and watch what happens to the two figures at the bottom.

<div id="proforma"></div>
<noscript>
  <p><strong>This calculator needs JavaScript.</strong> The short version: on
  plausible Surrey inputs, the rent required to make a small-scale multi-unit
  building viable sits well above what a median renter household can afford, and
  adding units narrows that gap without closing it.</p>
</noscript>

## What to try

**Add units.** Going from four to six spreads the same land price across more
homes, and the required rent falls sharply. This is the part of the supply
argument that works: density genuinely does lower cost per unit.

**Then put the land price back up.** That is the mechanism the thesis is about.
Upzoning increases what a lot is worth, because it increases what can be built
on it. If the land price rises faster than the per-unit saving from density, the
rent needed goes up rather than down, and the policy produces more housing that
is less affordable.

**Set the margin to zero and waive the fees.** That is roughly a non-profit
builder with municipal charges relieved. It is the most favourable case
available, and it is worth seeing how far it gets.

## What this leaves out

Plenty, deliberately. It is one building, not a market. It assumes the units are
rented rather than sold, holds construction costs flat over the build, treats
financing as a single blended rate, and ignores the parking, servicing and
tree-replacement requirements that vary lot by lot. It says nothing about
whether the builder can actually get the land, which is often the real
constraint.

It is a teaching tool for one relationship: **land cost against viable rent.**
For that relationship it is honest, and the direction it points is not sensitive
to the exact inputs.

<!-- ---------------------------------------------------------------------
     TODO (Brandon): figures to replace the illustrative defaults, in
     assets/js/proforma.js under FIELDS. Currently guessed:

       land          $1,300,000   a Surrey SFH lot after upzoning. You have
                                  this from BC Assessment
       hard cost     $340/sq ft   2026 Altus Group BC Cost Guide
       soft costs    18%          of hard cost
       municipal     $30,000/unit Surrey 2025 DCC bylaw plus proposed ACC
       financing     6.5%         conventional. What does MLI Select give you?
       cap rate      4.25%        Metro Vancouver purpose-built rental
       opex          28%          of effective gross income
       unit size     800 sq ft
       income        $75,000      REPLACE THIS. Your thesis uses 2021 Census
                                  renter median household income at the
                                  dissemination-area level for Newton and
                                  Fleetwood. Those two numbers would let the
                                  tool carry preset buttons for each
                                  neighbourhood, which would be much stronger
                                  than one generic slider.
     --------------------------------------------------------------------- -->
