"use client";

/* Flows.
   Built from real elements rather than plotted SVG: a hand-placed diagram is
   never quite aligned and never responsive. These are cards in a grid with
   connectors drawn by CSS, so they inherit the type scale, the palette and the
   spacing rhythm of everything else on the page. */

type Tone = "plain" | "accent" | "gain" | "hold" | "tool" | "deep";

type Step = {
  kicker?: string;
  title: string;
  lines?: string[];
  tone?: Tone;
};

function Card({ step }: { step: Step }) {
  return (
    <div className={`fc ${step.tone ?? "plain"}`}>
      {step.kicker && <span className="fc-k">{step.kicker}</span>}
      <h4>{step.title}</h4>
      {step.lines?.length ? (
        <ul>
          {step.lines.map((line) => <li key={line}>{line}</li>)}
        </ul>
      ) : null}
    </div>
  );
}

/** A row of cards joined by connectors. Stacks cleanly on narrow screens. */
function Flow({ steps, note }: { steps: Step[]; note?: string }) {
  return (
    <div className="flow">
      <div className="flow-row" style={{ ["--n" as string]: steps.length }}>
        {steps.map((step, i) => (
          <div className="flow-cell" key={step.title}>
            <Card step={step} />
            {i < steps.length - 1 && <span className="flow-join" aria-hidden="true" />}
          </div>
        ))}
      </div>
      {note && <p className="flow-note">{note}</p>}
    </div>
  );
}

/** Three labelled columns, each a small stack. Used for the engine split. */
function Lanes({ lanes, note }: { lanes: Array<{ label: string; tone: Tone; steps: Step[] }>; note?: string }) {
  return (
    <div className="flow">
      <div className="lanes">
        {lanes.map((lane) => (
          <section className={`lane ${lane.tone}`} key={lane.label}>
            <header>{lane.label}</header>
            {lane.steps.map((step) => <Card step={step} key={step.title} />)}
          </section>
        ))}
      </div>
      {note && <p className="flow-note">{note}</p>}
    </div>
  );
}

/* ── 1. Three engines, one cycle ───────────────────────────────────────── */
export function LoopDiagram() {
  return (
    <Lanes
      note="The evaluator cannot edit the agent. The improver cannot approve itself. A promoted agent re-enters the same suite next cycle."
      lanes={[
        {
          label: "01 · Measure",
          tone: "accent",
          steps: [
            { kicker: "Input", title: "Scenario contract", lines: ["Hidden caller goal and persona", "Seeded account state", "Required and forbidden actions"] },
            { kicker: "Run + score", title: "Executed episode", tone: "accent", lines: ["Validity before scoring", "Deterministic truth before judges", "First break and owning component"] },
          ],
        },
        {
          label: "02 · Improve",
          tone: "hold",
          steps: [
            { kicker: "Route", title: "Failure packet", lines: ["Evidence turn, verbatim", "Severity and owner", "Becomes a permanent test"] },
            { kicker: "Repair", title: "Competing candidates", tone: "hold", lines: ["Optimiser, manual, control", "Versioned diff and hypothesis", "Losers retained as evidence"] },
          ],
        },
        {
          label: "03 · Release",
          tone: "gain",
          steps: [
            { kicker: "Compare", title: "Frozen per-case gate", lines: ["Same suite, same evaluator hash", "No severe regression averaged away", "Sealed test opened once"] },
            { kicker: "Decide", title: "Promote · hold · roll back", tone: "gain", lines: ["A human signs the release", "Published whichever way it lands"] },
          ],
        },
      ]}
    />
  );
}

/* ── 2. Inside one episode ─────────────────────────────────────────────── */
export function EvaluationDiagram() {
  return (
    <Flow
      note="Validity is checked before anything is scored, executable truth outranks opinion, and the judge never reaches the gate."
      steps={[
        { kicker: "Setup", title: "Caller, agent, environment", lines: ["Hidden goal, never revealed", "The prompt under test", "Fresh database per trial"] },
        { kicker: "Artifact", title: "Preserved episode", tone: "accent", lines: ["Transcript, turn by turn", "Tool calls with arguments", "State before and after"] },
        { kicker: "Gate 0", title: "Was this fair to score?", tone: "hold", lines: ["Off-policy or unterminated", "Excluded, never counted as failure"] },
        { kicker: "Decides", title: "Deterministic truth", tone: "gain", lines: ["Outcome, state, required calls", "Guardrails", "A claim is not an effect"] },
      ]}
    />
  );
}

/* ── 3. The repair router ──────────────────────────────────────────────── */
export function ImprovementDiagram() {
  return (
    <Flow
      note="A prompt rewrite cannot fix a broken tool contract, so the evidence picks the surface — not the symptom."
      steps={[
        { kicker: "Input", title: "Failure packets", tone: "plain", lines: ["Grouped into families", "Ranked by severity"] },
        { kicker: "Router", title: "Pick one surface", tone: "accent", lines: ["Prompt, extractor, tool,", "workflow, policy or runtime", "Exactly one is opened"] },
        { kicker: "Output", title: "Gated candidate", tone: "hold", lines: ["Exact diff and hash", "Stated hypothesis", "Faces the frozen gate"] },
      ]}
    />
  );
}

/* ── 4. Three evidence tiers ───────────────────────────────────────────── */
export function TiersDiagram() {
  return (
    <Flow
      note="One evaluator hash, one set of rules, every tier measured identically before and after. The headline never comes from data the optimiser was allowed to see."
      steps={[
        { kicker: "Tier 1 · text", title: "Synthetic conversations", tone: "accent", lines: ["Families × languages × variants", "Cheap, reproducible, large n", "The optimiser learns here"] },
        { kicker: "Tier 2 · human", title: "Calls you record", tone: "hold", lines: ["Real speech, real improvisation", "Owner-confirmed labels", "Tool effects checked in the journal"] },
        { kicker: "Tier 3 · voice", title: "Bot-to-bot, duplex audio", tone: "gain", lines: ["Full accuracy and experience set", "Audio-only metrics scorable", "Matched arms, identical records"] },
      ]}
    />
  );
}

/* ── 5. Production substrate ───────────────────────────────────────────── */
export function ProductionDiagram() {
  return (
    <Lanes
      note="The first deliverable on a real corpus is a calibrated baseline and a ranked failure taxonomy — not a prompt rewrite."
      lanes={[
        {
          label: "Built · proven at MVP scale",
          tone: "gain",
          steps: [
            { title: "Scenario contracts", lines: ["One pack per domain"] },
            { title: "Executable verifiers", lines: ["State, tools, guardrails"] },
            { title: "First break and routing", lines: ["Failure to owning component"] },
            { title: "Per-case release gate", lines: ["Promote, hold, roll back"] },
          ],
        },
        {
          label: "Must be built for production",
          tone: "hold",
          steps: [
            { title: "Ingestion and redaction", lines: ["Strip PII at volume"] },
            { title: "Outcome join", lines: ["Ledger — proxy to truth"] },
            { title: "Sampling and human review", lines: ["Keeps the grader honest"] },
            { title: "Canary, rollback, drift", lines: ["Automatic revert"] },
          ],
        },
      ]}
    />
  );
}
