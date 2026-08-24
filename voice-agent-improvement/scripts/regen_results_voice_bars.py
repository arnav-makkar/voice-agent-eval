"""Regenerate the Results page voice-tier bars from the enriched bot indexes.

Values are computed from the same index.json files the call browser reads, so
the bars can never disagree with the per-call rows.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT.parent / "dashboard" / "public" / "evidence" / "audio"
PAGE = ROOT.parent / "dashboard" / "public" / "c2" / "results.html"


def mean(idx, f):
    vals = [f(e) for e in idx if f(e) is not None]
    return sum(vals) / len(vals)


def bar(name, v3, v4):
    p3, p4 = round(v3 * 1000) / 10, round(v4 * 1000) / 10
    return f'''  <div class="bar-row">
    <span class="nm">{name}</span>
    <span class="bar-pair">
      <span class="bar-track"><span class="bar-fill" data-w="{p3}%"></span></span>
      <span class="bar-track"><span class="bar-fill now" data-w="{p4}%"></span></span>
    </span>
    <span class="fig">{p4}%<span class="d">was {p3}%</span></span>
  </div>'''


def main() -> int:
    b3 = json.loads((DASH / "bot-v3" / "index.json").read_text())
    b4 = json.loads((DASH / "bot-v4" / "index.json").read_text())

    rows = [
        ("Task completion", mean(b3, lambda e: e["task_completion"]), mean(b4, lambda e: e["task_completion"])),
        ("Faithfulness", mean(b3, lambda e: e["faithfulness"]), mean(b4, lambda e: e["faithfulness"])),
        ("Speech fidelity", mean(b3, lambda e: e["agent_speech_fidelity"]), mean(b4, lambda e: e["agent_speech_fidelity"])),
        ("Conciseness", mean(b3, lambda e: e["conciseness"]), mean(b4, lambda e: e["conciseness"])),
        ("Progression", mean(b3, lambda e: e["progression"]), mean(b4, lambda e: e["progression"])),
        ("Wrote exactly once",
         sum(1 for e in b3 if e["exactly_once"]) / len(b3),
         sum(1 for e in b4 if e["exactly_once"]) / len(b4)),
    ]
    block = "\n".join(bar(*r) for r in rows)

    s = PAGE.read_text()
    m = re.search(
        r'(<h3>Every voice metric, averaged across the five conversations</h3>\n<div class="bars" style="gap:22px">\n).*?(\n</div>)',
        s, re.S)
    assert m, "bars block not found"
    s = s[:m.start(1) + len(m.group(1))] + block + s[m.end(0) - len(m.group(2)):]

    old_intro = ("<p>Five situations, run once on each version, with a synthetic caller speaking to the agent over\n"
                 "live audio. Each cell is a pass or fail against a fixed threshold.</p>")
    new_intro = ("<p>Five situations, run once on each version, with a synthetic caller speaking to the agent over\n"
                 "live audio. Judged metrics use the same five-level rubric as the phone tier; execution metrics\n"
                 "come from the permanent log.</p>")
    if old_intro in s:
        s = s.replace(old_intro, new_intro)

    PAGE.write_text(s)
    for name, v3, v4 in rows:
        print(f"{name:20} {v3:.3f} -> {v4:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
