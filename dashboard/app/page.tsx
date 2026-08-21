"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

import { EvaluationDiagram, ImprovementDiagram, LoopDiagram, ProductionDiagram, TiersDiagram } from "./Diagrams";
import Gallery from "./Gallery";
import { CallsBrowser, ComparisonScatter } from "./Calls";
import type { CallsData } from "./Calls";
import { ComponentBars, Methodology, ScenarioMatrix } from "./Results";
import type { ComponentRates, MetricDef, ScenarioRow } from "./Results";

type Metric = { label: string; value: string; detail: string; delta?: number };
type Family = { name: string; count: number; component: string; explains: string };
type Evidence = {
  scenario_id: string;
  said: string | null;
  turn: number | null;
  broke_on: string | null;
  owned_by: string | null;
  expected_action: { name: string; arguments: Record<string, unknown> } | null;
  tools_called: string[];
  declared_disposition: string | null;
};
type Arm = { label: string; task_successes: number; episodes: number; decision: string; severe_regressions: number; note: string; accepted: boolean };
type Condition = { label: string; passed: boolean };

type Act = {
  id: string;
  eyebrow: string;
  title: string;
  summary: string;
  metrics?: Metric[];
  families?: Family[];
  evidence?: Evidence[];
  arms?: Arm[];
  conditions?: Condition[];
  decision?: string;
  next_gate?: string;
  claim_boundary?: string;
  honesty?: string;
  tool_usage?: Record<string, number>;
  business_tool_episodes?: number;
};

type Story = {
  headline: { before: string; after: string; before_rate: number; after_rate: number; repairs: number; regressions: number };
  acts: Act[];
  still_open: Array<{ title: string; detail: string }>;
  calibration: { reference_status?: string; review_mode?: string; agreement?: Record<string, number>; interpretation?: string };
  metric_contract: MetricDef[];
  scenario_matrix: ScenarioRow[];
  component_rates: ComponentRates;
  evidence_tiers?: Array<{ id: string; label: string; n: number; before: string; after: string; independence: string; caveat: string }>;
  eva_coverage?: {
    intro: string;
    honesty: string;
    rows: Array<{ axis: string; metric: string; text: string; live: string; note: string }>;
  };
  layers?: {
    intro: string;
    rows: Array<{
      id: string; name: string; status: string; detail: string;
      lessons?: Array<{ lesson_id: string; rule: string; why: string; episode_count: number; applies_to_families: string[] }>;
      verifier?: {
        precision: number; recall: number; scope_limit: string; honesty_note: string;
        history: Array<{ revision: number; precision: number; recall: number; problem: string; fix: string }>;
      };
    }>;
  };
  judge_audit?: {
    detection: { agreement: number; n: number; cohen_kappa?: number | null };
    ownership: { agreement: number; n: number; cohen_kappa?: number | null };
    disagreements: Array<{ scenario_id: string; experiment: string; deterministic: string; judge: string }>;
    interpretation: string;
    independence_limit?: string;
  };
  claim_boundary: string;
  live_pilot?: {
    decision: string;
    decision_detail: string;
    transport: string;
    rounds: Array<{
      label: string; version: string; attempted: number; valid: number; task_passes: number;
      eva_a_passes: number; eva_x_passes: number; eva_a_mean: number; eva_x_mean: number;
      overall_mean: number; note: string;
    }>;
    scenarios: Array<{ id: string; name: string; initial: string; repair: string; result: string; audio: string }>;
    repairs_proven: string[];
    repairs_not_proven: string[];
  };
};

/* Five tabs. One headline per tab, stated in the first screen.
   The hash is the router, so every view is linkable. */
const TABS = [
  { id: "overview", label: "Overview" },
  { id: "how", label: "How it works" },
  { id: "results", label: "Results" },
  { id: "calls", label: "Calls" },
  { id: "limits", label: "Limits" },
] as const;
type TabId = (typeof TABS)[number]["id"];
const TAB_IDS = new Set<string>(TABS.map((tab) => tab.id));

const STEP_ORDER = ["measure", "diagnose", "improve", "reevaluate", "seal", "decide"] as const;
const STEP_META: Record<string, { name: string; does: string }> = {
  measure: { name: "Measure", does: "Run the deployed agent against scenarios with hidden goals, seeded state and executable tools." },
  diagnose: { name: "Diagnose", does: "Find the earliest turn after which the right outcome became impossible, and name its owner." },
  improve: { name: "Improve", does: "Open only the repair surface the evidence points at, and make candidates compete." },
  reevaluate: { name: "Re-evaluate", does: "Re-run the identical suite. The agent is the only thing that changed." },
  seal: { name: "Sealed test", does: "Open scenarios written after the method was frozen — once per agent." },
  decide: { name: "Decide", does: "An independent controller emits promote, hold or roll back. A human signs it." },
};

function tabFromHash(): TabId {
  if (typeof window === "undefined") return "overview";
  const hash = window.location.hash.slice(1);
  return TAB_IDS.has(hash) ? (hash as TabId) : "overview";
}

/** One short outcome per step, read off the generated act rather than authored. */
function stepOutcome(act?: Act): string {
  if (!act) return "—";
  if (act.decision) return act.decision;
  if (act.metrics?.length) {
    if (act.id === "seal" && act.metrics.length > 1) return `${act.metrics[0].value} → ${act.metrics[1].value}`;
    return act.metrics[0].value;
  }
  if (act.arms?.length) return `${act.arms.length} candidates · ${act.arms.filter((a) => !a.accepted).length} rejected`;
  if (act.families?.length) return `${act.families.length} families · ${act.families.reduce((s, f) => s + f.count, 0)} failures`;
  return "—";
}

/* A slot that says plainly when its data has not arrived yet, so the layout is
   finished before the campaign runs and only numbers get plugged in later. */
function Pending({ what }: { what: string }) {
  return <div className="pending"><b>Awaiting data</b> {what}</div>;
}

function Stat({ label, value, detail, tone }: { label: string; value: string; detail?: string; tone?: string }) {
  return (
    <div className={`stat ${tone ?? ""}`}>
      <p className="k">{label}</p>
      <p className="v">{value}</p>
      {detail && <p className="d">{detail}</p>}
    </div>
  );
}

function SectionHead({ eyebrow, title, lede }: { eyebrow: string; title: string; lede?: string }) {
  return (
    <div className="shead">
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      {lede && <p className="lede">{lede}</p>}
    </div>
  );
}

export default function Home() {
  const [story, setStory] = useState<Story | null>(null);
  const [calls, setCalls] = useState<CallsData | null>(null);
  // The URL is external state. useSyncExternalStore gives the server a stable
  // snapshot and the client the real one, so hydration cannot mismatch, and the
  // hash subscription replaces a manual listener.
  const subscribeHash = useCallback((onChange: () => void) => {
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const tab = useSyncExternalStore<TabId>(subscribeHash, tabFromHash, () => "overview");
  const preview = useSyncExternalStore(
    () => () => {},
    () => new URLSearchParams(window.location.search).get("view") === "c2",
    () => false,
  );
  const [theme, setTheme] = useState<"light" | "dark" | null>(null);

  useEffect(() => {
    if (preview) {
      fetch("/story.campaign2-preview.json").then((r) => r.json()).then(setStory).catch(() => undefined);
      fetch("/calls.campaign2-preview.json").then((r) => r.json()).then(setCalls).catch(() => undefined);
      return;
    }
    fetch("/story.json").then((r) => r.json()).then(setStory).catch(() => undefined);
  }, [preview]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [tab]);

  useEffect(() => {
    const label = TABS.find((t) => t.id === tab)?.label ?? "";
    document.title = tab === "overview" ? "Loopline — Voice Agent Learning Control Plane" : `Loopline — ${label}`;
  }, [tab]);

  const flipTheme = () => {
    const dark = theme ? theme === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    const next = dark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    setTheme(next);
  };

  const act = (id: string) => story?.acts.find((a) => a.id === id);
  const measure = act("measure");
  const reevaluate = act("reevaluate");
  const seal = act("seal");
  const decide = act("decide");
  const diagnose = act("diagnose");
  const improve = act("improve");
  const head = story?.headline;

  return (
    <main className="shell">
      {preview && (
        <div className="preview-banner" role="alert">
          <b>Campaign 2 preview — every number here is a placeholder.</b> Nothing has been measured; this shows the shape of the
          final result. <a href="?">Back to the measured page</a>
        </div>
      )}

      <header className="bar">
        <div className="bound">
          <span className="mark"><i />Loopline</span>
          <nav>
            {TABS.map((t) => (
              <a key={t.id} href={`#${t.id}`} className={tab === t.id ? "on" : undefined}>{t.label}</a>
            ))}
          </nav>
          <button className="theme" onClick={flipTheme} aria-label="Switch between light and dark appearance">
            {theme === "dark" ? "☾" : "☀"}
          </button>
        </div>
      </header>

      {/* ══ 1 · OVERVIEW ══ */}
      {tab === "overview" && (
        <>
          <section className="hero">
            <div className="bound hero-grid">
              <div>
                <p className="eyebrow grad">Voice agent learning control plane</p>
                <h1>Make every failure <em>teach the next release</em>.</h1>
                <p className="lede">
                  Loopline measures what a voice agent said, what its tools actually did, and where the call first broke. It repairs
                  the component that owns the failure, then makes an independent release gate challenge the fix.
                </p>
                <div className="hero-actions">
                  <a className="primary-action" href="#how">See how it works</a>
                  <a className="secondary-action" href="#calls">Inspect every call</a>
                </div>
                <p className="fine">Built on a real Sarvam Indus agent · EVA-inspired metrics · human-gated release</p>
              </div>
              <div className="hero-card">
                <div className="hc-top"><span>Headline · held-out</span>{head ? <b>{Math.round(head.after_rate * 100)}%</b> : null}</div>
                {head ? (
                  <>
                    <div className="hc-score">
                      <div><small>Original</small><strong className="loss">{head.before}</strong></div>
                      <span>→</span>
                      <div><small>Improved</small><strong className="gain">{head.after}</strong></div>
                    </div>
                    <div className="hc-meta">
                      <div><b>{head.repairs}</b><span>repaired</span></div>
                      <div><b>{head.regressions}</b><span>regressions</span></div>
                      <div><b>{head.source.includes("blind") ? "blind" : "sealed"}</b><span>split</span></div>
                    </div>
                  </>
                ) : <Pending what="— the headline populates from the campaign export." />}
                <p className="hc-note">
                  The optimiser never saw these scenarios. In-sample scores are reported separately and never lead.
                </p>
              </div>
            </div>
          </section>

          <section className="band">
            <div className="bound">
              <SectionHead eyebrow="Three tiers of evidence" title="Measured three ways, identically, before and after."
                lede="Each tier answers a different question. None of them is allowed to borrow another's denominator." />
              <TiersDiagram />
              {story?.evidence_tiers ? (
                <div className="tiergrid">
                  {story.evidence_tiers.map((t) => (
                    <div className="tier" key={t.id}>
                      <span className={`badge ${t.independence === "out-of-sample" ? "gain" : t.independence === "hold" ? "hold" : "dim"}`}>{t.independence}</span>
                      <h4>{t.label}</h4>
                      <p className="score"><span className="loss">{t.before}</span> <i>→</i> <span className="gain">{t.after}</span></p>
                      <p className="fine">{t.caveat}</p>
                    </div>
                  ))}
                </div>
              ) : <Pending what="— tier results populate after the before and after runs." />}
            </div>
          </section>

          <section className="band alt">
            <div className="bound">
              <SectionHead eyebrow="What it is for" title="From one failed call to a release decision."
                lede="Most agent tooling mixes measuring with changing, which lets the thing being optimised quietly redefine success. Here the three responsibilities never merge." />
              <LoopDiagram />
            </div>
          </section>
        </>
      )}

      {/* ══ 2 · HOW IT WORKS ══ */}
      {tab === "how" && (
        <>
          <section className="band">
            <div className="bound">
              <SectionHead eyebrow="The loop · six steps" title="Each step produces the evidence the next one consumes."
                lede="Run in order, ending in a decision a human signs." />
              <div className="steps">
                {STEP_ORDER.map((id, i) => {
                  const a = act(id);
                  return (
                    <div className="stepcard" key={id}>
                      <span className="num">{i + 1}</span>
                      <div>
                        <h4>{STEP_META[id].name}</h4>
                        <p>{STEP_META[id].does}</p>
                        <p className="out">{a ? stepOutcome(a) : "awaiting data"}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          <section className="band alt">
            <div className="bound">
              <SectionHead eyebrow="Inside one episode" title="A claim is not an effect."
                lede="Validity is checked before anything is scored, executable truth outranks opinion, and the judge never reaches the gate." />
              <EvaluationDiagram />
              <div className="callout">
                <b>The distinction the whole project turns on.</b> When an agent says “I have noted your promise” and declares an
                outcome, the state gets written for it — but that write never enters the tool log. Read the transcript and the call
                looks like a success. Only the tool trace separates a pass from a silent failure.
              </div>
            </div>
          </section>

          <section className="band">
            <div className="bound">
              <SectionHead eyebrow="Diagnosis → improvement" title="The evidence picks the repair surface."
                lede="A prompt optimiser is one arm here, not the framework." />
              {diagnose?.families ? (
                <div className="families">
                  {diagnose.families.map((f) => (
                    <div className="family" key={f.name}>
                      <span className="n mono">{f.count}</span>
                      <div>
                        <h4>{f.name}</h4>
                        <p>{f.explains}</p>
                        <p className="own mono">owned by {f.component.replaceAll("_", " ")}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : <Pending what="— failure families are grouped after the baseline runs." />}
              <ImprovementDiagram />
              {improve?.arms ? (
                <div className="arms">
                  {improve.arms.map((arm) => (
                    <div className={`arm ${arm.accepted ? "kept" : ""}`} key={arm.label}>
                      <div><h4>{arm.label}</h4><p>{arm.note}</p></div>
                      <span className="score mono">{arm.task_successes}/{arm.episodes}</span>
                      <span className={`badge ${arm.accepted ? "gain" : "loss"}`}>
                        {arm.accepted ? "accepted" : `rejected · ${arm.severe_regressions} severe`}
                      </span>
                    </div>
                  ))}
                </div>
              ) : <Pending what="— candidate arms populate after the improvement round." />}
              <div className="callout">
                It produced a strong candidate and the gate still rejected it, because a higher average cannot buy back a safety
                regression. Losing candidates are kept — a rejection is evidence that the gate works.
              </div>
            </div>
          </section>

          <section className="band alt">
            <div className="bound">
              <SectionHead eyebrow="The metric contract" title="What gets checked, by what, and what has to be true to pass."
                lede="Written down before a candidate runs and unchangeable while candidates are compared. Executable checks decide; a language model grades only what code cannot." />
              {story?.metric_contract ? <Methodology metrics={story.metric_contract} /> : <Pending what="— the metric contract renders from the frozen evaluator." />}
            </div>
          </section>
        </>
      )}

      {/* ══ 3 · RESULTS ══ */}
      {tab === "results" && (
        <>
          <section className="band">
            <div className="bound">
              <SectionHead eyebrow="Results" title="Not one headline number. Every check, and every call."
                lede="A single success rate hides which checks moved. Development scores are shown, labelled, and never allowed to lead — those are the scenarios the repair was built against, so a high score there is close to circular." />
              <div className="statrow">
                {measure?.metrics?.slice(0, 3).map((m) => <Stat key={m.label} label={m.label} value={m.value} detail={m.detail} tone="loss" />)}
              </div>
              <p className="arrowdown">after the repair ↓</p>
              <div className="statrow">
                {reevaluate?.metrics?.slice(0, 3).map((m) => <Stat key={m.label} label={m.label} value={m.value} detail={m.detail} tone="gain" />)}
              </div>
              {!measure && <Pending what="— before and after panels populate from the two measurement rounds." />}
            </div>
          </section>

          <section className="band alt">
            <div className="bound">
              <SectionHead eyebrow="Accuracy versus experience" title="Every live call, both agents, on the two axes that matter."
                lede="One dot per call per agent. The diamond is the arm mean; the line is the shift the repair bought." />
              {calls ? <ComparisonScatter data={calls} /> : <Pending what="— the scatter draws from per-call live results." />}
            </div>
          </section>

          <section className="band">
            <div className="bound">
              <SectionHead eyebrow="Per-check pass rates" title="Which checks actually moved." />
              {story?.component_rates ? <ComponentBars rates={story.component_rates} /> : <Pending what="— per-check rates populate with the paired comparison." />}
            </div>
          </section>

          <section className="band alt">
            <div className="bound">
              <SectionHead eyebrow="The sealed test" title="Opened exactly once per agent."
                lede="Written after the method was frozen, hashed, never shown to the optimiser, access-logged." />
              <div className="statrow">
                {seal?.metrics?.map((m) => <Stat key={m.label} label={m.label} value={m.value} detail={m.detail} />)}
              </div>
              {!seal && <Pending what="— the sealed result appears once both agents have opened it." />}
              <div className="verdict">
                <span>Release decision</span>
                <b>{decide?.decision ?? "awaiting the gate"}</b>
                <p>{decide?.summary ?? "The controller reads the frozen artifacts and applies per-case rules. No aggregate score can outvote a single severe regression."}</p>
              </div>
            </div>
          </section>

          <section className="band">
            <div className="bound">
              <SectionHead eyebrow="Every scenario" title="The full suite, one row at a time." />
              {story?.scenario_matrix ? <ScenarioMatrix rows={story.scenario_matrix} /> : <Pending what="— the scenario matrix renders per-case results." />}
            </div>
          </section>
        </>
      )}

      {/* ══ 4 · CALLS ══ */}
      {tab === "calls" && (
        <>
          <section className="band">
            <div className="bound">
              <SectionHead eyebrow="The call browser" title="Every call, inspectable — original and improved, side by side."
                lede="Pick any call: the scenario briefing, the full tool catalogue with what each agent actually used, and every metric with how it was scored. Unused tools stay listed — that is the rubric." />
              {calls ? <CallsBrowser data={calls} /> : <Pending what="— the browser fills with the recorded and bot-to-bot calls." />}
            </div>
          </section>
          <section className="band alt">
            <div className="bound">
              <SectionHead eyebrow="Deep cases" title="Auditable down to the assertion."
                lede="Each card is generated from a preserved artifact — transcript, tool calls with arguments and results, state before and after, and the turn where the run first broke." />
              <Gallery />
            </div>
          </section>
        </>
      )}

      {/* ══ 5 · LIMITS ══ */}
      {tab === "limits" && (
        <>
          <section className="band">
            <div className="bound">
              <SectionHead eyebrow="What this does not prove" title="The limits are part of the result."
                lede="The improvement is real and reproducible. It is also bounded, and the boundaries are stated here rather than left for someone to find." />
              {story?.still_open ? (
                <div className="limits">
                  {story.still_open.map((item, i) => (
                    <div className="limit" key={item.title}>
                      <span className="num mono">{String(i + 1).padStart(2, "0")}</span>
                      <div><h4>{item.title}</h4><p>{item.detail}</p></div>
                    </div>
                  ))}
                </div>
              ) : <Pending what="— the limits list is generated with the campaign." />}
            </div>
          </section>

          <section className="band alt">
            <div className="bound">
              <SectionHead eyebrow="How good is the grader?" title="A grader whose accuracy is unstated should not be trusted."
                lede="Publishing the number is the point." />
              {story?.judge_audit ? (
                <div className="statrow">
                  <Stat label="Agreement · did it fail at all" value={`${Math.round(story.judge_audit.detection.agreement * 100)}%`} detail={`n=${story.judge_audit.detection.n}`} />
                  <Stat label="Agreement · which component owns it" value={`${Math.round(story.judge_audit.ownership.agreement * 100)}%`} detail={`n=${story.judge_audit.ownership.n}`} />
                  <Stat label="Cohen’s κ · detection" value={String(story.judge_audit.detection.cohen_kappa ?? "—")} detail="vs the executable checker" />
                  <Stat label="Cohen’s κ · ownership" value={String(story.judge_audit.ownership.cohen_kappa ?? "—")} detail="advisory routing only" />
                </div>
              ) : <Pending what="— judge agreement is recomputed from preserved episodes." />}
              <div className="callout">{story?.judge_audit?.interpretation ?? "The judge is reliable at noticing that something went wrong and materially less reliable at saying what owns it. That is why ownership routing is advisory and the executable checker controls the gate."}</div>
            </div>
          </section>

          <section className="band">
            <div className="bound">
              <SectionHead eyebrow="From one agent to a platform" title="The loop transfers. The substrate has to be built."
                lede="The control loop is domain-independent. What does not exist yet at production scale is set out here rather than waved at." />
              <ProductionDiagram />
              <div className="callout">
                First deliverable on a real corpus is a calibrated baseline and a ranked failure taxonomy — not a prompt rewrite.
              </div>
            </div>
          </section>
        </>
      )}

      <footer className="foot">
        <div className="bound">
          <p>{story?.claim_boundary ?? "Every figure comes from a preserved evaluation artifact."}</p>
          <p className="fine">Built by Arnav for Sarvam · EMI recovery is the reference domain · all customer data is fictional.</p>
        </div>
      </footer>
    </main>
  );
}
