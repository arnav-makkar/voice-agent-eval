/* The nav and the prev/next walk are static markup in every page, so nothing is
   inserted at load and the layout never shifts. This file only wires up the
   parts that need behaviour: the theme control and the comparison bars. */
(function () {
  const ICON = {
    auto: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none"/></svg>',
    light: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="4.6"/><path d="M12 2.6v2.4M12 19v2.4M2.6 12H5M19 12h2.4M5.4 5.4l1.7 1.7M16.9 16.9l1.7 1.7M18.6 5.4l-1.7 1.7M7.1 16.9l-1.7 1.7"/></svg>',
    dark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M20 14.2A8.4 8.4 0 0 1 9.8 4a8.5 8.5 0 1 0 10.2 10.2z"/></svg>',
  };
  const ORDER = ["auto", "light", "dark"];
  const LABEL = {
    auto: "Theme: follows your system",
    light: "Theme: light",
    dark: "Theme: dark",
  };

  function apply(mode) {
    if (mode === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", mode);
  }

  let mode = "auto";
  try { mode = localStorage.getItem("theme") || "auto"; } catch (e) { /* private mode */ }
  if (!ORDER.includes(mode)) mode = "auto";
  apply(mode);

  const btn = document.getElementById("themebtn");
  if (btn) {
    if (mode !== "auto") {
      btn.innerHTML = ICON[mode];
      btn.title = LABEL[mode];
      btn.setAttribute("aria-label", LABEL[mode]);
    }
    btn.addEventListener("click", () => {
      mode = ORDER[(ORDER.indexOf(mode) + 1) % ORDER.length];
      apply(mode);
      try { localStorage.setItem("theme", mode); } catch (e) { /* ignore */ }
      btn.innerHTML = ICON[mode];
      btn.title = LABEL[mode];
      btn.setAttribute("aria-label", LABEL[mode]);
    });
  }

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
