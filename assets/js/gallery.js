/* Photography page: category filtering and a lightbox.
 *
 * Both are progressive. With this file absent or broken you get every
 * photograph in one flow, and clicking one opens the full-size file, which is
 * exactly what the page did before any of this existed. The filter chips are
 * marked hidden in the template and only revealed here, so they can never sit
 * there looking clickable while doing nothing.
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

  if (bar) {
    bar.hidden = false;

    bar.addEventListener("click", function (e) {
      var btn = e.target.closest(".chip");
      if (!btn) return;

      var want = btn.getAttribute("data-filter");
      var shown = 0;

      bar.querySelectorAll(".chip").forEach(function (c) {
        var on = c === btn;
        c.classList.toggle("is-on", on);
        c.setAttribute("aria-pressed", on ? "true" : "false");
      });

      shots.forEach(function (fig) {
        var show = want === "all" || fig.getAttribute("data-category") === want;
        fig.hidden = !show;
        if (show) shown++;
      });

      if (empty) empty.hidden = shown > 0;
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
    '<p class="lb-caption"></p>';
  document.body.appendChild(dlg);

  var img = dlg.querySelector("img");
  var cap = dlg.querySelector(".lb-caption");
  var at = 0;

  // Only the photos currently on screen, so the arrows follow the active
  // filter instead of wandering into hidden ones.
  function visible() {
    return shots.filter(function (f) { return !f.hidden; });
  }

  function show(list, i) {
    at = (i + list.length) % list.length;
    var link = list[at].querySelector("a");
    var thumb = list[at].querySelector("img");

    img.src = link.getAttribute("data-full");
    img.alt = thumb ? thumb.alt : "";

    var c = link.getAttribute("data-caption") || "";
    var p = link.getAttribute("data-place") || "";
    cap.textContent = c && p ? c + " · " + p : c || p;

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
