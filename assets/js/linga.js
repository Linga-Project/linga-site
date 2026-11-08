/* Linga · site public. Amélioration progressive, sans dépendance : tout reste lisible sans JavaScript.
   Chargé dans <head> (sans defer) pour poser la classe « js » avant le premier affichage. */
(function () {
  "use strict";

  var root = document.documentElement;
  root.classList.add("js");

  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  /* Lien vers une ancre de la page courante : la cible correspondante, sinon null. */
  function anchorTarget(link) {
    if (!link || !link.hash || link.pathname !== window.location.pathname) return null;
    try {
      return document.getElementById(decodeURIComponent(link.hash.slice(1)));
    } catch (error) {
      return null;
    }
  }

  /* Après un clic dans un bloc que le script referme (menu, sommaire mobile), le focus suit le lecteur jusqu'à la
     cible au lieu de retomber sur <body>. Le défilement, lui, reste celui du navigateur. */
  function focusAfterJump(target) {
    if (!target) return;
    window.requestAnimationFrame(function () {
      if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
    });
  }

  /* En-tête : un filet apparaît dès qu'on a défilé. */
  function initHeader() {
    var header = document.querySelector(".site-header");
    if (!header) return;
    var update = function () {
      header.classList.toggle("is-scrolled", window.scrollY > 8);
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
  }

  /* Menu mobile. */
  function initMenu() {
    var toggle = document.querySelector(".menu-toggle");
    var panel = toggle && document.getElementById(toggle.getAttribute("aria-controls"));
    if (!toggle || !panel) return;

    /* Menu ouvert : le reste de la page (caché sous le panneau) sort de l'ordre de tabulation. */
    var behind = document.querySelectorAll(".skip-link, main, .site-footer");

    function setOpen(open, restoreFocus) {
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      panel.hidden = !open;
      document.body.classList.toggle("menu-open", open);
      Array.prototype.forEach.call(behind, function (element) {
        element.inert = open;
      });
      if (open) {
        var first = panel.querySelector("a");
        if (first) first.focus();
      } else if (restoreFocus) {
        toggle.focus();
      }
    }

    toggle.addEventListener("click", function () {
      setOpen(toggle.getAttribute("aria-expanded") !== "true", false);
    });
    panel.addEventListener("click", function (event) {
      var link = event.target.closest("a");
      if (!link) return;
      setOpen(false, false);
      focusAfterJump(anchorTarget(link));
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") setOpen(false, true);
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth >= 1024 && toggle.getAttribute("aria-expanded") === "true") setOpen(false, false);
    });
  }

  /* « Comment ça marche » : le téléphone collant montre l'écran de l'étape qui passe au milieu de l'écran. */
  function initHow() {
    var how = document.querySelector("[data-how]");
    if (!how || !("IntersectionObserver" in window)) return;
    var steps = Array.prototype.slice.call(how.querySelectorAll("[data-step]"));
    var screens = how.querySelectorAll("[data-screen]");
    var marks = how.querySelectorAll("[data-mark]");
    if (!steps.length) return;

    function activate(index) {
      steps.forEach(function (step, i) {
        step.classList.toggle("is-active", i === index);
      });
      Array.prototype.forEach.call(screens, function (screen) {
        screen.classList.toggle("is-active", Number(screen.getAttribute("data-screen")) === index);
      });
      Array.prototype.forEach.call(marks, function (mark) {
        mark.classList.toggle("is-active", Number(mark.getAttribute("data-mark")) === index);
      });
    }

    activate(0);
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) activate(steps.indexOf(entry.target));
        });
      },
      { rootMargin: "-48% 0px -48% 0px", threshold: 0 }
    );
    steps.forEach(function (step) {
      observer.observe(step);
    });
  }

  /* Pages légales et d'aide : le sommaire suit la lecture. */
  function initToc() {
    var links = Array.prototype.slice.call(document.querySelectorAll(".toc a[href^='#']"));
    if (!links.length) return;
    var targets = links
      .map(function (link) {
        return document.getElementById(decodeURIComponent(link.getAttribute("href").slice(1)));
      })
      .filter(Boolean);
    if (!targets.length) return;

    var current = -1;
    var ticking = false;

    function update() {
      ticking = false;
      var offset = window.innerHeight * 0.25 + 60;
      var index = 0;
      for (var i = 0; i < targets.length; i++) {
        if (targets[i].getBoundingClientRect().top - offset <= 0) index = i;
        else break;
      }
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
        index = targets.length - 1;
      }
      if (index === current) return;
      current = index;
      links.forEach(function (link, i) {
        if (i === index) link.setAttribute("aria-current", "true");
        else link.removeAttribute("aria-current");
      });
      var active = links[index];
      var aside = active && active.closest(".doc__aside");
      if (aside && aside.scrollHeight > aside.clientHeight) {
        var top = active.offsetTop - aside.clientHeight / 2;
        aside.scrollTo({ top: Math.max(0, top), behavior: reduceMotion ? "auto" : "smooth" });
      }
    }

    window.addEventListener(
      "scroll",
      function () {
        if (!ticking) {
          ticking = true;
          window.requestAnimationFrame(update);
        }
      },
      { passive: true }
    );
    update();

    /* Sur mobile, le sommaire dépliable se referme une fois l'article choisi. */
    var mobile = document.querySelector(".toc-mobile");
    if (mobile) {
      mobile.addEventListener("click", function (event) {
        var link = event.target.closest("a");
        if (!link) return;
        mobile.open = false;
        focusAfterJump(anchorTarget(link));
      });
    }
  }

  /* Tableaux des pages légales : seuls ceux qui défilent encore de côté restent atteignables au clavier (build.py
     leur donne tabindex, rôle et nom), avec un fondu à droite tant que la fin n'est pas atteinte. */
  function initTables() {
    var wraps = Array.prototype.slice.call(document.querySelectorAll(".table-wrap"));
    if (!wraps.length) return;
    wraps.forEach(function (wrap) {
      wrap.setAttribute("data-region-label", wrap.getAttribute("aria-label") || "Tableau");
      wrap.addEventListener(
        "scroll",
        function () {
          wrap.classList.toggle("is-at-end", wrap.scrollLeft + wrap.clientWidth >= wrap.scrollWidth - 2);
        },
        { passive: true }
      );
    });

    function update() {
      wraps.forEach(function (wrap) {
        var scrollable = wrap.scrollWidth > wrap.clientWidth + 1;
        wrap.classList.toggle("is-scrollable", scrollable);
        wrap.classList.toggle("is-at-end", !scrollable || wrap.scrollLeft + wrap.clientWidth >= wrap.scrollWidth - 2);
        if (scrollable) {
          wrap.setAttribute("tabindex", "0");
          wrap.setAttribute("role", "region");
          wrap.setAttribute("aria-label", wrap.getAttribute("data-region-label"));
        } else {
          wrap.removeAttribute("tabindex");
          wrap.removeAttribute("role");
          wrap.removeAttribute("aria-label");
        }
      });
    }

    var pending = false;
    window.addEventListener("resize", function () {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(function () {
        pending = false;
        update();
      });
    });
    update();
  }

  ready(function () {
    initHeader();
    initMenu();
    initHow();
    initToc();
    initTables();
  });
})();
