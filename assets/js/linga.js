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

  /* ------------------------------------------------------------------------------------------------------------
     Mouvement. Rien de tout cela n'est nécessaire pour lire la page : sans JavaScript, ou avec « réduire les
     animations », tout est déjà à sa place (la CSS ne masque rien dans ces cas-là). */

  var each = function (list, fn) {
    Array.prototype.forEach.call(list, fn);
  };

  /* Quand un élément entre à l'écran (une seule fois). Sans IntersectionObserver : tout de suite. */
  function whenVisible(elements, fn, options) {
    if (!("IntersectionObserver" in window)) {
      each(elements, fn);
      return;
    }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        fn(entry.target);
      });
    }, options || { rootMargin: "0px 0px -12% 0px", threshold: 0.05 });
    each(elements, function (element) {
      observer.observe(element);
    });
  }

  /* Titre de l'accueil : chaque mot dans deux span, pour le faire monter (le texte reste le même pour tout le monde). */
  function initWords() {
    if (reduceMotion) return;
    each(document.querySelectorAll("[data-words]"), function (title) {
      var index = 0;
      var walk = function (node) {
        Array.prototype.slice.call(node.childNodes).forEach(function (child) {
          if (child.nodeType === 1) {
            walk(child);
            return;
          }
          if (child.nodeType !== 3 || !child.textContent.trim()) return;
          var fragment = document.createDocumentFragment();
          child.textContent.split(/(\s+)/).forEach(function (part) {
            if (!part) return;
            if (/^\s+$/.test(part)) {
              fragment.appendChild(document.createTextNode(part));
              return;
            }
            var outer = document.createElement("span");
            var inner = document.createElement("span");
            outer.className = "w";
            inner.textContent = part;
            inner.style.setProperty("--i", String(index++));
            outer.appendChild(inner);
            fragment.appendChild(outer);
          });
          child.parentNode.replaceChild(fragment, child);
        });
      };
      walk(title);
      title.classList.add("is-split");
    });
  }

  /* Blocs qui entrent quand on y arrive ; dans une même liste, l'un après l'autre. */
  function initReveal() {
    var blocks = document.querySelectorAll("[data-reveal]");
    if (!blocks.length) return;
    each(blocks, function (block) {
      var siblings = block.parentNode.querySelectorAll(":scope > [data-reveal]");
      var position = Array.prototype.indexOf.call(siblings, block);
      if (position > 0) block.style.setProperty("--d", String(Math.min(position, 6) * 90));
    });
    if (reduceMotion) {
      each(blocks, function (block) {
        block.classList.add("is-in");
      });
      return;
    }
    whenVisible(blocks, function (block) {
      block.classList.add("is-in");
    });
  }

  /* Chiffres des engagements : ils défilent jusqu'à leur valeur (0 pub part de 99 et descend). */
  function initCounters() {
    var numbers = document.querySelectorAll("[data-count]");
    if (!numbers.length || reduceMotion) return;
    each(numbers, function (number) {
      number.textContent = number.getAttribute("data-from") || "0";
    });
    whenVisible(numbers, function (number) {
      var from = Number(number.getAttribute("data-from") || 0);
      var to = Number(number.getAttribute("data-count"));
      var start = null;
      var duration = 1400;
      var step = function (time) {
        if (start === null) start = time;
        var t = Math.min(1, (time - start) / duration);
        var eased = 1 - Math.pow(1 - t, 4);
        number.textContent = String(Math.round(from + (to - from) * eased));
        if (t < 1) window.requestAnimationFrame(step);
      };
      window.requestAnimationFrame(step);
    }, { threshold: 0.6 });
  }

  /* Téléphone du haut : il suit un peu la souris, et les notifications de l'app descendent sur l'écran. */
  function initHeroPhone() {
    var tilt = document.querySelector("[data-tilt]");
    if (!tilt || reduceMotion) return;
    var hero = tilt.closest(".hero") || document.body;

    if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
      var target = { x: 0, y: 0 };
      var current = { x: 0, y: 0 };
      var frame = 0;
      var loop = function () {
        current.x += (target.x - current.x) * 0.08;
        current.y += (target.y - current.y) * 0.08;
        tilt.style.setProperty("--rx", (current.y * -7).toFixed(2) + "deg");
        tilt.style.setProperty("--ry", (current.x * 9).toFixed(2) + "deg");
        if (Math.abs(target.x - current.x) + Math.abs(target.y - current.y) > 0.001) {
          frame = window.requestAnimationFrame(loop);
        } else {
          frame = 0;
        }
      };
      var aim = function (x, y) {
        target.x = x;
        target.y = y;
        if (!frame) frame = window.requestAnimationFrame(loop);
      };
      hero.addEventListener("pointermove", function (event) {
        var box = hero.getBoundingClientRect();
        aim((event.clientX - box.left) / box.width - 0.5, (event.clientY - box.top) / box.height - 0.5);
      });
      hero.addEventListener("pointerleave", function () {
        aim(0, 0);
      });
    }

    var pushes = tilt.querySelectorAll("[data-push]");
    var tap = tilt.querySelector(".tap");
    if (!pushes.length) return;
    var timers = [];
    var running = false;
    var later = function (fn, ms) {
      timers.push(window.setTimeout(fn, ms));
    };
    var cycle = function () {
      if (!running) return;
      if (tap) {
        later(function () {
          tap.classList.remove("is-on");
          void tap.offsetWidth; /* relance l'animation */
          tap.classList.add("is-on");
        }, 1400);
      }
      later(function () { pushes[0].classList.add("is-shown"); }, 2000);
      later(function () { pushes[0].classList.remove("is-shown"); }, 5600);
      if (pushes[1]) {
        later(function () { pushes[1].classList.add("is-shown"); }, 6600);
        later(function () { pushes[1].classList.remove("is-shown"); }, 10200);
      }
      later(cycle, 11400);
    };
    var start = function () {
      if (running) return;
      running = true;
      cycle();
    };
    var stop = function () {
      running = false;
      timers.forEach(window.clearTimeout);
      timers = [];
      each(pushes, function (push) {
        push.classList.remove("is-shown");
      });
    };
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        if (entries[0].isIntersecting && !document.hidden) start();
        else stop();
      }, { threshold: 0.25 }).observe(tilt);
      document.addEventListener("visibilitychange", function () {
        if (document.hidden) stop();
      });
    } else {
      start();
    }
  }

  /* « Comment ça marche » : le fil vertical se remplit à mesure qu'on descend dans les étapes. */
  function initSpine() {
    var spine = document.querySelector(".how__spine");
    var steps = spine && spine.parentNode;
    if (!spine || !steps || reduceMotion) return;
    var ticking = false;
    var update = function () {
      ticking = false;
      var box = steps.getBoundingClientRect();
      var middle = window.innerHeight * 0.5;
      var progress = (middle - box.top) / Math.max(1, box.height);
      spine.style.setProperty("--p", Math.max(0, Math.min(1, progress)).toFixed(4));
    };
    window.addEventListener("scroll", function () {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    }, { passive: true });
    window.addEventListener("resize", update);
    update();
  }

  /* Les conversations ne défilent que lorsqu'on les voit. */
  function initMarquee() {
    var rows = document.querySelector("[data-marquee]");
    var section = rows && rows.closest(".chatter");
    if (!section || !("IntersectionObserver" in window)) return;
    new IntersectionObserver(function (entries) {
      section.classList.toggle("is-paused", !entries[0].isIntersecting);
    }).observe(rows);
  }

  /* L'éventail des trois écrans s'ouvre quand on arrive dessus. */
  function initFan() {
    var fans = document.querySelectorAll("[data-fan]");
    if (!fans.length) return;
    if (reduceMotion) {
      each(fans, function (fan) {
        fan.classList.add("is-open");
      });
      return;
    }
    whenVisible(fans, function (fan) {
      fan.classList.add("is-open");
    }, { threshold: 0.35 });
  }

  ready(function () {
    initWords();
    initHeader();
    initMenu();
    initHow();
    initToc();
    initTables();
    initReveal();
    initCounters();
    initHeroPhone();
    initSpine();
    initMarquee();
    initFan();
  });
})();
