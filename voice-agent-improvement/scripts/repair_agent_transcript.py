"""Rebuild the agent's side of a bot-to-bot run from what the agent actually said.

The bug this exists for
-----------------------
EVA's metrics processor builds the judged conversation from
``user_simulator_events.jsonl``. In a bot-to-bot run the ``assistant_speech``
events in that file carry ``provider: "elevenlabs"`` — they are the *caller's*
speech-to-text applied to the agent's audio, not the agent's own words. So every
speech-quality metric grades the agent on the caller's hearing of it.

It is not a small effect. In one dispute call the caller's ASR produced
``"Thank you, Aruna ji. Hello, Deepak."`` The agent never said that: Samvaad's own
transcription ends at ``"I have noted the dispute. I will make sure this is looked
into."`` The judge then flagged ``information_loss`` for forgetting the customer's
name and cut ``conversation_progression`` in half. Two of the five v3 baseline
calls were penalised the same way (``ma'am``, ``अरुण जी``), which means the
baseline's own EVA-X was understated too.

The repair
----------
Samvaad emits ``server.event.transcription`` with ``role: "bot"`` — the agent's
generated text, before any microphone. For each ElevenLabs ``assistant_speech``
event we take the Samvaad turn nearest in time (within a tolerance) and swap the
text in. Events with no Samvaad counterpart are dropped as ASR artefacts, with one
exception: the runtime's scripted greeting is delivered as fixed audio and is never
transcribed as a bot turn, so it is restored from the greeting template rather than
lost.

User turns are left exactly as they are. The caller's ASR is the right source for
the caller — that is genuinely what the agent had to work with.

The original file is kept alongside as ``.orig`` so any run can be re-repaired or
reverted, and the repair records what it did in ``transcript_repair.json``.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The runtime speaks this before the model generates anything, so Samvaad never
# transcribes it as a bot turn. Kept verbatim from the agent's greeting field.
GREETING = "नमस्ते, क्या मैं Arnav जी से बात कर रहा हूँ?"
TOLERANCE_MS = 4000


def samvaad_bot_turns(record: Path) -> list[tuple[int, str]]:
    turns: list[tuple[int, str]] = []
    path = record / "samvaad_events.jsonl"
    if not path.exists():
        return turns
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if event.get("type") == "server.event.transcription" and event.get("role") == "bot":
            text = (event.get("content") or "").strip()
            if text:
                turns.append((int(float(event["timestamp"]) * 1000), text))
    turns.sort()
    return turns


def repair(record: Path, apply: bool) -> dict:
    events_path = record / "user_simulator_events.jsonl"
    if not events_path.exists():
        return {"record": record.name, "skipped": "no user_simulator_events.jsonl"}

    truth = samvaad_bot_turns(record)
    rows = [json.loads(l) for l in events_path.read_text().splitlines() if l.strip()]

    used: set[int] = set()
    out: list[dict] = []
    replaced = dropped = restored = kept = 0

    for row in rows:
        if row.get("type") != "assistant_speech":
            out.append(row)
            continue
        heard = (row.get("data", {}).get("text") or "").strip()
        stamp = int(row.get("timestamp") or 0)

        best, best_gap = None, None
        for index, (turn_stamp, _) in enumerate(truth):
            if index in used:
                continue
            gap = abs(turn_stamp - stamp)
            if gap <= TOLERANCE_MS and (best_gap is None or gap < best_gap):
                best, best_gap = index, gap

        if best is not None:
            used.add(best)
            said = truth[best][1]
            if said != heard:
                replaced += 1
            else:
                kept += 1
            row = json.loads(json.dumps(row))
            row["data"]["text"] = said
            row["data"]["source_of_truth"] = "samvaad"
            row["data"].pop("recovered_post_call", None)
            out.append(row)
        elif not out or not any(r.get("type") == "assistant_speech" for r in out):
            # First agent utterance with no Samvaad turn: the scripted greeting.
            row = json.loads(json.dumps(row))
            row["data"]["text"] = GREETING
            row["data"]["source_of_truth"] = "greeting_template"
            row["data"].pop("recovered_post_call", None)
            out.append(row)
            restored += 1
        else:
            dropped += 1  # caller ASR artefact; the agent never said it

    summary = {
        "record": record.name,
        "samvaad_bot_turns": len(truth),
        "assistant_events_before": sum(1 for r in rows if r.get("type") == "assistant_speech"),
        "assistant_events_after": sum(1 for r in out if r.get("type") == "assistant_speech"),
        "text_replaced": replaced,
        "text_already_correct": kept,
        "greeting_restored": restored,
        "asr_artefacts_dropped": dropped,
    }

    if apply:
        backup = events_path.with_suffix(".jsonl.orig")
        if not backup.exists():
            shutil.copy(events_path, backup)
        events_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n")
        (record / "transcript_repair.json").write_text(json.dumps(summary, indent=1))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", help="run ids under artifacts/eva_live")
    parser.add_argument("--apply", action="store_true", help="write; otherwise dry-run")
    args = parser.parse_args()

    for run in args.runs:
        run_dir = ROOT / "artifacts" / "eva_live" / run / "records"
        if not run_dir.exists():
            print(f"  {run}: no records dir")
            continue
        for record in sorted(run_dir.iterdir()):
            if not record.is_dir():
                continue
            s = repair(record, args.apply)
            if "skipped" in s:
                print(f"  {run}/{s['record']}: {s['skipped']}")
                continue
            print(f"  {run}/{s['record']}: samvaad={s['samvaad_bot_turns']} "
                  f"events {s['assistant_events_before']}→{s['assistant_events_after']} "
                  f"| replaced {s['text_replaced']} kept {s['text_already_correct']} "
                  f"greeting {s['greeting_restored']} dropped {s['asr_artefacts_dropped']}")
    if not args.apply:
        print("\n  dry run — pass --apply to write (originals kept as .jsonl.orig)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
