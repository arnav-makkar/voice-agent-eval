"use client";

import { useState } from "react";

export type MetricDef = {
  id: string; name: string; axis: string; method: string;
  question: string; inputs: string; output: string; threshold: string; why: string;
};

export type ScenarioRow = {
  scenario_id: string; split: string; language?: string; family?: string; goal?: string;
  before: { task_success?: boolean | null; first_failure?: string | null };
  after: { task_success?: boolean | null; first_failure?: string | null };
  outcome: "repaired" | "regressed" | "held" | "still failing";
};

export type Rate = { rate: number; ci: [number, number]; n: number };

export type ComponentRates = {
  before: Record<string, Rate>;
  after: Record<string, Rate>;
  labels: Record<string, string>;
  task_ci: { before: Rate; after: Rate };
  ci_note: string;
};

const words = (value?: string | null) => (value || "—").replaceAll("_", " ");

function Bar({ value, tone }: { value?: Rate; tone: "before" | "after" }) {
  if (!value) return <div className="bar-track" />;
  const [low, high] = value.ci;
  return (
    <div className="bar-track">
      <div className={`bar-fill ${tone}`} style={{ width: `${value.rate * 100}%` }} />
      <span className="ci-span" style={{ left: `${low * 100}%`, width: `${(high - low) * 100}%` }} aria-hidden="true" />
      <span className="bar-val" title={`95% interval ${(low * 100).toFixed(0)}–${(high * 100).toFixed(0)}% over n=${value.n}`}>
        {(value.rate * 100).toFixed(0)}%
      </span>
    </div>
  );
}

export function Methodology({ metrics }: { metrics: MetricDef[] }) {
  const [open, setOpen] = useState<string | null>(metrics[0]?.id ?? null);
  const axes = ["Accuracy", "Experience", "Validation", "Secondary"];
  return (
    <div className="mth">
      {axes.map((axis) => {
        const rows = metrics.filter((metric) => metric.axis === axis);
        if (rows.length === 0) return null;
        return (
          <div key={axis} className="mth-axis">
            <p className="eyebrow">{axis}</p>
            {rows.map((metric) => {
              const isOpen = open === metric.id;
              return (
                <div className={`mth-row ${isOpen ? "on" : ""}`} key={metric.id}>
                  <button onClick={() => setOpen(isOpen ? null : metric.id)} aria-expanded={isOpen}>
                    <span className="nm">{metric.name}</span>
                    <span className={`meth ${metric.method === "Deterministic" ? "det" : "judge"}`}>{metric.method}</span>
                    <span className="q">{metric.question}</span>
                    <span className="chev">{isOpen ? "–" : "+"}</span>
                  </button>
                  {isOpen && (
                    <div className="mth-body">
                      <div>
                        <p className="k">Inputs</p>
                        <p>{metric.inputs}</p>
                      </div>
                      <div>
                        <p className="k">Output</p>
                        <p>{metric.output}</p>
                      </div>
                      <div>
                        <p className="k">Pass rule</p>
                        <p>{metric.threshold}</p>
                      </div>
                      <div className="wide">
                        <p className="k">Why it exists</p>
                        <p>{metric.why}</p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

export function ComponentBars({ rates }: { rates: ComponentRates }) {
  const keys = Object.keys(rates.labels);
  return (
    <div className="bars">
      {keys.map((key) => {
        const before = rates.before[key];
        const after = rates.after[key];
        return (
          <div className="bar-row" key={key}>
            <p className="bar-name">{rates.labels[key]}</p>
            <Bar value={before} tone="before" />
            <Bar value={after} tone="after" />
          </div>
        );
      })}
      <div className="bar-legend">
        <span><i className="sw before" /> As deployed</span>
        <span><i className="sw after" /> After improvement</span>
        <span className="ci-key">Whiskers are 95% intervals</span>
      </div>
      <p className="ci-note">{rates.ci_note}</p>
    </div>
  );
}

export function ScenarioMatrix({ rows }: { rows: ScenarioRow[] }) {
  const [focus, setFocus] = useState<ScenarioRow | null>(null);
  const counts = rows.reduce<Record<string, number>>((acc, row) => {
    acc[row.outcome] = (acc[row.outcome] || 0) + 1;
    return acc;
  }, {});
  return (
    <div className="matrix">
      <div className="matrix-legend">
        <span className="pill gain">{counts.repaired ?? 0} repaired</span>
        <span className="pill">{counts.held ?? 0} already passing, still passing</span>
        <span className="pill loss">{counts.regressed ?? 0} regressed</span>
        <span className="pill hold">{counts["still failing"] ?? 0} still failing</span>
      </div>
      <div className="matrix-grid">
        {rows.map((row) => (
          <button
            key={row.scenario_id}
            className={`cell ${row.outcome.replace(" ", "-")}`}
            onMouseEnter={() => setFocus(row)}
            onFocus={() => setFocus(row)}
            onClick={() => setFocus(row)}
            aria-label={`${row.scenario_id}: ${row.outcome}`}
          >
            <span className="dot-before" />
            <span className="dot-after" />
          </button>
        ))}
      </div>
      <div className="matrix-detail">
        {focus ? (
          <>
            <p className="mono id">{focus.scenario_id} · {words(focus.split)} · {words(focus.language)}</p>
            <p className="goal">{focus.goal}</p>
            <div className="ba">
              <span className={focus.before.task_success ? "ok" : "no"}>
                As deployed: {focus.before.task_success ? "passed" : `failed on ${words(focus.before.first_failure)}`}
              </span>
              <span className={focus.after.task_success ? "ok" : "no"}>
                After: {focus.after.task_success ? "passed" : `failed on ${words(focus.after.first_failure)}`}
              </span>
            </div>
          </>
        ) : (
          <p className="hint">Every scenario in the suite. Hover or tap a cell to see what it tests and how each agent did.</p>
        )}
      </div>
    </div>
  );
}
