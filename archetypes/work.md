+++
title = "{{ replace .File.ContentBaseName "-" " " | title }}"
date = {{ .Date }}
draft = true
weight = 50

# One sentence, plain language. Shown on cards and in search results.
summary = ""

year    = ""
context = ""          # e.g. "Agricultural Land Commission internship"
role    = ""          # e.g. "Sole analyst"
tools   = []          # e.g. ["ArcGIS Pro", "Excel"]
status  = ""          # "in-progress" to show the WIP tag, otherwise leave blank

# thumb = "/images/example-thumb.jpg"
# hero  = "/images/example.jpg"
# heroAlt = ""
# heroCaption = ""

# sources = [
#   "[Dataset name](https://example.gov.bc.ca)",
# ]

# ⚠ Keep [download] LAST. In TOML a table header swallows every bare key that
# follows it, so anything you add below this line becomes download.whatever and
# the templates won't see it.
# [download]
#   url   = "/documents/example.pdf"
#   label = "Download the full paper (PDF)"
#   note  = "34 pages"
+++
