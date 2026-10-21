/* Riverside Hospital Manager — plain JavaScript (no libraries) */
(function () {
  "use strict";

  /* ---------- Mobile navigation ---------- */
  var navToggle = document.querySelector("[data-nav-toggle]");
  var nav = document.querySelector("[data-nav]");
  if (navToggle && nav) {
    navToggle.addEventListener("click", function () {
      nav.classList.toggle("is-open");
    });
  }

  /* ---------- Flash messages close on their own ---------- */
  document.querySelectorAll("[data-flash]").forEach(function (flash) {
    var close = flash.querySelector("[data-flash-close]");
    if (close) {
      close.addEventListener("click", function () { flash.remove(); });
    }
    window.setTimeout(function () {
      flash.classList.add("is-leaving");
      window.setTimeout(function () { flash.remove(); }, 450);
    }, 6000);
  });

  /* ---------- Ask before deleting ---------- */
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (event) {
      if (!window.confirm(el.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var message = form.getAttribute("data-confirm");
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  /* ---------- Live word counter for fields with a texttools word limit ----------
     The form adds data-word-limit / data-word-min from the model's validators,
     so this counter always agrees with what the server will accept. */
  document.querySelectorAll("[data-word-limit], [data-word-min]").forEach(function (el) {
    var max = parseInt(el.getAttribute("data-word-limit") || "0", 10);
    var min = parseInt(el.getAttribute("data-word-min") || "0", 10);
    if (!max && !min) return;

    var counter = document.createElement("small");
    counter.className = "word-count";
    el.insertAdjacentElement("afterend", counter);

    function update() {
      var words = el.value.trim() === "" ? 0 : el.value.trim().split(/\s+/).length;
      counter.textContent = max ? words + " / " + max + " words" : words + " words";
      counter.classList.toggle("is-over", Boolean(max) && words > max);
      counter.classList.toggle("is-under", Boolean(min) && words < min && el.value !== "");
    }

    el.addEventListener("input", update);
    update();
  });
})();
