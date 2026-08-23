"""Reword the fresh blind-30's caller lines, keeping the contract identical.

The suite's caller turns come from a fixed authored utterance bank, so a fair
challenge is whether the champion learned *tool discipline* or merely the bank's
phrasings. This rewrites every caller line with Gemini — same intent, same
language, same facts, different words — and changes nothing else: the required
journal writes, accepted dispositions and account values are untouched, so the
grading contract is identical and only the surface wording moves.

A champion that holds its score here generalises past the wording. One that drops
was partly fitting the bank, and that is worth knowing before any claim about
production traffic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")
import litellm  # noqa: E402

BENCH = ROOT / "artifacts" / "framework" / "emi" / "benchmark_v1"
MODEL = "gemini/gemini-2.5-flash"

# The script must be pinned, not merely requested. A first pass that only asked
# for "the same language" flipped 26% of Hinglish lines into Devanagari, which
# would have made this a translation test wearing a paraphrase label — a score
# drop would have been unattributable.
PROMPT = """Reword this line an EMI-recovery customer says on a call.

Rules:
- WRITING SYSTEM: the reworded line MUST be written in {script}. This is absolute.
  Do not transliterate into any other script.
- Keep every fact identical: dates, amounts, names, and what they are agreeing or refusing to do.
- Keep the same intent and the same length range.
- Change the wording — different verbs and phrasing, how a different person would say it.
- Reply with the reworded line only, nothing else.

Line: {line}"""


def script_of(text: str) -> str:
    import re
    devanagari = len(re.findall(r"[\u0900-\u097f]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return "the Devanagari script" if devanagari > latin else "the Latin script (romanised)"


def reword(line: str, attempts: int = 3) -> str:
    """Reword, rejecting any candidate that changed writing system."""
    want = script_of(line)
    for _ in range(attempts):
        try:
            r = litellm.completion(model=MODEL, max_tokens=200, messages=[
                {"role": "user", "content": PROMPT.format(line=line, script=want)}])
            out = (r.choices[0].message.content or "").strip().strip('"')
        except Exception:
            return line
        if out and out != line and script_of(out) == want:
            return out
    return line


def main() -> int:
    rows = [json.loads(l) for l in (BENCH / "blind_g2.jsonl").read_text().splitlines() if l.strip()]
    changed = 0
    for i, row in enumerate(rows, 1):
        for step in row["user_steps"]:
            original = step["text"]
            step["text"] = reword(original)
            changed += step["text"] != original
        row["scenario_id"] = row["scenario_id"].replace("EMI-BLIND-", "EMI-PARA-")
        row["split"] = "paraphrase"
        print(f"  [{i}/{len(rows)}] {row['scenario_id']}", flush=True)
    (BENCH / "paraphrase.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    print(f"  wrote {len(rows)} scenarios, {changed} lines reworded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
