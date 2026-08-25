/* The nav and the prev/next walk are static markup in every page, so nothing is
   inserted at load and the layout never shifts. This file only wires up the
   parts that need behaviour: the theme control and the comparison bars. */
(function () {
  const ICON = {
    light: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="4.6"/><path d="M12 2.6v2.4M12 19v2.4M2.6 12H5M19 12h2.4M5.4 5.4l1.7 1.7M16.9 16.9l1.7 1.7M18.6 5.4l-1.7 1.7M7.1 16.9l-1.7 1.7"/></svg>',
    dark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M20 14.2A8.4 8.4 0 0 1 9.8 4a8.5 8.5 0 1 0 10.2 10.2z"/></svg>',
  };
  // The icon shows the theme you are in; the label says what clicking does.
  const LABEL = { light: "Switch to dark theme", dark: "Switch to light theme" };

  function apply(mode) {
    document.documentElement.setAttribute("data-theme", mode);
  }

  // Two states only. The system preference decides the first visit; after that
  // the stored choice wins and the OS is no longer consulted.
  let mode = null;
  try { mode = localStorage.getItem("theme"); } catch (e) { /* private mode */ }
  if (mode !== "light" && mode !== "dark") {
    mode = window.matchMedia
      && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  apply(mode);

  const btn = document.getElementById("themebtn");
  if (btn) {
    const paint = () => {
      btn.innerHTML = ICON[mode];
      btn.title = LABEL[mode];
      btn.setAttribute("aria-label", LABEL[mode]);
    };
    paint();
    btn.addEventListener("click", () => {
      mode = mode === "dark" ? "light" : "dark";
      apply(mode);
      try { localStorage.setItem("theme", mode); } catch (e) { /* ignore */ }
      paint();
    });
  }

  // Click-to-play video: swap the poster for the real player only on click, so
  // the page never loads a third-party iframe for a visitor who does not watch.
  document.querySelectorAll(".vidplay").forEach((btn) => {
    // A private or still-processing video serves a 120x90 placeholder rather
    // than a 404, so detect it by size and drop to the box's own background.
    const thumb = btn.querySelector(".vidthumb");
    if (thumb) {
      const check = () => {
        if (thumb.naturalWidth && thumb.naturalWidth <= 120) {
          btn.closest(".vidbox").classList.add("nothumb");
        }
      };
      thumb.complete ? check() : (thumb.onload = check, thumb.onerror = () =>
        btn.closest(".vidbox").classList.add("nothumb"));
    }
    btn.addEventListener("click", () => {
      const id = btn.dataset.yt;
      if (!id) return;
      const f = document.createElement("iframe");
      f.src = "https://www.youtube-nocookie.com/embed/" + id +
              "?autoplay=1&rel=0&modestbranding=1";
      f.title = "Walkthrough video";
      f.allow = "accelerometer; autoplay; encrypted-media; picture-in-picture; web-share";
      f.referrerPolicy = "strict-origin-when-cross-origin";
      f.allowFullscreen = true;
      btn.replaceWith(f);
      f.focus();
    });
  });

  // Comparison bars start at zero width in CSS and are filled once, shortly after
  // load, so the transition plays. A timer rather than requestAnimationFrame:
  // rAF callbacks do not fire while a tab is in the background, which left the
  // bars permanently empty on any page opened in a hidden tab.
  const fills = document.querySelectorAll(".bar-fill[data-w]");
  if (fills.length) {
    setTimeout(() => {
      fills.forEach((f) => { f.style.width = f.dataset.w; });
    }, 40);
  }
})();
