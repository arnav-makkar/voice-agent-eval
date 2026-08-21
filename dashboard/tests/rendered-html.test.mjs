import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders Loopline without starter scaffolding", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /Loopline — Voice Agent Learning Control Plane/i);
  assert.match(html, /release gate challenge the fix/i);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site|react-loading-skeleton/i);
});

test("the headline is the held-out result, not the in-sample one", async () => {
  const [page, story] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../public/story.json", import.meta.url), "utf8"),
  ]);
  const parsed = JSON.parse(story);
  // Leading with the development suite would be close to circular: those are the
  // scenarios the repair was built against.
  assert.equal(parsed.headline.source, "sealed held-out test");
  assert.ok(parsed.headline.after_rate < 1, "headline must not be a 100% in-sample figure");
  // All three tiers stay on the page, including the live pilot that failed its gate.
  const tiers = parsed.evidence_tiers.map((tier) => tier.independence);
  assert.deepEqual(tiers, ["in-sample", "out-of-sample", "hold"]);
  assert.equal(parsed.live_pilot.decision, "HOLD");
  assert.equal(parsed.live_pilot.rounds[1].valid, 1);
  assert.match(page, /close to circular/);
});

test("the narrative keeps measurement, improvement, and release separate", async () => {
  const [page, story] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../public/story.json", import.meta.url), "utf8"),
  ]);
  // The evaluation must be stated as unchanged across the comparison. That claim
  // lives in the generated narrative, so assert it there rather than in the page.
  const reevaluate = JSON.parse(story).acts.find((act) => act.id === "reevaluate");
  assert.match(reevaluate.summary, /same evaluator, same thresholds/i);
  assert.match(reevaluate.summary, /only variable is the agent/i);
  // The optimiser must never be presented as the framework, or as its own approver.
  assert.match(page, /A prompt optimiser is one arm here, not the framework/);
  assert.match(page, /the gate still rejected it/);
  // Limits must remain on the page rather than being quietly dropped.
  assert.match(page, /The limits are part of the result/);
  assert.match(page, /How good is the grader\?/);
  assert.doesNotMatch(page, /Offline lift cleared|held-out is sealed and unopened|no guardrail regression/i);
});

test("the story and gallery are generated from artifacts, not authored in the page", async () => {
  const [page, story, gallery] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../public/story.json", import.meta.url), "utf8"),
    readFile(new URL("../public/gallery.json", import.meta.url), "utf8"),
  ]);
  assert.match(page, /fetch\("\/story\.json"\)/);
  const parsed = JSON.parse(story);
  assert.equal(parsed.acts.length, 6);
  // Headline figures must come from the export, never be hardcoded in the page.
  assert.doesNotMatch(page, /16 of 30|30 of 30/);
  assert.ok(parsed.still_open.length >= 4, "limits section must stay populated");
  assert.ok(JSON.parse(gallery).cards.length >= 6, "gallery must retain its episode cards");
  await assert.rejects(access(new URL("../app/_sites-preview/SkeletonPreview.tsx", import.meta.url)));
});
