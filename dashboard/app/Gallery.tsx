"use client";

import { useEffect, useState } from "react";

type StateMap = Record<string, unknown>;

type ToolEvent = {
  sequence: number;
  name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
  status: string;
};

type Turn = {
  sequence: number;
  actor: "caller" | "agent";
  content: string;
  latency_ms?: number | null;
  defect?: { metric?: string | null; component?: string | null } | null;
};

type Episode = {
  candidate_id: string;
  candidate_hash?: string;
  termination_reason?: string;
  declared_disposition?: string;
  turns: Turn[];
  tool_events: ToolEvent[];
  tools_used: string[];
  initial_state: StateMap;
  final_state: StateMap;
  state_diff: Array<{ field: string; before: unknown; after: unknown }>;
  accuracy?: Record<string, boolean> | null;
  action_checks?: Array<{ expected: { name: string; arguments: Record<string, unknown> }; passed: boolean }> | null;
  forbidden_hits?: string[] | null;
  first_failure?: string | null;
  failure_localization?: { component?: string; evidence?: string; turn_sequence?: number } | null;
  experience?: Record<string, number> | null;
  task_success?: boolean | null;
  valid_simulation?: boolean | null;
  semantic?: Record<string, unknown> | null;
  evaluator?: string | null;
};

type Card = {
  id: string;
  title: string;
  headline: string;
  why: string;
  kind: "single" | "comparison" | "evaluator_toggle";
  tier: string;
  tier_label: string;
  tier_detail: string;
  scenario: {
    scenario_id: string;
    language?: string;
    split?: string;
    failure_family?: string;
    persona?: Record<string, string>;
    user_goal?: string;
    target_disposition?: string;
    accepted_dispositions?: string[];
    expected_state?: StateMap;
    required_actions?: Array<{ name: string; arguments: Record<string, unknown> }>;
    forbidden_phrases?: string[];
    perturbations?: string[];
    max_agent_turns?: number;
    initial_environment?: StateMap;
    visible_context?: Record<string, string>;
  };
  tools: Array<{ name: string; kind: string; description: string }>;
  episode?: Episode;
  episode_rescored?: Episode;
  baseline?: Episode;
  candidate?: Episode;
  baseline_label?: string;
  candidate_label?: string;
  audio?: string;
  source_note?: string;
};

type GalleryData = { cards: Card[]; claim_boundary: string; card_count: number };

const fmt = (value: unknown) => (value === null || value === undefined ? "null" : typeof value === "object" ? JSON.stringify(value) : String(value));
const words = (value?: string | null) => (value || "—").replaceAll("_", " ");


function Acc({ label, children, open = false }: { label: string; children: React.ReactNode; open?: boolean }) {
  return (
    <details className="g-acc" open={open}>
      <summary>{label}</summary>
      <div>{children}</div>
    </details>
  );
}

function ToolCard({ event, stateDiff }: { event: ToolEvent; stateDiff: Episode["state_diff"] }) {
  return (
    <div className="g-toolcall">
      <div className="g-toolcall-head">
        <span className="g-wrench">⚒</span>
        <code>{event.name}</code>
        <span className={`g-status g-status-${event.status === "success" ? "ok" : "bad"}`}>{event.status}</span>
      </div>
      <div className="g-toolcall-body">
        <p className="g-minilabel">Parameters</p>
        {Object.keys(event.arguments || {}).length === 0 ? (
          <p className="g-none">no arguments</p>
        ) : (
          Object.entries(event.arguments).map(([key, value]) => (
            <div className="g-kv" key={key}>
              <code className="g-k">{key}:</code>
              <code className="g-v">{fmt(value)}</code>
            </div>
          ))
        )}
      </div>
      {stateDiff.length > 0 && (
        <div className="g-toolcall-delta">
          <p className="g-minilabel">State delta</p>
          {stateDiff.map((row) => (
            <div className="g-kv" key={row.field}>
              <code className="g-k">{row.field}</code>
              <code className="g-before">{fmt(row.before)}</code>
              <span>→</span>
              <code className="g-after">{fmt(row.after)}</code>
            </div>
          ))}
        </div>
      )}
      <details className="g-toolcall-foot">
        <summary>Response</summary>
        <pre>{JSON.stringify(event.result, null, 2)}</pre>
      </details>
    </div>
  );
}

function Transcript({ episode, title }: { episode: Episode; title?: string }) {
  const byTurn = new Map<number, ToolEvent[]>();
  // Tool events are appended after the agent turn that produced them.
  const lastAgent = [...episode.turns].reverse().find((turn) => turn.actor === "agent");
  episode.tool_events.forEach((event) => {
    const key = lastAgent?.sequence ?? 0;
    byTurn.set(key, [...(byTurn.get(key) || []), event]);
  });
  return (
    <div className="g-transcript">
      {title && <p className="g-minilabel">{title}</p>}
      {episode.turns.map((turn) => (
        <div key={turn.sequence}>
          <article className={`g-turn g-turn-${turn.actor}`}>
            <div className="g-turn-head">
              <b>{turn.actor === "agent" ? "Shubh · voice agent" : "Caller · simulated"}</b>
              {turn.defect && (
                <span className="g-flag" title={`${words(turn.defect.metric)} — owned by ${words(turn.defect.component)}`}>
                  ⚠ {words(turn.defect.metric)}
                </span>
              )}
            </div>
            <p>{turn.content}</p>
          </article>
          {(byTurn.get(turn.sequence) || []).map((event) => (
            <ToolCard key={`${event.sequence}-${event.name}`} event={event} stateDiff={episode.state_diff} />
          ))}
        </div>
      ))}
    </div>
  );
}

function Verdict({ episode }: { episode: Episode }) {
  return (
    <div className="g-verdict">
      <div className={`g-badge ${episode.task_success ? "g-pass" : "g-fail"}`}>
        {episode.task_success ? "Task passed" : "Task failed"}
      </div>
      <dl className="g-acc-grid">
        {Object.entries(episode.accuracy || {}).map(([key, value]) => (
          <div key={key} className={value ? "ok" : "bad"}>
            <dt>{words(key)}</dt>
            <dd>{value ? "pass" : "fail"}</dd>
          </div>
        ))}
      </dl>
      {episode.action_checks && episode.action_checks.length > 0 && (
        <Acc label={`Required actions (${episode.action_checks.filter((c) => c.passed).length}/${episode.action_checks.length} met)`} open>
          {episode.action_checks.map((check, index) => (
            <div className={`g-check ${check.passed ? "ok" : "bad"}`} key={index}>
              <span>{check.passed ? "✓" : "✗"}</span>
              <div>
                <code>{check.expected.name}</code>
                <code className="g-args">{JSON.stringify(check.expected.arguments)}</code>
              </div>
            </div>
          ))}
        </Acc>
      )}
      {episode.first_failure && (
        <Acc label="First break">
          <p className="g-fl">
            <b>{words(episode.first_failure)}</b> · owned by <b>{words(episode.failure_localization?.component)}</b>
            {episode.failure_localization?.turn_sequence != null && <> · turn {episode.failure_localization.turn_sequence}</>}
          </p>
          {episode.failure_localization?.evidence && <p className="g-quote">“{episode.failure_localization.evidence}”</p>}
        </Acc>
      )}
      {episode.semantic && (
        <Acc label="Semantic judge (secondary)">
          <dl className="g-sem">
            {Object.entries(episode.semantic).map(([key, value]) => (
              <div key={key}>
                <dt>{words(key)}</dt>
                <dd>{fmt(value)}</dd>
              </div>
            ))}
          </dl>
          <p className="g-note">Judges never control the gate. Where the deterministic checker and the judge disagree, both readings are preserved.</p>
        </Acc>
      )}
      {episode.experience && (
        <Acc label="Experience dimensions">
          <dl className="g-sem">
            {Object.entries(episode.experience).map(([key, value]) => (
              <div key={key}>
                <dt>{words(key)}</dt>
                <dd>{typeof value === "number" ? value.toFixed(3) : fmt(value)}</dd>
              </div>
            ))}
          </dl>
        </Acc>
      )}
    </div>
  );
}

function Evidence({ card, episode }: { card: Card; episode: Episode }) {
  const used = new Set(episode.tools_used);
  return (
    <aside className="g-rail">
      <p className="g-minilabel">Agent tools</p>
      <p className="g-count">
        {used.size} of {card.tools.length} used in this episode
      </p>
      {card.tools.map((tool) => (
        <div key={tool.name} className={`g-tool ${used.has(tool.name) ? "g-tool-used" : ""}`} title={tool.description}>
          <span className="g-wrench">⚒</span>
          <code>{tool.name}</code>
          <span className={`g-kind g-kind-${tool.kind}`}>{tool.kind}</span>
        </div>
      ))}

      <p className="g-minilabel">State change</p>
      {episode.state_diff.length === 0 ? (
        <p className="g-none">Nothing in the backend changed during this episode.</p>
      ) : (
        episode.state_diff.map((row) => (
          <div className="g-diff" key={row.field}>
            <code className="g-k">{row.field}</code>
            <div>
              <code className="g-before">{fmt(row.before)}</code>
              <span>→</span>
              <code className="g-after">{fmt(row.after)}</code>
            </div>
          </div>
        ))
      )}

      <p className="g-minilabel">Episode</p>
      <dl className="g-meta">
        <div><dt>Candidate</dt><dd>{episode.candidate_id}</dd></div>
        <div><dt>Declared</dt><dd>{words(episode.declared_disposition)}</dd></div>
        <div><dt>Ended</dt><dd>{words(episode.termination_reason)}</dd></div>
        <div><dt>Simulator</dt><dd>{episode.valid_simulation ? "valid" : "invalid"}</dd></div>
      </dl>
    </aside>
  );
}

function Contract({ card }: { card: Card }) {
  const scenario = card.scenario;
  return (
    <aside className="g-rail">
      <p className="g-minilabel">Scenario contract</p>
      <h4 className="g-goal">{scenario.user_goal}</h4>
      {scenario.persona && (
        <div className="g-persona">
          <p className="g-minilabel">Persona</p>
          <p>{Object.entries(scenario.persona).map(([key, value]) => `${key}: ${value}`).join(" · ")}</p>
        </div>
      )}
      <Acc label="Expected outcome" open>
        <dl className="g-meta">
          <div><dt>Target</dt><dd>{words(scenario.target_disposition)}</dd></div>
          <div><dt>Accepted</dt><dd>{(scenario.accepted_dispositions || []).map(words).join(", ") || "—"}</dd></div>
          {Object.entries(scenario.expected_state || {}).map(([key, value]) => (
            <div key={key}><dt>{words(key)}</dt><dd>{fmt(value)}</dd></div>
          ))}
        </dl>
      </Acc>
      {scenario.required_actions && scenario.required_actions.length > 0 && (
        <Acc label="Required actions">
          {scenario.required_actions.map((action, index) => (
            <div className="g-kv" key={index}>
              <code className="g-k">{action.name}</code>
              <code className="g-v">{JSON.stringify(action.arguments)}</code>
            </div>
          ))}
        </Acc>
      )}
      <Acc label="Forbidden phrases">
        <p className="g-chips">{(scenario.forbidden_phrases || []).map((phrase) => <span key={phrase}>{phrase}</span>)}</p>
      </Acc>
      <Acc label="Seeded account state">
        <pre className="g-pre">{JSON.stringify(scenario.initial_environment, null, 2)}</pre>
      </Acc>
      <Acc label="Scenario details">
        <dl className="g-meta">
          <div><dt>ID</dt><dd>{scenario.scenario_id}</dd></div>
          <div><dt>Split</dt><dd>{words(scenario.split)}</dd></div>
          <div><dt>Language</dt><dd>{words(scenario.language)}</dd></div>
          <div><dt>Family</dt><dd>{words(scenario.failure_family)}</dd></div>
          <div><dt>Turn budget</dt><dd>{scenario.max_agent_turns ?? "—"}</dd></div>
          {scenario.perturbations && scenario.perturbations.length > 0 && (
            <div><dt>Perturbations</dt><dd>{scenario.perturbations.map(words).join(", ")}</dd></div>
          )}
        </dl>
      </Acc>
    </aside>
  );
}

export default function Gallery() {
  const [data, setData] = useState<GalleryData | null>(null);
  const [active, setActive] = useState(0);
  const [rescored, setRescored] = useState(true);
  const [side, setSide] = useState<"baseline" | "candidate">("candidate");
  const [judgeOpen, setJudgeOpen] = useState(false);

  useEffect(() => {
    fetch("/gallery.json").then((response) => response.json()).then(setData).catch(() => undefined);
  }, []);

  if (!data) return <div className="loading-card">Loading preserved episode artifacts…</div>;
  const card = data.cards[active];
  const episode =
    card.kind === "comparison"
      ? side === "baseline" ? card.baseline! : card.candidate!
      : card.kind === "evaluator_toggle"
        ? rescored ? card.episode_rescored! : card.episode!
        : card.episode!;

  return (
    <div className="g-wrap">
      <div className="g-tabs">
        {data.cards.map((item, index) => (
          <button key={item.id} className={index === active ? "on" : ""} onClick={() => setActive(index)}>
            <span className={`g-tier g-tier-${item.tier}`}>{item.tier_label}</span>
            <b>{item.title}</b>
            <small>{item.scenario.scenario_id}</small>
          </button>
        ))}
      </div>

      <div className="g-head">
        <div>
          <h3>{card.headline}</h3>
          <p>{card.why}</p>
          {card.source_note && <p className="g-source">{card.source_note}</p>}
          {card.audio && (
            <audio className="g-audio" controls preload="metadata" src={card.audio} aria-label={`${card.title} call recording`}>
              <track kind="captions" src="/evidence/eva-live/conversation.hi.vtt" srcLang="hi" label="Hinglish transcript" />
            </audio>
          )}
        </div>
        <div className="g-controls">
          {card.kind === "comparison" && (
            <div className="g-switch">
              <button className={side === "baseline" ? "on" : ""} onClick={() => setSide("baseline")}>{card.baseline_label ?? "Baseline"}</button>
              <button className={side === "candidate" ? "on" : ""} onClick={() => setSide("candidate")}>{card.candidate_label ?? "Candidate"}</button>
            </div>
          )}
          {card.kind === "evaluator_toggle" && (
            <div className="g-switch">
              <button className={!rescored ? "on" : ""} onClick={() => setRescored(false)}>Evaluator v2</button>
              <button className={rescored ? "on" : ""} onClick={() => setRescored(true)}>Evaluator v3</button>
            </div>
          )}
          <button className="g-judge-button" onClick={() => setJudgeOpen(true)}>Inspect judge contract</button>
        </div>
      </div>

      {judgeOpen && (
        <div className="g-modal-backdrop" role="presentation">
          <section className="g-modal" role="dialog" aria-modal="true" aria-label="Judge contract">
            <div className="g-modal-head">
              <div><p className="g-minilabel">Judge accountability</p><h3>The judge can explain. It cannot release.</h3></div>
              <button aria-label="Close judge contract" onClick={() => setJudgeOpen(false)}>×</button>
            </div>
            <p>The semantic judge receives the immutable transcript and scenario contract, then returns structured scores and a cited sentence. It never sees candidate ranking and never controls deterministic task, state, action, or safety gates.</p>
            <div className="g-modal-grid">
              <div><b>Prompt contract</b><span>Score only faithfulness, conciseness, progression, and speakability. Cite the exact turn.</span></div>
              <div><b>Calibration</b><span>83% failure-detection agreement over 60 preserved episodes; ownership agreement is 50% on six jointly-failed cases.</span></div>
              <div><b>Release authority</b><span>None. Executable assertions decide; owner review resolves evaluator disputes.</span></div>
            </div>
            <p className="g-note">The low ownership denominator is displayed because grader quality is evidence, not decoration.</p>
          </section>
        </div>
      )}

      {card.kind === "evaluator_toggle" && (
        <p className="g-callout">
          The trace below is byte-identical under both evaluators. Only the measurement changed: v2 matched the literal string
          “otp” inside a <em>correct refusal</em> and recorded a P0 guardrail failure. v3 fixed the check and the same episode passes.
          Measurement is a versioned artifact, and it can be wrong.
        </p>
      )}

      <div className="g-three">
        <Contract card={card} />
        <section className="g-center">
          <Transcript episode={episode} />
          <Verdict episode={episode} />
        </section>
        <Evidence card={card} episode={episode} />
      </div>

      <p className="g-boundary">
        <b>{card.tier_label}</b> — {card.tier_detail} {card.source_note ? `Source: ${card.source_note}.` : ""}
      </p>
    </div>
  );
}
