/* Elevation threshold for the contour plate.
 *
 * The background is a contour map of the Lower Mainland built from vector
 * layers (scripts/make_plate.py). Each contour band is its own
 * <g class="b" data-e="…"> where data-e is the band's elevation in metres.
 *
 * A threshold rises; every band at or below it lights. Read it as a water line
 * rising across the Fraser delta — which is the region's actual exposure, and
 * the reason the flat 0–35 m ground in the middle of the map is where most of
 * the housing is.
 *
 * Two ways to drive that threshold, because the two kinds of device have
 * nothing in common:
 *
 *   fine pointer   cursor height in the viewport. Bottom is sea level, top is
 *                  the highest contour. Direct and reversible.
 *   coarse pointer no cursor exists, so scroll position drives it instead: the
 *                  water rises as you read down the page and recedes as you go
 *                  back up. Same metaphor, same code path, different input.
 *
 * Cheap by construction: no per-frame redraw, no canvas, no reflow. An input
 * event only touches the DOM when the threshold actually crosses a band
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

  var bands = [].slice.call(svg.querySelectorAll("g.b"));
  if (bands.length < 2) return;

  bands.forEach(function (g) {
    g.__e = parseFloat(g.getAttribute("data-e")) || 0;
  });
  bands.sort(function (a, b) { return a.__e - b.__e; });

  var maxE = bands[bands.length - 1].__e;
  var lit = -1;             // how many bands are currently lit
  var pending = false;
  var level = 0;            // 0 = sea level, 1 = every band lit

  function apply() {
    pending = false;

    // Eased so the first few metres — where the delta actually lives — get a
    // usable share of the travel instead of being crossed instantly.
    //
    // The exponent is tied to the contour levels. At 1.7 and a 1150 m top band,
    // every band below 80 m lit inside the bottom fifth of the travel, which is
    // 57% of the ink on the plate gone in one flick. 2.6 gives the delta about a
    // third of the sweep. Raise it if the level list ever gains a 2 m or 5 m
    // line; lower it if the top of the range moves down.
    var threshold = Math.pow(level, 2.6) * maxE * 1.05;

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

  function set(v) {
    level = v < 0 ? 0 : (v > 1 ? 1 : v);
    if (!pending) { pending = true; requestAnimationFrame(apply); }
  }

  // A coarse pointer means touch: there is no hover state to read, so the
  // cursor path would simply never fire and the plate would sit inert.
  if (window.matchMedia("(hover: none)").matches) {

    var scrolled = function () {
      var doc = document.documentElement;
      // Total scrollable distance. Guard the divide: a short page — the 404, or
      // any page that fits the screen — has none, and would otherwise light
      // every band at once on first paint.
      var span = doc.scrollHeight - window.innerHeight;
      return span > 0 ? window.pageYOffset / span : 0;
    };

    var onScroll = function () { set(scrolled()); };

    window.addEventListener("scroll", onScroll, { passive: true });
    // scrollHeight moves when the address bar hides or the device rotates.
    window.addEventListener("resize", onScroll, { passive: true });
    window.addEventListener("orientationchange", onScroll, { passive: true });

    onScroll();   // honour the position we were restored to, not just the top

  } else {

    window.addEventListener("pointermove", function (e) {
      set(1 - e.clientY / window.innerHeight);
    }, { passive: true });

    // Drop back to nothing lit when the pointer leaves the window entirely.
    window.addEventListener("pointerleave", function () { set(0); }, { passive: true });
  }

  host.classList.add("is-live");
})();
