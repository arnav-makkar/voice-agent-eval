"use client";

/* Flowcharts.
   Drawn from theme tokens so light and dark both work, on a fixed viewBox grid
   so nothing ever overlaps. Each diagram reads left-to-right or top-to-bottom
   in one direction only — a flowchart that needs tracing is a failed flowchart. */

const INK = "var(--ink)";
const INK2 = "var(--ink-2)";
const INK3 = "var(--ink-3)";
const RULE = "var(--rule-2)";

type Tone = "plain" | "brand" | "gain" | "loss" | "hold" | "tool";

const TONES: Record<Tone, { fill: string; stroke: string; accent: string }> = {
  plain: { fill: "var(--surface)", stroke: "var(--rule-2)", accent: "var(--ink-3)" },
  brand: { fill: "var(--accent-soft)", stroke: "var(--accent-line)", accent: "var(--accent)" },
  gain: { fill: "var(--gain-soft)", stroke: "var(--gain-line)", accent: "var(--gain)" },
  loss: { fill: "var(--loss-soft)", stroke: "var(--loss-line)", accent: "var(--loss)" },
  hold: { fill: "var(--hold-soft)", stroke: "var(--hold-line)", accent: "var(--hold)" },
  tool: { fill: "var(--tool-soft)", stroke: "var(--tool-line)", accent: "var(--tool)" },
};

function Defs() {
  return (
    <defs>
      <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 z" fill={INK3} />
      </marker>
      <marker id="arb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 z" fill="var(--accent)" />
      </marker>
      <linearGradient id="brandgrad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="var(--accent)" />
        <stop offset="100%" stopColor="var(--accent-2)" />
      </linearGradient>
    </defs>
  );
}

function Node({
  x, y, w, h, step, title, lines = [], tone = "plain",
}: {
  x: number; y: number; w: number; h: number;
  step?: string; title: string; lines?: string[]; tone?: Tone;
}) {
  const t = TONES[tone];
  const top = y + (step ? 34 : 26);
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={13} fill={t.fill} stroke={t.stroke} strokeWidth={1.4} />
      <rect x={x} y={y} width={4} height={h} rx={2} fill={t.accent} />
      {step && (
        <text x={x + 16} y={y + 21} fill={t.accent} fontSize={10.5} fontWeight={700} letterSpacing=".1em" fontFamily="var(--mono)">
          {step}
        </text>
      )}
      <text x={x + 16} y={top} fill={INK} fontSize={14} fontWeight={650} letterSpacing="-.01em">{title}</text>
      {lines.map((line, i) => (
        <text key={line} x={x + 16} y={top + 20 + i * 16} fill={INK2} fontSize={11.5}>{line}</text>
      ))}
    </g>
  );
}

function Arrow({ d, label, brand = false, dashed = false }: { d: string; label?: string; brand?: boolean; dashed?: boolean }) {
  return (
    <g>
      <path
        d={d}
        fill="none"
        stroke={brand ? "var(--accent)" : RULE}
        strokeWidth={1.6}
        markerEnd={brand ? "url(#arb)" : "url(#ar)"}
        strokeDasharray={dashed ? "5 5" : undefined}
      />
      {label && (
        <text
          x={Number(d.split(" ")[1]) + 8}
          y={Number(d.split(" ")[2]) - 8}
          fill={INK3}
          fontSize={10.5}
          fontFamily="var(--mono)"
        >
          {label}
        </text>
      )}
    </g>
  );
}

function Lane({ x, y, w, h, label, tone = "plain" }: { x: number; y: number; w: number; h: number; label: string; tone?: Tone }) {
  const t = TONES[tone];
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={16} fill="none" stroke={t.stroke} strokeWidth={1.2} strokeDasharray="7 6" opacity={0.85} />
      <text x={x + 16} y={y + 20} fill={t.accent} fontSize={10.5} fontWeight={700} letterSpacing=".12em" fontFamily="var(--mono)">
        {label}
      </text>
    </g>
  );
}

/* ── 1. The loop: three engines, one cycle ─────────────────────────────── */
export function LoopDiagram() {
  return (
    <div className="figure">
      <svg viewBox="0 0 1120 470" role="img" aria-label="Evaluation, improvement and release as three separate engines feeding one cycle">
        <Defs />
        <Lane x={16} y={54} w={336} h={300} label="ENGINE 1 · MEASURE" tone="brand" />
        <Lane x={392} y={54} w={336} h={300} label="ENGINE 2 · IMPROVE" tone="hold" />
        <Lane x={768} y={54} w={336} h={300} label="ENGINE 3 · RELEASE" tone="gain" />

        <Node x={40} y={92} w={288} h={104} step="INPUT" title="Scenario contract" tone="plain"
          lines={["Hidden caller goal + persona", "Seeded account state", "Required + forbidden actions"]} />
        <Node x={40} y={220} w={288} h={110} step="RUN + SCORE" title="Executed episode" tone="brand"
          lines={["Validity checked before scoring", "Deterministic truth before judges", "First break + owning component"]} />

        <Node x={416} y={92} w={288} h={104} step="ROUTE" title="Failure packet" tone="plain"
          lines={["Evidence turn, verbatim", "Severity + owning component", "Becomes a permanent test"]} />
        <Node x={416} y={220} w={288} h={110} step="REPAIR" title="Competing candidates" tone="hold"
          lines={["Optimiser · manual · control arm", "Versioned diff + hypothesis", "Losers retained as evidence"]} />

        <Node x={792} y={92} w={288} h={104} step="COMPARE" title="Frozen per-case gate" tone="plain"
          lines={["Same suite, same evaluator hash", "No severe regression averaged away", "Sealed test opened once"]} />
        <Node x={792} y={220} w={288} h={110} step="DECIDE" title="Promote · hold · roll back" tone="gain"
          lines={["A human signs the release", "Published whichever way it lands"]} />

        <Arrow d="M 184 196 L 184 220" />
        <Arrow d="M 328 275 L 416 144" brand label="failures" />
        <Arrow d="M 560 196 L 560 220" />
        <Arrow d="M 704 275 L 792 144" brand label="candidate" />
        <Arrow d="M 936 196 L 936 220" />

        {/* the cycle closing back */}
        <Arrow d="M 936 330 L 936 400 L 184 400 L 184 358" dashed label="a promoted agent re-enters the same suite" />

        <text x={560} y={442} fill={INK3} fontSize={11.5} textAnchor="middle" fontFamily="var(--mono)">
          the evaluator cannot edit the agent · the improver cannot approve itself
        </text>
      </svg>
    </div>
  );
}

/* ── 2. Inside one episode: say-versus-do ──────────────────────────────── */
export function EvaluationDiagram() {
  return (
    <div className="figure">
      <svg viewBox="0 0 1120 430" role="img" aria-label="How one conversation becomes a score">
        <Defs />
        <Node x={24} y={40} w={250} h={96} step="1" title="Simulated caller" tone="plain"
          lines={["Hidden goal, never revealed", "Persona drives difficulty"]} />
        <Node x={24} y={168} w={250} h={96} step="2" title="Agent under test" tone="brand"
          lines={["The prompt being measured", "Four tools available"]} />
        <Node x={24} y={296} w={250} h={96} step="3" title="Isolated environment" tone="tool"
          lines={["Fresh database per trial", "Append-only tool log"]} />

        <Node x={352} y={140} w={266} h={152} step="ARTIFACT" title="Preserved episode" tone="plain"
          lines={["Transcript, turn by turn", "Tool calls with arguments", "State before and after", "Per-turn latency"]} />

        <Node x={696} y={30} w={400} h={78} step="GATE 0" title="Was this trial fair to score?" tone="hold"
          lines={["Simulator off-policy or unterminated → excluded, not failed"]} />
        <Node x={696} y={132} w={400} h={96} step="DECIDES THE GATE" title="Deterministic truth" tone="gain"
          lines={["Outcome · state · required tool calls · guardrails", "Say-versus-do: a claim is not an effect"]} />
        <Node x={696} y={252} w={400} h={72} step="ADVISORY ONLY" title="Semantic judge" tone="plain"
          lines={["Scores what code cannot. Never reaches the gate."]} />
        <Node x={696} y={348} w={400} h={62} title="First break + owner" tone="brand"
          lines={["Earliest turn after which the right outcome was impossible"]} />

        <Arrow d="M 274 88 L 352 200" />
        <Arrow d="M 274 216 L 352 216" brand />
        <Arrow d="M 274 344 L 352 232" />
        <Arrow d="M 618 190 L 696 69" />
        <Arrow d="M 618 210 L 696 180" brand />
        <Arrow d="M 618 226 L 696 288" dashed />
        <Arrow d="M 896 228 L 896 252" />
        <Arrow d="M 896 324 L 896 348" />
      </svg>
    </div>
  );
}

/* ── 3. Improvement: evidence chooses the repair surface ───────────────── */
export function ImprovementDiagram() {
  return (
    <div className="figure">
      <svg viewBox="0 0 1120 400" role="img" aria-label="How a failure becomes a gated candidate">
        <Defs />
        <Node x={24} y={130} w={244} h={128} step="INPUT" title="Failure packets" tone="loss"
          lines={["Grouped into families", "Ranked by severity", "Each carries its evidence turn"]} />

        <Node x={318} y={130} w={230} h={128} step="ROUTER" title="Pick the surface" tone="brand"
          lines={["Reads the owner,", "not the symptom.", "Opens exactly one."]} />

        <Node x={604} y={24} w={228} h={62} title="Prompt" tone="plain" lines={["optimiser or manual"]} />
        <Node x={604} y={104} w={228} h={62} title="Extractor" tone="plain" lines={["output schema"]} />
        <Node x={604} y={184} w={228} h={62} title="Tool" tone="tool" lines={["contract or arguments"]} />
        <Node x={604} y={264} w={228} h={62} title="Workflow · policy" tone="plain" lines={["runtime state"]} />

        <Node x={884} y={130} w={212} h={128} step="OUTPUT" title="Gated candidate" tone="hold"
          lines={["Exact diff + hash", "Stated hypothesis", "Faces the frozen gate"]} />

        <Arrow d="M 268 194 L 318 194" brand />
        <Arrow d="M 548 170 L 604 55" />
        <Arrow d="M 548 185 L 604 135" />
        <Arrow d="M 548 200 L 604 215" brand />
        <Arrow d="M 548 218 L 604 295" />
        <Arrow d="M 832 55 L 884 165" />
        <Arrow d="M 832 135 L 884 180" />
        <Arrow d="M 832 215 L 884 200" brand />
        <Arrow d="M 832 295 L 884 220" />

        <text x={560} y={372} fill={INK3} fontSize={11.5} textAnchor="middle" fontFamily="var(--mono)">
          a prompt rewrite cannot fix a broken tool contract — so the evidence picks the surface
        </text>
      </svg>
    </div>
  );
}

/* ── 4. Three tiers of evidence ────────────────────────────────────────── */
export function TiersDiagram() {
  return (
    <div className="figure">
      <svg viewBox="0 0 1120 300" role="img" aria-label="Three evidence tiers measured the same way">
        <Defs />
        <Node x={24} y={40} w={330} h={150} step="TIER 1 · TEXT" title="Synthetic conversations" tone="brand"
          lines={["Families x languages x variants", "Cheap, reproducible, large n", "Optimiser learns here — dev split only"]} />
        <Node x={396} y={40} w={330} h={150} step="TIER 2 · HUMAN" title="Calls you record yourself" tone="hold"
          lines={["Real speech, real improvisation", "Owner-confirmed labels", "Tool effects checked in the journal"]} />
        <Node x={768} y={40} w={330} h={150} step="TIER 3 · VOICE" title="Bot-to-bot, duplex audio" tone="gain"
          lines={["Full EVA accuracy + experience set", "Audio-only metrics finally scorable", "Matched arms, identical records"]} />

        <rect x={24} y={222} width={1074} height={52} rx={13} fill="var(--sunken)" stroke={RULE} strokeWidth={1.2} />
        <text x={561} y={244} fill={INK} fontSize={13} fontWeight={650} textAnchor="middle">
          One evaluator hash. One set of rules. Every tier measured identically before and after.
        </text>
        <text x={561} y={263} fill={INK3} fontSize={11} textAnchor="middle" fontFamily="var(--mono)">
          the headline never comes from data the optimiser was allowed to see
        </text>
        <Arrow d="M 189 190 L 189 222" />
        <Arrow d="M 561 190 L 561 222" brand />
        <Arrow d="M 933 190 L 933 222" />
      </svg>
    </div>
  );
}

/* ── 5. Production substrate ───────────────────────────────────────────── */
export function ProductionDiagram() {
  return (
    <div className="figure">
      <svg viewBox="0 0 1120 340" role="img" aria-label="What exists today versus what production needs">
        <Defs />
        <Lane x={16} y={30} w={532} h={280} label="BUILT — PROVEN AT MVP SCALE" tone="gain" />
        <Lane x={576} y={30} w={528} h={280} label="MUST BE BUILT FOR PRODUCTION" tone="hold" />

        <Node x={40} y={68} w={228} h={70} title="Scenario contracts" tone="gain" lines={["One pack per domain"]} />
        <Node x={296} y={68} w={228} h={70} title="Executable verifiers" tone="gain" lines={["State, tools, guardrails"]} />
        <Node x={40} y={158} w={228} h={70} title="First break + routing" tone="gain" lines={["Failure to owner"]} />
        <Node x={296} y={158} w={228} h={70} title="Repair arms" tone="gain" lines={["Optimiser, manual, memory"]} />
        <Node x={40} y={248} w={484} h={44} title="Per-case release gate — promote, hold, roll back" tone="gain" />

        <Node x={600} y={68} w={228} h={70} title="Ingestion + redaction" tone="hold" lines={["Strip PII at volume"]} />
        <Node x={856} y={68} w={228} h={70} title="Outcome join" tone="hold" lines={["Ledger — proxy to truth"]} />
        <Node x={600} y={158} w={228} h={70} title="Sampling + human review" tone="hold" lines={["Keeps the grader honest"]} />
        <Node x={856} y={158} w={228} h={70} title="Canary + rollback" tone="hold" lines={["Automatic revert"]} />
        <Node x={600} y={248} w={484} h={44} title="Drift monitors · registries · residency and access controls" tone="hold" />
      </svg>
    </div>
  );
}
