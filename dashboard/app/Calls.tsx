"use client";

import { useState } from "react";

/*
 * The call browser: every recorded and bot-to-bot call, inspectable per arm.
 * Modeled on the EVA demo page — full tool catalogue with unused tools kept
 * visible, and per-metric rows that expand into how the score was produced.
 * Data comes from the campaign-2 preview file until the real campaign runs.
 */

type MetricCell = { score: number | null; by: string; note: string };
type MetricGroups = Record<string, Record<string, MetricCell>>;
type Turn = { who: string; text: string };
type Arm = {
  task: boolean;
  grounded: boolean;
  used_tools: string[];
  metrics: MetricGroups;
  transcript: Turn[];
  note: string;
};
export type Call = {
  id: string;
  tier: "recorded" | "live";
  family: string;
  title: string;
  language: string;
  goal: string;
  tools: Array<{ name: string; kind: string; required: boolean }>;
  arms: { base: Arm; improved: Arm };
};
export type CallsData = {
  placeholder: boolean;
  banner: string;
  tiers: Record<string, { label: string; n: number }>;
  totals: Record<string, { task: number[]; grounded: number[] }>;
  calls: Call[];
};

const GROUP_LABELS: Record<string, string> = {
  eva_a: "Accuracy (EVA-A)",
  eva_x: "Experience (EVA-X)",
  validation: "Validation",
  diagnostic: "Diagnostic",
};
const BY_LABELS: Record<string, string> = {
  deterministic: "Deterministic",
  llm_judge: "LLM judge",
  audio_judge: "Audio judge",
};

const words = (value: string) => value.replaceAll("_", " ");
const pct = (cell?: MetricCell) => (cell && cell.score !== null ? `${Math.round(cell.score * 100)}%` : "—");
const tone = (cell?: MetricCell) =>
  !cell || cell.score === null ? "dim" : cell.score >= 0.7 ? "gain" : cell.score >= 0.4 ? "hold" : "loss";

function MetricRow({ name, base, improved }: { name: string; base?: MetricCell; improved?: MetricCell }) {
  const [open, setOpen] = useState(false);
  const by = improved?.by ?? base?.by ?? "";
  return (
    <div className="mrow">
      <button className="mrow-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="mname">{words(name)}</span>
        <span className="mby">{BY_LABELS[by] ?? by}</span>
        <span className={`mpill ${tone(base)}`}>{pct(base)}</span>
        <span className="marrow">→</span>
        <span className={`mpill ${tone(improved)}`}>{pct(improved)}</span>
        <span className={`chev ${open ? "open" : ""}`}>⌄</span>
      </button>
      {open && (
        <div className="mrow-body">
          <p><b>Original:</b> {base?.note ?? "—"}</p>
          <p><b>Improved:</b> {improved?.note ?? "—"}</p>
        </div>
      )}
    </div>
  );
}

function ToolsPanel({ call }: { call: Call }) {
  return (
    <div className="toolpanel">
      <p className="eyebrow" style={{ marginBottom: 12 }}>
        Agent tools · full catalogue — unused tools stay listed, that is the rubric
      </p>
      {call.tools.map((tool) => {
        const inBase = call.arms.base.used_tools.includes(tool.name);
        const inImproved = call.arms.improved.used_tools.includes(tool.name);
        const used = inBase || inImproved;
        return (
          <div className={`toolrow ${used ? "used" : "idle"}`} key={tool.name}>
            <span className="tname mono">{tool.name}</span>
            <span className={`tkind ${tool.kind}`}>{tool.kind}</span>
            {tool.required && <span className="treq">required</span>}
            <span className="tarms">
              <i className={inBase ? "on" : ""}>original</i>
              <i className={inImproved ? "on" : ""}>improved</i>
            </span>
          </div>
        );
      })}
    </div>
  );
}

function CallDetail({ call }: { call: Call }) {
  return (
    <div className="calldetail">
      <div className="calldetail-grid">
        <div>
          <p className="eyebrow" style={{ marginBottom: 10 }}>Scenario briefing</p>
          <p className="body" style={{ fontSize: 14.5 }}>{call.goal}</p>
          <div className="armnotes">
            <div>
              <span className="pill loss">original</span>
              <p>{call.arms.base.note}</p>
              {call.arms.base.transcript.map((turn, index) => (
                <p className="snip" key={index}><b>{turn.who}:</b> {turn.text}</p>
              ))}
            </div>
            <div>
              <span className="pill gain">improved</span>
              <p>{call.arms.improved.note}</p>
              {call.arms.improved.transcript.map((turn, index) => (
                <p className="snip" key={index}><b>{turn.who}:</b> {turn.text}</p>
              ))}
            </div>
          </div>
          <p className="fine" style={{ marginTop: 14 }}>
            Audio, full transcript and the append-only tool journal attach here when the call actually runs.
          </p>
        </div>
        <ToolsPanel call={call} />
      </div>

      <div className="metricsets">
        {Object.keys(GROUP_LABELS).map((group) => {
          const base = call.arms.base.metrics[group] ?? {};
          const improved = call.arms.improved.metrics[group] ?? {};
          const names = Object.keys({ ...base, ...improved });
          if (!names.length) return null;
          return (
            <div key={group}>
              <p className="msection">{GROUP_LABELS[group]}</p>
              {names.map((name) => (
                <MetricRow key={name} name={name} base={base[name]} improved={improved[name]} />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function CallsBrowser({ data }: { data: CallsData }) {
  const [tier, setTier] = useState<"all" | "recorded" | "live">("all");
  const [openId, setOpenId] = useState<string | null>(null);
  const calls = data.calls.filter((call) => tier === "all" || call.tier === tier);
  return (
    <div>
      <div className="callfilters">
        {(["all", "recorded", "live"] as const).map((value) => (
          <button key={value} className={`fchip ${tier === value ? "on" : ""}`} onClick={() => { setTier(value); setOpenId(null); }}>
            {value === "all" ? `All 30 calls` : `${data.tiers[value].label} · ${data.tiers[value].n}`}
          </button>
        ))}
      </div>
      <div className="callgrid">
        {calls.map((call) => (
          <div key={call.id} className={`callcard ${openId === call.id ? "open" : ""}`}>
            <button className="callcard-head" onClick={() => setOpenId(openId === call.id ? null : call.id)} aria-expanded={openId === call.id}>
              <span className="cid mono">{call.id}</span>
              <span className="ctitle">{call.title}</span>
              <span className="clang">{call.language}</span>
              <span className={`cpill ${call.arms.base.task ? "gain" : "loss"}`}>orig {call.arms.base.task ? "pass" : "fail"}</span>
              <span className={`cpill ${call.arms.improved.task ? "gain" : "loss"}`}>impr {call.arms.improved.task ? "pass" : "fail"}</span>
              <span className={`cpill ${call.arms.improved.grounded ? "gain" : "hold"}`}>{call.arms.improved.grounded ? "grounded" : "ungrounded"}</span>
            </button>
            {openId === call.id && <CallDetail call={call} />}
          </div>
        ))}
      </div>
    </div>
  );
}

/* EVA-A × EVA-X scatter over the bot-to-bot calls, one dot per call per arm. */
export function ComparisonScatter({ data }: { data: CallsData }) {
  const live = data.calls.filter((call) => call.tier === "live");
  const mean = (cells: Record<string, MetricCell>) => {
    const values = Object.values(cells).map((cell) => cell.score).filter((score): score is number => score !== null);
    return values.length ? values.reduce((sum, score) => sum + score, 0) / values.length : 0;
  };
  const points = live.flatMap((call) =>
    (["base", "improved"] as const).map((arm) => ({
      arm,
      id: call.id,
      x: mean(call.arms[arm].metrics.eva_a ?? {}),
      y: mean(call.arms[arm].metrics.eva_x ?? {}),
    })),
  );
  const width = 640, height = 420, pad = 46;
  const sx = (value: number) => pad + value * (width - pad - 18);
  const sy = (value: number) => height - pad - value * (height - pad - 20);
  const grid = [0, 0.2, 0.4, 0.6, 0.8, 1];
  const centroid = (arm: "base" | "improved") => {
    const mine = points.filter((point) => point.arm === arm);
    return {
      x: mine.reduce((sum, point) => sum + point.x, 0) / mine.length,
      y: mine.reduce((sum, point) => sum + point.y, 0) / mine.length,
    };
  };
  const cb = centroid("base"), ci = centroid("improved");
  return (
    <div className="scatterwrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Accuracy versus experience, one dot per bot-to-bot call per arm">
        {grid.map((value) => (
          <g key={value}>
            <line x1={sx(value)} y1={sy(0)} x2={sx(value)} y2={sy(1)} className="gridline" />
            <line x1={sx(0)} y1={sy(value)} x2={sx(1)} y2={sy(value)} className="gridline" />
            <text x={sx(value)} y={height - pad + 18} className="tick" textAnchor="middle">{value.toFixed(1)}</text>
            <text x={pad - 10} y={sy(value) + 4} className="tick" textAnchor="end">{value.toFixed(1)}</text>
          </g>
        ))}
        <line x1={sx(cb.x)} y1={sy(cb.y)} x2={sx(ci.x)} y2={sy(ci.y)} className="shiftline" />
        {points.map((point) => (
          <circle key={`${point.id}-${point.arm}`} cx={sx(point.x)} cy={sy(point.y)} r={5.5} className={`dot ${point.arm}`}>
            <title>{`${point.id} · ${point.arm} · EVA-A ${point.x.toFixed(2)} · EVA-X ${point.y.toFixed(2)}`}</title>
          </circle>
        ))}
        <rect x={sx(cb.x) - 7} y={sy(cb.y) - 7} width={14} height={14} className="cent base" transform={`rotate(45 ${sx(cb.x)} ${sy(cb.y)})`} />
        <rect x={sx(ci.x) - 7} y={sy(ci.y) - 7} width={14} height={14} className="cent improved" transform={`rotate(45 ${sx(ci.x)} ${sy(ci.y)})`} />
        <text x={(width + pad) / 2} y={height - 8} className="axis" textAnchor="middle">Accuracy (EVA-A, per-call mean)</text>
        <text x={14} y={(height - pad) / 2} className="axis" transform={`rotate(-90 14 ${(height - pad) / 2})`} textAnchor="middle">Experience (EVA-X)</text>
      </svg>
      <div className="scatterlegend">
        <span><i className="dotkey base" /> Original, one dot per call</span>
        <span><i className="dotkey improved" /> Improved, same call</span>
        <span><i className="dotkey cent" /> Arm mean</span>
      </div>
    </div>
  );
}
