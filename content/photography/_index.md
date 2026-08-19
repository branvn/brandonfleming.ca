+++
title = "Photography"
summary = "Photographs of the Lower Mainland and beyond: the built environment, the coast, and things found on the ground."

# Old URLs from when this was split into Film and Digital. Hugo emits redirect
# pages at these paths so any link already out in the world still works.
aliases = ["/photography/film/", "/photography/digital/"]

# The filter chips across the top, in this order. "All" is added automatically
# and is the default. Add a category here and it appears; every category needs
# at least one photo or you get an empty tab, which is dead space.
categories = ["Urban", "Landscape", "Textures"]

# Captions are keyed by filename. Every photo needs a block, or it renders with
# no caption and no alt text.
#
#   category  must match one of the names above, exactly
#   medium    shown under the caption. Film and digital look different and the
#             difference is worth naming, it just isn't worth navigating by
#   order     controls position on the page, lowest first. Ties fall back to
#             filename. Renumber freely, gaps are fine
#   alt       what a screen reader announces. Describe the photograph
[captions]

  [captions."science-world.jpg"]
    caption  = "Science World as seen from the Expo Line"
    place    = "False Creek"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 10
    alt      = "The geodesic dome of Science World against a grey sky, a thin crescent moon above it"

  [captions."teardown.jpg"]
    caption  = "Excavator waiting on a boarded-up bungalow"
    place    = "Surrey"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 20
    alt      = "An orange excavator parked beside a boarded-up character house with a detached bucket on the lawn"

  [captions."balconies-at-night.jpg"]
    caption  = "Two new towers, uptown between Martin and Foster"
    place    = "White Rock"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 30
    alt      = "Looking up at night between two recently built residential towers with curved stacked balconies, their undersides lit orange against a black sky"

  [captions."skytrain-escalator.jpg"]
    caption  = "Down to the platform"
    place    = "SkyTrain"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 40
    alt      = "Passengers descending a long escalator through a tiled vaulted tunnel lit by a single strip light"

  [captions."gateway-station.jpg"]
    caption  = "Waterfront-bound, pulling in"
    place    = "Gateway Station, Surrey"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 50
    alt      = "A SkyTrain arriving at an elevated platform, motion-blurred, destination sign reading Waterfront"

  [captions."seymour-street.jpg"]
    caption  = "Glass towers and the 44 UBC Express"
    place    = "Seymour & Pender"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 60
    alt      = "Downtown Vancouver glass office towers seen past a trolley bus at an intersection, an orange car in the foreground"

  [captions."st-regis.jpg"]
    caption  = "Neon holding on"
    place    = "Dunsmuir & Seymour"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 70
    alt      = "The vertical neon sign of the St Regis Hotel photographed from below against a bright sky"

  [captions."arbutus-coffee.jpg"]
    caption  = "Corner store that survived the block"
    place    = "Arbutus Ridge"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 80
    alt      = "A green-shingled heritage corner building housing Arbutus Coffee, with a striped awning and a garden out front"

  [captions."bnsf-crossing.jpg"]
    caption  = "Southbound freight at the Cypress Street crossing"
    place    = "White Rock"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 90
    alt      = "A BNSF locomotive approaching a level crossing beside the sea, tide out, pier in the distance"

  [captions."badminton-court.jpg"]
    caption  = "Court one, mid-rally"
    place    = "Surrey"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 100
    alt      = "An empty sports hall with a single blurred figure mid-stride on a badminton court"

  [captions."white-rock-poles.jpg"]
    caption  = "Coast Salish house post and Haida pole, above the pier"
    place    = "White Rock"
    category = "Urban"
    medium   = "35mm, Nikon FE"
    order    = 110
    alt      = "Two tall carved poles standing either side of a pair of stone interpretive plaques, with the sea and a long pier behind them"

  [captions."boundary-bay.jpg"]
    caption  = "Catamaran coming in on the tide"
    place    = "Boundary Bay"
    category = "Landscape"
    medium   = "35mm, Nikon FE"
    order    = 200
    alt      = "A small catamaran under sail close to shore, with people standing on the rocks watching"

  [captions."salmon-fence.jpg"]
    caption  = "Painted salmon on the estuary fence"
    place    = "Blackie Spit"
    category = "Landscape"
    medium   = "35mm, Nikon FE"
    order    = 210
    alt      = "Wooden salmon cut-outs painted by schoolchildren wired to a fence above still water at golden hour"

  [captions."crescent-beach-mooring.jpg"]
    caption  = "Moored off the swimming club, last light"
    place    = "Crescent Beach, Surrey"
    category = "Landscape"
    medium   = "Nikon D750"
    order    = 220
    alt      = "A yellow sailboat moored on flat water at dusk, with a beach, trees and the low sheds of a sailing club behind it"

  [captions."white-rock-sea-tours.jpg"]
    caption  = "Metrotown on the horizon, twenty kilometres off"
    place    = "Boundary Bay"
    category = "Landscape"
    medium   = "Nikon D750"
    order    = 230
    alt      = "A small red tour boat crossing calm water at dusk, with a wooded spit in front of the distant tower cluster of Metrotown, hazy on the horizon"

  # TODO (Brandon): the four below are from the August camping trip. I wrote
  # the captions from what I can see; set `place` and rewrite them in your own
  # words. There was a fifth, the Milky Way frame, which never made it into the
  # folder.
  [captions."lake-camp.jpg"]
    caption  = "Driftwood leaned into a shelter, tent at the edge of the frame"
    place    = ""
    category = "Landscape"
    medium   = "Nikon D750"
    order    = 240
    alt      = "A lake ringed by forested hills, with bleached driftwood leaned together into a shelter on a gravel shore and the corner of a tent at the right"

  [captions."milky-way.jpg"]
    caption  = "Thirteen seconds, no moon"
    place    = ""
    category = "Landscape"
    medium   = "Nikon D750"
    order    = 250
    alt      = "The band of the Milky Way across a dense starfield, with a faint meteor trail crossing the upper right"

  [captions."stones-on-a-stump.jpg"]
    caption  = "Two stones balanced on a cut stump"
    place    = ""
    category = "Textures"
    medium   = "Nikon D750"
    order    = 300
    alt      = "Two smooth stones balanced one on the other atop a weathered cut stump, with mist lifting off a lake and forested slopes behind"

  [captions."balanced-stones.jpg"]
    caption  = "Closer, with the water gone soft behind"
    place    = ""
    category = "Textures"
    medium   = "Nikon D750"
    order    = 310
    alt      = "Close view of two wet balanced stones on the growth rings of a cut stump, the lake behind them thrown far out of focus"

  [captions."driftwood.jpg"]
    caption  = "Everything the lake put back on the shore"
    place    = ""
    category = "Textures"
    medium   = "Nikon D750"
    order    = 320
    alt      = "A dense tangle of bleached and blackened driftwood filling the frame, one pale reed standing upright through it"
+++

Mostly the Lower Mainland. Transit, infrastructure, buildings that are about to
change, and whatever the tide leaves behind.
