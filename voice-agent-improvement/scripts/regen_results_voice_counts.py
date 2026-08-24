"""Regenerate the Results page voice-tier counts from the enriched bot indexes.

Five conversations cannot carry an average, so this tier is reported as counts
out of five. Values come from the same index.json files the call browser reads,
so the table can never disagree with the per-call rows.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT.parent / "dashboard" / "public" / "evidence" / "audio"
PAGE = ROOT.parent / "dashboard" / "public" / "results.html"

ROWS = [
    ("Reached the required end state", lambda c: c["task_completion"] == 1),
    ("Wrote every record exactly once", lambda c: c["exactly_once"]),
    ("Top rating on all three judged metrics",
     lambda c: c["faithfulness_rating"] == 5 and c["conciseness_rating"] == 5
     and c["progression_rating"] == 5),
]


def main() -> int:
    b3 = json.loads((DASH / "bot-v3" / "index.json").read_text())
    b4 = json.loads((DASH / "bot-v4" / "index.json").read_text())
    n = len(b3)

    out = [f'<tr><th style="width:44%">Across the five conversations</th>'
           f'<th class="n">Before</th><th class="n">After</th></tr>']
    for label, pred in ROWS:
        a, b = sum(1 for c in b3 if pred(c)), sum(1 for c in b4 if pred(c))
        after = f'<strong class="gain">{b} of {n}</strong>' if b > a else f"{b} of {n}"
        out.append(f'<tr><td><strong>{label}</strong></td>'
                   f'<td class="n">{a} of {n}</td><td class="n">{after}</td></tr>')
        print(f"{label:40} {a}/{n} -> {b}/{n}")

    s = PAGE.read_text()
    m = re.search(r'(<h2>The voice tier</h2>.*?<div class="tw"><table>\n).*?(\n</table></div>)',
                  s, re.S)
    assert m, "voice counts table not found"
    s = s[:m.start(1) + len(m.group(1))] + "\n".join(out) + s[m.end(0) - len(m.group(2)):]
    PAGE.write_text(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
