/* One nav for every page. The order is the order of the talk. */
(function () {
  const PAGES = [
    ["overview.html", "Overview"],
    ["problem.html", "The failure mode"],
    ["system.html", "The instrument"],
    ["diagnosis.html", "Diagnosis"],
    ["loop.html", "The loop"],
    ["results.html", "Results"],
    ["calls.html", "Call evidence"],
    ["notes.html", "Limits & references"],
  ];
  const here = location.pathname.split("/").pop() || "overview.html";
  const nav = document.createElement("nav");
  nav.className = "topnav";
  nav.innerHTML =
    '<span class="word">Execution truth</span>' +
    PAGES.map(([href, label]) =>
      `<a href="${href}"${href === here ? ' class="on"' : ""}>${label}</a>`).join("") +
    '<span class="sp"></span>';
  document.body.prepend(nav);

  const i = PAGES.findIndex(([href]) => href === here);
  const walk = document.createElement("div");
  walk.className = "walk";
  walk.innerHTML =
    (i > 0 ? `<a href="${PAGES[i - 1][0]}"><span class="k">Previous</span><span class="t">${PAGES[i - 1][1]}</span></a>` : "<span></span>") +
    (i < PAGES.length - 1 ? `<a class="next" href="${PAGES[i + 1][0]}"><span class="k">Next</span><span class="t">${PAGES[i + 1][1]}</span></a>` : "");
  document.querySelector(".shell")?.append(walk);
})();
