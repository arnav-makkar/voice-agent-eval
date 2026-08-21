"use client";

/* Schematics.
   Real technical diagrams: numbered stages, typed edges, decision points and
   parallel arms — the mechanism, not a decoration. Drawn on a fixed viewBox
   grid with theme tokens, so both appearances work and nothing overlaps.
   Surfaces carry the same soft relief as the rest of the page via an SVG
   filter, so the schematics read as pressed into the same material. */

const INK = "var(--ink)";
const INK2 = "var(--ink-2)";
const INK3 = "var(--ink-3)";
const EDGE = "var(--rule-2)";

type Tone = "plain" | "accent" | "gain" | "hold" | "tool" | "loss";

const FILL: Record<Tone, string> = {
  plain: "var(--surface)",
  accent: "var(--accent-soft)",
  gain: "var(--gain-soft)",
  hold: "var(--hold-soft)",
  tool: "var(--tool-soft)",
  loss: "var(--loss-soft)",
};
const STROKE: Record<Tone, string> = {
  plain: "var(--rule-2)",
  accent: "var(--accent-line)",
  gain: "var(--gain-line)",
  hold: "var(--hold-line)",
  tool: "var(--tool-line)",
  loss: "var(--loss-line)",
};
const HUE: Record<Tone, string> = {
  plain: "var(--ink-3)",
  accent: "var(--accent)",
  gain: "var(--gain)",
  hold: "var(--hold)",
  tool: "var(--tool)",
  loss: "var(--loss)",
};

function Defs() {
  return (
    <defs>
      <filter id="relief" x="-25%" y="-25%" width="150%" height="150%">
        <feDropShadow dx="3" dy="4" stdDeviation="4" floodColor="var(--hi)" floodOpacity="1" />
        <feDropShadow dx="-3" dy="-3" stdDeviation="4" floodColor="var(--lo)" floodOpacity="1" />
      </filter>
      <marker id="a-n" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 z" fill={INK3} />
      </marker>
      <marker id="a-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 z" fill="var(--accent)" />
      </marker>
    </defs>
  );
}

/** A process box: number, title, and the detail that gives it depth. */
function Box({
  x, y, w, h, n, title, lines = [], tone = "plain",
}: { x: number; y: number; w: number; h: number; n?: string; title: string; lines?: string[]; tone?: Tone }) {
  const titleY = y + (n ? 36 : 27);
  return (
    <g filter="url(#relief)">
      <rect x={x} y={y} width={w} height={h} rx={14} fill={FILL[tone]} stroke={STROKE[tone]} strokeWidth={1.25} />
      {n && (
        <>
          <circle cx={x + 27} cy={y + 25} r={11} fill="var(--paper)" stroke={STROKE[tone]} strokeWidth={1.1} />
          <text x={x + 27} y={y + 29} fill={HUE[tone]} fontSize={10.5} fontWeight={700} textAnchor="middle" fontFamily="var(--mono)">{n}</text>
        </>
      )}
      <text x={n ? x + 46 : x + 17} y={n ? y + 29 : titleY} fill={INK} fontSize={13.5} fontWeight={600} letterSpacing="-.015em">{title}</text>
      {lines.map((l, i) => (
        <text key={l} x={x + 17} y={(n ? y + 54 : titleY + 21) + i * 16} fill={INK2} fontSize={11.5}>{l}</text>
      ))}
    </g>
  );
}

/** A decision point. Diamonds are what make a flowchart a flowchart. */
function Decision({ cx, cy, w, h, label, sub }: { cx: number; cy: number; w: number; h: number; label: string; sub?: string }) {
  return (
    <g filter="url(#relief)">
      <path
        d={`M ${cx} ${cy - h / 2} L ${cx + w / 2} ${cy} L ${cx} ${cy + h / 2} L ${cx - w / 2} ${cy} Z`}
        fill="var(--hold-soft)" stroke="var(--hold-line)" strokeWidth={1.25}
      />
      <text x={cx} y={sub ? cy - 2 : cy + 4} fill={INK} fontSize={12} fontWeight={600} textAnchor="middle">{label}</text>
      {sub && <text x={cx} y={cy + 15} fill={INK3} fontSize={10} textAnchor="middle" fontFamily="var(--mono)">{sub}</text>}
    </g>
  );
}

function Edge({ d, label, accent = false, dashed = false, lx, ly }: { d: string; label?: string; accent?: boolean; dashed?: boolean; lx?: number; ly?: number }) {
  return (
    <g>
      <path d={d} fill="none" stroke={accent ? "var(--accent)" : EDGE} strokeWidth={1.6}
        markerEnd={accent ? "url(#a-a)" : "url(#a-n)"} strokeDasharray={dashed ? "5 5" : undefined} />
      {label && lx !== undefined && ly !== undefined && (
        <text x={lx} y={ly} fill={INK3} fontSize={10} textAnchor="middle" fontFamily="var(--mono)" letterSpacing=".04em">{label}</text>
      )}
    </g>
  );
}

function Zone({ x, y, w, h, label, tone = "plain" }: { x: number; y: number; w: number; h: number; label: string; tone?: Tone }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={20} fill="none" stroke={STROKE[tone]} strokeWidth={1.1} strokeDasharray="6 7" opacity={0.9} />
      <text x={x + 18} y={y + 21} fill={HUE[tone]} fontSize={10} fontWeight={700} letterSpacing=".16em" fontFamily="var(--mono)">{label}</text>
    </g>
  );
}

function Figure({ children, note, vb }: { children: React.ReactNode; note?: string; vb: string }) {
  return (
    <>
      <div className="figure">
        <svg viewBox={vb} role="img">{children}</svg>
      </div>
      {note && <p className="figure-note">{note}</p>}
    </>
  );
}

/* ── 1 · Three engines, one governed cycle ─────────────────────────────── */
export function LoopDiagram() {
  return (
    <Figure vb="0 0 1140 500"
      note="Three responsibilities that never merge. The evaluator cannot edit the agent, the improver cannot approve itself, and a third component decides. A promoted agent re-enters the identical suite next cycle.">
      <Defs />
      <Zone x={14} y={44} w={344} h={330} label="01 · EVALUATION ENGINE" tone="accent" />
      <Zone x={398} y={44} w={344} h={330} label="02 · IMPROVEMENT ENGINE" tone="hold" />
      <Zone x={782} y={44} w={344} h={330} label="03 · RELEASE CONTROLLER" tone="gain" />

      <Box x={38} y={78} w={296} h={104} n="1" title="Scenario contract"
        lines={["Hidden caller goal + persona", "Seeded account state", "Required / forbidden actions"]} />
      <Box x={38} y={210} w={296} h={140} n="2" title="Execute + score" tone="accent"
        lines={["Simulated caller ⇄ agent", "Isolated tools and state", "Validity → deterministic truth", "First break + owning component"]} />

      <Box x={422} y={78} w={296} h={104} n="3" title="Failure packet"
        lines={["Evidence turn, verbatim", "Severity + owning component", "Becomes a permanent test"]} />
      <Box x={422} y={210} w={296} h={140} n="4" title="Bounded repair arms" tone="hold"
        lines={["Optimiser (GEPA)", "Manual repair", "No-diagnosis control", "Versioned diff + hypothesis"]} />

      <Box x={806} y={78} w={296} h={104} n="5" title="Frozen per-case gate"
        lines={["Same suite, same evaluator hash", "No severe regression averaged away"]} />
      <Box x={806} y={210} w={296} h={140} n="6" title="Promote · hold · roll back" tone="gain"
        lines={["Sealed test opened once", "Human signs the release", "Published whichever way it lands"]} />

      <Edge d="M 186 182 L 186 210" />
      <Edge d="M 334 280 L 422 130" accent label="failures" lx={392} ly={196} />
      <Edge d="M 570 182 L 570 210" />
      <Edge d="M 718 280 L 806 130" accent label="candidate" lx={776} ly={196} />
      <Edge d="M 954 182 L 954 210" />
      <Edge d="M 954 350 L 954 420 L 186 420 L 186 350" dashed label="promoted agent re-enters the same suite" lx={570} ly={412} />

      <text x={570} y={468} fill={INK3} fontSize={11} textAnchor="middle" fontFamily="var(--mono)" letterSpacing=".05em">
        MEASUREMENT CANNOT EDIT · IMPROVEMENT CANNOT APPROVE · RELEASE DECIDES
      </text>
    </Figure>
  );
}

/* ── 2 · One episode → one score, with the validity gate ───────────────── */
export function EvaluationDiagram() {
  return (
    <Figure vb="0 0 1140 520"
      note="Validity is checked before anything is graded, so a broken trial is excluded rather than counted as an agent failure. Executable truth decides the gate; the semantic judge runs in a separate pass and never reaches it.">
      <Defs />
      <Box x={24} y={40} w={244} h={92} n="1" title="Simulated caller"
        lines={["Hidden goal", "Persona sets difficulty"]} />
      <Box x={24} y={158} w={244} h={92} n="2" title="Agent under test" tone="accent"
        lines={["The prompt being measured", "Four tools offered"]} />
      <Box x={24} y={276} w={244} h={92} n="3" title="Isolated environment" tone="tool"
        lines={["Fresh database per trial", "Append-only tool log"]} />

      <Box x={332} y={148} w={252} h={132} title="Preserved episode"
        lines={["Transcript, turn by turn", "Tool calls + arguments", "State before / after", "Per-turn latency"]} />

      <Decision cx={716} cy={214} w={188} h={104} label="Fair to score?" sub="GATE 0" />

      <Box x={856} y={40} w={260} h={80} title="Excluded" tone="loss"
        lines={["Off-policy or unterminated —", "never counted as failure"]} />

      <Box x={856} y={160} w={260} h={116} title="Deterministic truth" tone="gain"
        lines={["Outcome · state · required calls", "Guardrails · disclosures", "Decides the gate"]} />
      <Box x={856} y={302} w={260} h={80} title="Semantic judge"
        lines={["Advisory only — separate pass,", "never reaches the gate"]} />
      <Box x={332} y={404} w={784} h={72} title="First break + owning component" tone="accent"
        lines={["The earliest turn after which the correct outcome had become impossible, routed to prompt / extractor / tool / workflow / policy"]} />

      <Edge d="M 268 86 L 332 190" />
      <Edge d="M 268 204 L 332 210" accent />
      <Edge d="M 268 322 L 332 250" />
      <Edge d="M 584 214 L 622 214" accent />
      <Edge d="M 760 176 L 856 92" label="invalid" lx={812} ly={124} />
      <Edge d="M 810 214 L 856 214" accent label="valid" lx={833} ly={205} />
      <Edge d="M 986 276 L 986 302" dashed />
      <Edge d="M 986 382 L 986 404" />
      <Edge d="M 458 280 L 458 404" />
    </Figure>
  );
}

/* ── 3 · Repair routing: evidence chooses the surface ──────────────────── */
export function ImprovementDiagram() {
  return (
    <Figure vb="0 0 1140 460"
      note="The router reads the owner, not the symptom, and opens exactly one repair surface. A prompt rewrite cannot fix a broken tool contract, so a mis-routed repair is worse than none."
    >
      <Defs />
      <Box x={24} y={158} w={228} h={124} n="1" title="Failure packets" tone="loss"
        lines={["Grouped into families", "Ranked by severity", "Carry their evidence turn"]} />

      <Decision cx={392} cy={220} w={210} h={120} label="Who owns it?" sub="ROUTER" />

      <Box x={540} y={30} w={252} h={64} title="Prompt" lines={["optimiser or manual repair"]} />
      <Box x={540} y={112} w={252} h={64} title="Extractor" lines={["output schema"]} />
      <Box x={540} y={194} w={252} h={64} title="Tool" tone="tool" lines={["contract or arguments"]} />
      <Box x={540} y={276} w={252} h={64} title="Workflow / policy" lines={["explicit runtime state"]} />
      <Box x={540} y={358} w={252} h={64} title="Model / runtime" lines={["escalated, not patched"]} />

      <Box x={856} y={158} w={260} h={124} n="2" title="Gated candidate" tone="hold"
        lines={["Exact diff + prompt hash", "Stated hypothesis", "Faces the frozen gate"]} />

      <Edge d="M 252 220 L 287 220" accent />
      <Edge d="M 470 196 L 540 62" />
      <Edge d="M 480 208 L 540 144" />
      <Edge d="M 497 220 L 540 226" accent />
      <Edge d="M 480 232 L 540 308" />
      <Edge d="M 470 244 L 540 390" />
      <Edge d="M 792 62 L 856 190" />
      <Edge d="M 792 144 L 856 206" />
      <Edge d="M 792 226 L 856 220" accent />
      <Edge d="M 792 308 L 856 234" />
      <Edge d="M 792 390 L 856 250" />
      <text x={392} y={330} fill={INK3} fontSize={10} textAnchor="middle" fontFamily="var(--mono)" letterSpacing=".08em">
        EXACTLY ONE SURFACE OPENS
      </text>
    </Figure>
  );
}

/* ── 4 · Three evidence tiers, one contract ────────────────────────────── */
export function TiersDiagram() {
  return (
    <Figure vb="0 0 1140 360"
      note="Each tier answers a different question and keeps its own denominator. The headline never comes from data the optimiser was allowed to see.">
      <Defs />
      <Box x={24} y={44} w={334} h={152} n="T1" title="Synthetic text" tone="accent"
        lines={["Families × languages × variants", "Cheap, reproducible, large n", "Optimiser learns here —", "development split only"]} />
      <Box x={402} y={44} w={334} h={152} n="T2" title="Calls you record" tone="hold"
        lines={["Real speech, real improvisation", "Owner-confirmed labels", "Tool effects checked against", "the append-only journal"]} />
      <Box x={780} y={44} w={336} h={152} n="T3" title="Bot-to-bot voice" tone="gain"
        lines={["Duplex audio, matched arms", "Audio-only metrics scorable", "Identical records both arms"]} />

      <Box x={24} y={252} w={1092} h={68} title="One evaluator hash · one set of rules · measured identically before and after"
        lines={["Blind splits and the sealed test are authored before any candidate exists, so the headline cannot be tuned"]} />

      <Edge d="M 191 196 L 191 252" />
      <Edge d="M 569 196 L 569 252" accent />
      <Edge d="M 948 196 L 948 252" />
    </Figure>
  );
}

/* ── 5 · Production substrate ──────────────────────────────────────────── */
export function ProductionDiagram() {
  return (
    <Figure vb="0 0 1140 420"
      note="The control loop is domain-independent and transfers as it is. The substrate around it does not exist yet at production scale, and pretending otherwise is how evaluation projects die in month two."
    >
      <Defs />
      <Zone x={14} y={30} w={544} h={360} label="BUILT · PROVEN AT MVP SCALE" tone="gain" />
      <Zone x={586} y={30} w={540} h={360} label="MUST BE BUILT FOR PRODUCTION" tone="hold" />

      <Box x={38} y={70} w={232} h={76} title="Scenario contracts" tone="gain" lines={["One pack per domain"]} />
      <Box x={302} y={70} w={232} h={76} title="Executable verifiers" tone="gain" lines={["State, tools, guardrails"]} />
      <Box x={38} y={168} w={232} h={76} title="First break + routing" tone="gain" lines={["Failure to owner"]} />
      <Box x={302} y={168} w={232} h={76} title="Repair arms" tone="gain" lines={["Optimiser, manual, memory"]} />
      <Box x={38} y={266} w={496} h={68} title="Per-case release gate" tone="gain" lines={["Promote · hold · roll back, with a human in the loop"]} />

      <Box x={610} y={70} w={232} h={76} title="Ingestion + redaction" tone="hold" lines={["Strip PII at volume"]} />
      <Box x={874} y={70} w={232} h={76} title="Outcome join" tone="hold" lines={["Ledger — proxy to truth"]} />
      <Box x={610} y={168} w={232} h={76} title="Sampling + review" tone="hold" lines={["Keeps the grader honest"]} />
      <Box x={874} y={168} w={232} h={76} title="Canary + rollback" tone="hold" lines={["Automatic revert"]} />
      <Box x={610} y={266} w={496} h={68} title="Drift monitors · registries · residency and access controls" tone="hold"
        lines={["Alert when the population moves away from the suite"]} />

      <Edge d="M 558 202 L 586 202" dashed />
    </Figure>
  );
}
