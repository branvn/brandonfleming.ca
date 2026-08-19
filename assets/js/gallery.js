/* Photography page: two-axis filtering and a lightbox.
 *
 * Both are progressive. With this file absent or broken you get every
 * photograph in one flow, and clicking one opens the full-size file, which is
 * exactly what the page did before any of this existed. The chips are marked
 * hidden in the template and only revealed here, so they can never sit there
 * looking clickable while doing nothing.
 *
 * No dependencies. The lightbox is a native <dialog>, which brings focus
 * trapping, Escape-to-close and the top layer for free.
 */
(function () {
  "use strict";

  var gallery = document.querySelector(".gallery");
  if (!gallery) return;

  var shots = [].slice.call(gallery.querySelectorAll(".shot"));
  if (!shots.length) return;

  /* ---------------------------------------------------------------- filters */

  var bar = document.querySelector(".filters");
  var empty = document.querySelector(".gallery-empty");

  // One entry per axis, so subject and medium are independent and combine.
  // "all" means no constraint on that axis.
  var picked = { category: "all", medium: "all" };

  function applyFilters() {
    var shown = 0;
    shots.forEach(function (fig) {
      var ok = true;
      for (var axis in picked) {
        var want = picked[axis];
        if (want !== "all" && fig.getAttribute("data-" + axis) !== want) ok = false;
      }
      fig.hidden = !ok;
      if (ok) shown++;
    });
    if (empty) empty.hidden = shown > 0;
  }

  if (bar) {
    bar.hidden = false;

    bar.addEventListener("click", function (e) {
      var btn = e.target.closest(".chip");
      if (!btn) return;

      var group = btn.closest(".filter-group");
      var axis = group.getAttribute("data-axis");
      var value = btn.getAttribute("data-value");

      // Clicking the active chip clears that axis rather than doing nothing,
      // which saves hunting for an "All" button on the medium group.
      var next = picked[axis] === value ? "all" : value;
      picked[axis] = next;

      group.querySelectorAll(".chip").forEach(function (c) {
        var on = c.getAttribute("data-value") === next;
        c.classList.toggle("is-on", on);
        c.setAttribute("aria-pressed", on ? "true" : "false");
      });

      applyFilters();
    });
  }

  /* --------------------------------------------------------------- lightbox */

  // Skip on coarse pointers: on a phone the photo already fills the width, so
  // an overlay adds a tap and takes one away.
  if (window.matchMedia("(hover: none)").matches) return;
  if (!window.HTMLDialogElement) return;

  var dlg = document.createElement("dialog");
  dlg.className = "lightbox";
  dlg.innerHTML =
    '<button class="lb-close" type="button" aria-label="Close">×</button>' +
    '<button class="lb-nav lb-prev" type="button" aria-label="Previous photograph">‹</button>' +
    '<img alt="">' +
    '<button class="lb-nav lb-next" type="button" aria-label="Next photograph">›</button>' +
    '<p class="lb-caption"><span class="lb-text"></span><span class="lb-spec"></span></p>';
  document.body.appendChild(dlg);

  var img = dlg.querySelector("img");
  var text = dlg.querySelector(".lb-text");
  var spec = dlg.querySelector(".lb-spec");
  var at = 0;

  // Only the photos currently on screen, so the arrows follow the active
  // filters instead of wandering into hidden ones.
  function visible() {
    return shots.filter(function (f) { return !f.hidden; });
  }

  function show(list, i) {
    if (!list.length) return;
    at = (i + list.length) % list.length;
    var link = list[at].querySelector("a");
    var thumb = list[at].querySelector("img");

    img.src = link.getAttribute("data-full");
    img.alt = thumb ? thumb.alt : "";

    var c = link.getAttribute("data-caption") || "";
    var p = link.getAttribute("data-place") || "";
    text.textContent = c && p ? c + " · " + p : c || p;
    spec.textContent = link.getAttribute("data-spec") || "";

    var many = list.length > 1;
    dlg.querySelector(".lb-prev").hidden = !many;
    dlg.querySelector(".lb-next").hidden = !many;
  }

  gallery.addEventListener("click", function (e) {
    var link = e.target.closest(".shot a");
    if (!link) return;
    e.preventDefault();
    var list = visible();
    show(list, list.indexOf(e.target.closest(".shot")));
    dlg.showModal();
  });

  dlg.addEventListener("click", function (e) {
    if (e.target.closest(".lb-close")) return dlg.close();
    if (e.target.closest(".lb-prev")) return show(visible(), at - 1);
    if (e.target.closest(".lb-next")) return show(visible(), at + 1);
    // A click on the backdrop lands on the dialog itself, never on its children.
    if (e.target === dlg) dlg.close();
  });

  document.addEventListener("keydown", function (e) {
    if (!dlg.open) return;
    if (e.key === "ArrowLeft") show(visible(), at - 1);
    if (e.key === "ArrowRight") show(visible(), at + 1);
  });

  // Drop the source on close so a large image isn't held in memory.
  dlg.addEventListener("close", function () { img.removeAttribute("src"); });
})();
