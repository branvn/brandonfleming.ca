/* Elevation threshold for the contour plate.
 *
 * The background is a contour map of the Lower Mainland built from a 25 m DEM
 * (scripts/make_plate.py). Each contour band is its own <g class="b" data-e="…">
 * where data-e is the band's elevation in metres.
 *
 * Moving the pointer up the viewport raises a threshold; every band at or below
 * it lights. Read it as a water line rising across the Fraser delta — which is
 * the region's actual exposure, and the reason the flat 0–10 m ground in the
 * middle of the map is where most of the housing is.
 *
 * Cheap by construction: no per-frame redraw, no canvas, no reflow. A pointer
 * move only touches the DOM when the threshold actually crosses a band
 * boundary — at most a couple of dozen className writes, and usually zero.
 *
 * Everything works without this file. The plate renders as a plain SVG.
 */
(function () {
  "use strict";

  var host = document.querySelector(".topo");
  if (!host) return;

  var svg = host.querySelector("svg");
  if (!svg || !window.requestAnimationFrame) return;

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  // Coarse pointers (touch) get no hover state, so there's nothing to drive.
  if (window.matchMedia("(hover: none)").matches) return;

  var bands = [].slice.call(svg.querySelectorAll("g.b"));
  if (bands.length < 2) return;

  bands.forEach(function (g) {
    g.__e = parseFloat(g.getAttribute("data-e")) || 0;
  });
  bands.sort(function (a, b) { return a.__e - b.__e; });

  var maxE = bands[bands.length - 1].__e;
  var lit = -1;             // how many bands are currently lit
  var pending = false;
  var targetY = 1;

  function apply() {
    pending = false;

    // Bottom of the viewport is sea level; top is the highest contour. Eased
    // so the first few metres — where the delta actually lives — get a usable
    // share of the travel instead of being crossed instantly.
    var f = 1 - Math.min(Math.max(targetY, 0), 1);
    var threshold = Math.pow(f, 1.7) * maxE * 1.05;

    var n = 0;
    while (n < bands.length && bands[n].__e <= threshold) n++;
    if (n === lit) return;

    if (n > lit) {
      for (var i = Math.max(lit, 0); i < n; i++) bands[i].classList.add("lit");
    } else {
      for (var j = lit - 1; j >= n; j--) bands[j].classList.remove("lit");
    }
    lit = n;
  }

  window.addEventListener("pointermove", function (e) {
    targetY = e.clientY / window.innerHeight;
    if (!pending) { pending = true; requestAnimationFrame(apply); }
  }, { passive: true });

  // Drop back to nothing lit when the pointer leaves the window entirely.
  window.addEventListener("pointerleave", function () {
    targetY = 1;
    if (!pending) { pending = true; requestAnimationFrame(apply); }
  }, { passive: true });

  host.classList.add("is-live");
})();
