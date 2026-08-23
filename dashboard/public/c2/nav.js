/* Shared chrome: the section bar, the theme control, and the prev/next walk.
   Theme has three states (auto, light, dark) so a reader can override their OS
   without the page ever rendering one theme's text on the other's background. */
(function () {
  const PAGES = [
    ["overview.html",  "Overview"],
    ["problem.html",   "The problem"],
    ["system.html",    "How it is measured"],
    ["diagnosis.html", "What broke"],
    ["loop.html",      "How it improved"],
    ["results.html",   "Results"],
    ["calls.html",     "Listen"],
    ["notes.html",     "Limits"],
  ];

  const ICON = {
    auto: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17" /><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none"/></svg>',
    light: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="4.6"/><path d="M12 2.6v2.4M12 19v2.4M2.6 12H5M19 12h2.4M5.4 5.4l1.7 1.7M16.9 16.9l1.7 1.7M18.6 5.4l-1.7 1.7M7.1 16.9l-1.7 1.7"/></svg>',
    dark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M20 14.2A8.4 8.4 0 0 1 9.8 4a8.5 8.5 0 1 0 10.2 10.2z"/></svg>',
  };
  const ORDER = ["auto", "light", "dark"];
  const LABEL = { auto: "Theme: follows your system", light: "Theme: light", dark: "Theme: dark" };

  function apply(mode) {
    if (mode === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", mode);
  }

  let mode = "auto";
  try { mode = localStorage.getItem("theme") || "auto"; } catch (e) { /* private mode */ }
  if (!ORDER.includes(mode)) mode = "auto";
  apply(mode);

  const here = location.pathname.split("/").pop() || "overview.html";
  const nav = document.createElement("nav");
  nav.className = "topnav";
  nav.innerHTML =
    PAGES.map(([href, label]) =>
      `<a href="${href}"${href === here ? ' class="on" aria-current="page"' : ""}>${label}</a>`
    ).join("") +
    '<span class="sp"></span>' +
    `<button class="themebtn" id="themebtn" title="${LABEL[mode]}" aria-label="${LABEL[mode]}">${ICON[mode]}</button>`;
  document.body.prepend(nav);

  const btn = nav.querySelector("#themebtn");
  btn.addEventListener("click", () => {
    mode = ORDER[(ORDER.indexOf(mode) + 1) % ORDER.length];
    apply(mode);
    try { localStorage.setItem("theme", mode); } catch (e) { /* ignore */ }
    btn.innerHTML = ICON[mode];
    btn.title = LABEL[mode];
    btn.setAttribute("aria-label", LABEL[mode]);
  });

  // Keep the active tab visible when the bar has to scroll on a narrow screen.
  const active = nav.querySelector("a.on");
  if (active) active.scrollIntoView({ block: "nearest", inline: "center" });

  const i = PAGES.findIndex(([href]) => href === here);
  const walk = document.createElement("div");
  walk.className = "walk";
  walk.innerHTML =
    (i > 0
      ? `<a href="${PAGES[i - 1][0]}"><span class="k">Back</span><span class="t">${PAGES[i - 1][1]}</span></a>`
      : "<span></span>") +
    (i < PAGES.length - 1
      ? `<a class="next" href="${PAGES[i + 1][0]}"><span class="k">Next</span><span class="t">${PAGES[i + 1][1]}</span></a>`
      : "");
  document.querySelector(".shell")?.append(walk);

  // Fill the comparison bars. Widths are applied on the next frame so the CSS
  // transition still plays for anything already on screen, but nothing depends
  // on a scroll event ever arriving: a bar that is never scrolled past still
  // ends up at its correct width.
  const fills = document.querySelectorAll(".bar-fill[data-w]");
  if (fills.length) {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        fills.forEach((f) => { f.style.width = f.dataset.w; });
      });
    });
  }
})();
