/* Small-scale multi-unit pro forma, run in the browser.
 *
 * A residual rental model: fix the costs, decide what return the developer
 * needs, and solve backwards for the rent that produces it. Then compare that
 * rent against what a household on a given income can afford at the CMHC
 * threshold of 30% of gross income.
 *
 * The point of the tool is the gap between those two numbers, and how it moves.
 * Add units and it narrows. Cut the land price and it narrows further. Strip
 * the profit margin and waive the fees, and on plausible Surrey inputs it still
 * does not close.
 *
 * DEFAULTS ARE ILLUSTRATIVE. They are plausible starting points, not modelled
 * findings, and they are marked as such on the page. Replace them in FIELDS
 * below once the real figures are settled.
 *
 * No dependencies. Renders itself into #proforma, so with JavaScript off the
 * page shows the explanation and a note instead of a broken form.
 */
(function () {
  "use strict";

  var host = document.getElementById("proforma");
  if (!host) return;

  // value is the default; min/max bound the slider; step is the increment.
  // fmt controls how the readout is written.
  var FIELDS = [
    { group: "The site" },
    { id: "land",   label: "Land, per lot",        value: 1300000, min: 400000, max: 2500000, step: 25000,  fmt: "money" },
    { id: "units",  label: "Units built",          value: 6,       min: 2,      max: 8,       step: 1,      fmt: "plain" },
    { id: "sqft",   label: "Floor area per unit",  value: 800,     min: 400,    max: 1400,    step: 25,     fmt: "sqft"  },

    { group: "Cost to build" },
    { id: "hard",   label: "Construction",         value: 340,     min: 200,    max: 500,     step: 5,      fmt: "psf"   },
    { id: "soft",   label: "Soft costs",           value: 18,      min: 5,      max: 35,      step: 1,      fmt: "pct",   note: "design, permits, consultants, marketing, as a share of construction" },
    { id: "fees",   label: "Municipal fees",       value: 30000,   min: 0,      max: 80000,   step: 1000,   fmt: "money", note: "development and amenity charges per unit. Non-market housing is eligible for waivers" },

    { group: "Money" },
    { id: "rate",   label: "Construction financing", value: 6.5,   min: 2,      max: 10,      step: 0.1,    fmt: "pctd"  },
    { id: "months", label: "Build period",         value: 16,      min: 8,      max: 30,      step: 1,      fmt: "months" },
    { id: "margin", label: "Developer margin",     value: 15,      min: 0,      max: 25,      step: 1,      fmt: "pct",   note: "set this to zero for a non-profit builder" },
    { id: "cap",    label: "Capitalisation rate",  value: 4.25,    min: 3,      max: 6,       step: 0.05,   fmt: "pctd",  note: "what the finished building is worth per dollar of income. Lower means more valuable" },

    { group: "Running it" },
    { id: "opex",   label: "Operating costs",      value: 28,      min: 15,     max: 45,      step: 1,      fmt: "pct",   note: "share of rent collected that goes on taxes, insurance, maintenance" },
    { id: "vac",    label: "Vacancy",              value: 3,       min: 0,      max: 10,      step: 0.5,    fmt: "pct"   },

    { group: "Who it is for" },
    { id: "income", label: "Household income",     value: 75000,   min: 30000,  max: 150000,  step: 1000,   fmt: "money", note: "affordable rent is 30% of gross income, the CMHC threshold" }
  ];

  var money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", maximumFractionDigits: 0 });

  function readout(f, v) {
    switch (f.fmt) {
      case "money":  return money.format(v);
      case "psf":    return money.format(v) + " per sq ft";
      case "sqft":   return v.toLocaleString("en-CA") + " sq ft";
      case "pct":    return v + "%";
      case "pctd":   return v.toFixed(2).replace(/\.?0+$/, "") + "%";
      case "months": return v + " months";
      default:       return String(v);
    }
  }

  /* ------------------------------------------------------------------ build */

  var html = '<form class="pf" novalidate>';
  FIELDS.forEach(function (f) {
    if (f.group) {
      html += '<h3 class="pf-group">' + f.group + "</h3>";
      return;
    }
    html +=
      '<div class="pf-row">' +
        '<label for="pf-' + f.id + '">' + f.label +
          (f.note ? '<span class="pf-note">' + f.note + "</span>" : "") +
        "</label>" +
        '<output id="out-' + f.id + '" for="pf-' + f.id + '"></output>' +
        '<input type="range" id="pf-' + f.id + '" min="' + f.min + '" max="' + f.max +
          '" step="' + f.step + '" value="' + f.value + '">' +
      "</div>";
  });
  html += "</form>" +
    '<div class="pf-out" role="status" aria-live="polite">' +
      '<div class="pf-fig"><span class="pf-lab">Rent needed to make it viable</span>' +
        '<span class="pf-num" id="pf-rent"></span><span class="pf-unit">per unit, per month</span></div>' +
      '<div class="pf-fig"><span class="pf-lab">What that household can afford</span>' +
        '<span class="pf-num" id="pf-afford"></span><span class="pf-unit">at 30% of gross income</span></div>' +
      '<div class="pf-fig pf-gap"><span class="pf-lab">The gap</span>' +
        '<span class="pf-num" id="pf-gap"></span><span class="pf-unit" id="pf-gap-note"></span></div>' +
    "</div>" +
    '<p class="pf-total">Total development cost <strong id="pf-tdc"></strong>, ' +
      'or <strong id="pf-perunit"></strong> per unit.</p>';

  host.innerHTML = html;

  var el = {};
  FIELDS.forEach(function (f) {
    if (f.id) el[f.id] = document.getElementById("pf-" + f.id);
  });

  /* ------------------------------------------------------------------ model */

  function calculate() {
    var v = {};
    FIELDS.forEach(function (f) {
      if (f.id) v[f.id] = parseFloat(el[f.id].value);
    });

    var hard   = v.units * v.sqft * v.hard;
    var soft   = hard * (v.soft / 100);
    var fees   = v.units * v.fees;
    var subtot = v.land + hard + soft + fees;

    // Interest accrues on a balance that grows through the build, so the
    // average outstanding is far below the total. 60% is the usual rule of
    // thumb and avoids pretending to a precision this tool does not have.
    var finance = subtot * 0.60 * (v.rate / 100) * (v.months / 12);
    var tdc = subtot + finance;

    // Work backwards. The building has to be worth its cost plus the margin;
    // its worth is its income divided by the cap rate; income is rent less
    // vacancy and operating costs.
    var valueNeeded = tdc * (1 + v.margin / 100);
    var noiNeeded   = valueNeeded * (v.cap / 100);
    var egi         = noiNeeded / (1 - v.opex / 100);
    var gross       = egi / (1 - v.vac / 100);
    var rent        = gross / v.units / 12;

    var afford = v.income * 0.30 / 12;
    var gap    = rent - afford;

    document.getElementById("pf-rent").textContent    = money.format(rent);
    document.getElementById("pf-afford").textContent  = money.format(afford);
    document.getElementById("pf-gap").textContent     = money.format(Math.abs(gap));
    document.getElementById("pf-gap-note").textContent =
      gap > 0 ? "a month short of viable" : "a month of headroom";
    document.getElementById("pf-tdc").textContent     = money.format(tdc);
    document.getElementById("pf-perunit").textContent = money.format(tdc / v.units);

    host.querySelector(".pf-gap").classList.toggle("is-short", gap > 0);

    FIELDS.forEach(function (f) {
      if (f.id) document.getElementById("out-" + f.id).textContent = readout(f, v[f.id]);
    });
  }

  host.addEventListener("input", calculate);
  calculate();
})();
