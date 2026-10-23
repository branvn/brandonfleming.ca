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

# Second filter axis, shown on the right. Combines with the categories above:
# picking Urban and Film shows only urban film frames. Driven by each photo's
# `medium`, which must be one of these exactly.
media = ["Film", "Digital"]

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

  # order 5 puts this first on the page, ahead of the Urban block that starts at
  # 10. The numbering is otherwise grouped by subject in hundreds: Urban 10-110,
  # Landscape 200-250, Textures 310-320.
  [captions."crescent-beach-lightning.jpg"]
    caption  = "Lightning at the Wharf"
    place    = "Crescent Beach, Surrey"
    category = "Landscape"
    medium   = "Digital"
    camera   = "Nikon D750"
    lens     = "24–85mm f/3.5–4.5"
    settings = "38mm · f/8 · 30s · ISO 100"
    order    = 5
    alt      = "A floating dock of white rowboats beside the Crescent Beach Swimming Club hut on dark water, with two forks of lightning striking the horizon beneath a heavy sky"

  [captions."science-world.jpg"]
    caption  = "Science World as seen from the Expo Line"
    place    = "False Creek"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "50mm f/1.8 AI-S"
    film     = "Ilford Pan F Plus 50"
    order    = 10
    alt      = "The geodesic dome of Science World against a grey sky, a thin crescent moon above it"

  [captions."teardown.jpg"]
    caption  = "Excavator waiting on a boarded-up bungalow"
    place    = "Surrey"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "28mm f/2.8 AI"
    film     = "Fujifilm 400"
    order    = 20
    alt      = "An orange excavator parked beside a boarded-up character house with a detached bucket on the lawn"

  [captions."balconies-at-night.jpg"]
    caption  = "Two new towers, uptown between Martin and Foster"
    place    = "White Rock"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "28mm f/2.8 AI"
    film     = "Fujifilm 400"
    order    = 30
    alt      = "Looking up at night between two recently built residential towers with curved stacked balconies, their undersides lit orange against a black sky"

  [captions."skytrain-escalator.jpg"]
    caption  = "Down to the platform"
    place    = "SkyTrain"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "50mm f/1.8 AI-S"
    film     = "Ilford Pan F Plus 50"
    order    = 40
    alt      = "Passengers descending a long escalator through a tiled vaulted tunnel lit by a single strip light"

  [captions."gateway-station.jpg"]
    caption  = "Waterfront-bound, pulling in"
    place    = "Gateway Station, Surrey"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "50mm f/1.8 AI-S"
    film     = "Ilford Pan F Plus 50"
    order    = 50
    alt      = "A SkyTrain arriving at an elevated platform, motion-blurred, destination sign reading Waterfront"

  [captions."seymour-street.jpg"]
    caption  = "Glass towers and the 44 UBC Express"
    place    = "Seymour & Pender"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "28mm f/2.8 AI"
    film     = "Fujifilm 400"
    order    = 60
    alt      = "Downtown Vancouver glass office towers seen past a trolley bus at an intersection, an orange car in the foreground"

  [captions."st-regis.jpg"]
    caption  = "Neon holding on"
    place    = "Dunsmuir & Seymour"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "50mm f/1.8 AI-S"
    film     = "Ilford Pan F Plus 50"
    order    = 70
    alt      = "The vertical neon sign of the St Regis Hotel photographed from below against a bright sky"

  [captions."arbutus-coffee.jpg"]
    caption  = "Corner store that survived the block"
    place    = "Arbutus Ridge"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "28mm f/2.8 AI"
    film     = "Fujifilm 400"
    order    = 80
    alt      = "A green-shingled heritage corner building housing Arbutus Coffee, with a striped awning and a garden out front"

  [captions."bnsf-crossing.jpg"]
    caption  = "Southbound freight at the Cypress Street crossing"
    place    = "White Rock"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "50mm f/1.8 AI-S"
    film     = "Ilford Pan F Plus 50"
    order    = 90
    alt      = "A BNSF locomotive approaching a level crossing beside the sea, tide out, pier in the distance"

  [captions."badminton-court.jpg"]
    caption  = "Court one, mid-rally"
    place    = "Surrey"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "50mm f/1.8 AI-S"
    film     = "Ilford Pan F Plus 50"
    order    = 100
    alt      = "An empty sports hall with a single blurred figure mid-stride on a badminton court"

  [captions."white-rock-poles.jpg"]
    caption  = "Coast Salish house post and Haida pole, above the pier"
    place    = "White Rock"
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "50mm f/1.8 AI-S"
    film     = "Ilford Pan F Plus 50"
    order    = 110
    alt      = "Two tall carved poles standing either side of a pair of stone interpretive plaques, with the sea and a long pier behind them"

  # --- Added 23 October 2026. Captions and places below are mine, not yours;
  #     see the TODO comments. Lens is missing from the EXIF on every one of
  #     these, so none of them name a lens yet.
  [captions."granville-towers.jpg"]
    caption  = "Three eras on one block"
    place    = "Granville Street, Vancouver"   # TODO confirm
    category = "Urban"
    medium   = "Digital"
    camera   = "Nikon D750"
    settings = "28mm · f/8 · 1/250 · ISO 1100"
    order    = 120
    alt      = "Three downtown Vancouver towers seen from the pavement looking up: a dark 1970s office slab, a glass tower, and an older stone building topped with a clock tower"

  [captions."concrete-facade.jpg"]
    caption  = "Angled canopy, late light"
    # TODO place. Shot on film; the frame was scanned 19 October 2026.
    category = "Urban"
    medium   = "Film"
    camera   = "Nikon FE"
    # TODO film stock and lens. NOTE: this file carries D750 EXIF reading
    # 28mm f/2.8 1/30 ISO 100. That is the copy-stand rig you scanned the
    # negative with, not how the photograph was taken, so it is deliberately
    # not recorded as `settings`.
    order    = 130
    alt      = "A concrete modernist building in black and white, an angular canopy jutting out from its upper storey beside a row of tall cedars"

  [captions."boundary-bay.jpg"]
    caption  = "Catamaran coming in on the tide"
    place    = "Boundary Bay"
    category = "Landscape"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "50mm f/1.8 AI-S"
    film     = "Ilford Pan F Plus 50"
    order    = 200
    alt      = "A small catamaran under sail close to shore, with people standing on the rocks watching"

  [captions."salmon-fence.jpg"]
    caption  = "Painted salmon on the estuary fence"
    place    = "Blackie Spit"
    category = "Landscape"
    medium   = "Film"
    camera   = "Nikon FE"
    lens     = "28mm f/2.8 AI"
    film     = "Fujifilm 400"
    order    = 210
    alt      = "Wooden salmon cut-outs painted by schoolchildren wired to a fence above still water at golden hour"

  [captions."crescent-beach-mooring.jpg"]
    caption  = "Moored off the swimming club, last light"
    place    = "Crescent Beach, Surrey"
    category = "Landscape"
    medium   = "Digital"
    camera   = "Nikon D750"
    lens     = "24–85mm f/3.5–4.5"
    settings = "85mm · f/4.5 · 1/1250 · ISO 6400"
    order    = 220
    alt      = "A yellow sailboat moored on flat water at dusk, with a beach, trees and the low sheds of a sailing club behind it"

  [captions."white-rock-sea-tours.jpg"]
    caption  = "Metrotown on the horizon, twenty kilometres off"
    place    = "Boundary Bay"
    category = "Landscape"
    medium   = "Digital"
    camera   = "Nikon D750"
    lens     = "24–85mm f/3.5–4.5"
    settings = "85mm · f/4.5 · 1/1250 · ISO 6400"
    order    = 230
    alt      = "A small red tour boat crossing calm water at dusk, with a wooded spit in front of the distant tower cluster of Metrotown, hazy on the horizon"

  # TODO (Brandon): the four below are from the August camping trip. I wrote
  # the captions from what I can see; set `place` and rewrite them in your own
  # words.
  [captions."lake-camp.jpg"]
    caption  = "Driftwood leaned into a shelter, tent at the edge of the frame"
    place    = ""
    category = "Landscape"
    medium   = "Digital"
    camera   = "Nikon D750"
    lens     = "24–85mm f/3.5–4.5"
    settings = "28mm · f/4 · 1/2000 · ISO 100"
    order    = 240
    alt      = "A lake ringed by forested hills, with bleached driftwood leaned together into a shelter on a gravel shore and the corner of a tent at the right"

  [captions."milky-way.jpg"]
    caption  = "New Moon"
    place    = ""
    category = "Landscape"
    medium   = "Digital"
    camera   = "Nikon D750"
    lens     = "24–85mm f/3.5–4.5"
    settings = "24mm · f/3.5 · 13s · ISO 4000"
    order    = 250
    alt      = "The band of the Milky Way across a dense starfield, with a faint meteor trail crossing the upper right"

  [captions."mount-baker.jpg"]
    caption  = "Baker, pulled in close"
    # TODO place. This is where you stood, not what you pointed at: the
    # mountain is in the caption, the vantage point belongs here.
    category = "Landscape"
    medium   = "Digital"
    camera   = "Nikon D750"
    settings = "300mm · f/10 · 1/800 · ISO 100"
    order    = 260
    alt      = "The snow-covered summit and glaciers of Mount Baker against a deep blue sky, crevasses raking across the ice field below the peak"

  [captions."rescue-boats.jpg"]
    caption  = "End of shift"
    # TODO place
    category = "Landscape"
    medium   = "Digital"
    camera   = "Nikon D750"
    settings = "200mm · f/8 · 1/500 · ISO 1800"
    order    = 270
    alt      = "A man checking his phone on a gravel spit at sunset beside two beached rescue boats, with a pink sky and a long mountain ridge behind"

  [captions."dusk-breakwater.jpg"]
    caption  = "Ten seconds, after the sun had gone"
    # TODO place
    category = "Landscape"
    medium   = "Digital"
    camera   = "Nikon D750"
    settings = "28mm · f/8 · 10s · ISO 100"
    order    = 280
    alt      = "A long exposure at dusk: a low wooden breakwater on a dark beach, water smoothed to silver, and a band of orange on the horizon under deep blue sky"

  [captions."lighthouse.jpg"]
    caption  = "Still working"
    # TODO place, and which light this is. I could not identify it reliably.
    category = "Landscape"
    medium   = "Digital"
    camera   = "Nikon D750"
    settings = "160mm · f/8 · 1/400 · ISO 100"
    order    = 290
    alt      = "A white concrete lighthouse with a red lantern room and gallery rail, the sea and distant mountains behind it and shrubs crowding the foreground"

  [captions."valley-fog.jpg"]
    caption  = "Fog sitting on the treeline"
    # TODO place
    category = "Landscape"
    medium   = "Digital"
    camera   = "Nikon D750"
    settings = "155mm · f/8 · 1/125 · ISO 1250"
    order    = 300
    alt      = "A low band of fog lying along a forested ridge, mountains fading into haze behind it and flat water in the foreground"

  [captions."foggy-beach.jpg"]
    caption  = "Driftwood, and not much else visible"
    # TODO place
    category = "Landscape"
    medium   = "Film"
    camera   = "Nikon FE"
    film     = "Kentmere Pan 400"   # read off the rebate in the scan
    # TODO lens. No exposure data survived the scan, so there is no `settings`.
    order    = 310
    alt      = "Driftwood logs piled along a beach in heavy fog, a forested point receding into the haze beyond them"

  [captions."curtain-wall.jpg"]
    caption  = "Curtain wall"
    # TODO place
    category = "Textures"
    medium   = "Digital"
    camera   = "Nikon D750"
    settings = "120mm · f/8 · 1/2500 · ISO 2200"
    order    = 430
    alt      = "A blue glass curtain wall filling the frame, its grid of mullions running on the diagonal, ceiling lights showing faintly through the glazing"

  [captions."balanced-stones.jpg"]
    caption  = "Closer, with the water gone soft behind"
    place    = ""
    category = "Textures"
    medium   = "Digital"
    camera   = "Nikon D750"
    lens     = "24–85mm f/3.5–4.5"
    settings = "85mm · f/6.3 · 1/500 · ISO 1000"
    order    = 410
    alt      = "Close view of two wet balanced stones on the growth rings of a cut stump, the lake behind them thrown far out of focus"

  [captions."driftwood.jpg"]
    caption  = "Everything the lake put back on the shore"
    place    = ""
    category = "Textures"
    medium   = "Digital"
    camera   = "Nikon D750"
    lens     = "24–85mm f/3.5–4.5"
    settings = "48mm · f/6.3 · 1/640 · ISO 1000"
    order    = 420
    alt      = "A dense tangle of bleached and blackened driftwood filling the frame, one pale reed standing upright through it"
+++

Mostly the Lower Mainland. Transit, infrastructure, buildings that are about to
change, and whatever the tide leaves behind.
