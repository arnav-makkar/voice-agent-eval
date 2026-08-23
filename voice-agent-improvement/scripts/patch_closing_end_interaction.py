"""Name `end_interaction` in the closing rule so the agent actually hangs up.

What went wrong
---------------
Card 1 on v4 ended like this::

    AGENT   धन्यवाद Arnav जी, आपका दिन शुभ हो। अरे, है क्या तू?
            tools: record_call_outcome(disposition=payment_ready)

The agent delivered the correct closing and then held the line. Five seconds
later the Sarvam runtime injected its inactivity nudge, and the caller hung up.

The closing rule already told the agent to "end the interaction", but only as
prose — it never named the function that does it. The platform exposes
`end_interaction(end_message=...)` (confirmed: the agent calls it correctly over
the text-chat channel when the customer says goodbye first), and
`agent_can_end_interaction` is true. On this call the agent also collapsed the
two closing turns into one, and having done so never issued the call at all.

Naming the tool, and saying plainly what happens when it is skipped, closes the
gap. Nothing else in the prompt is touched.

Scope
-----
Call termination was never a GEPA objective, so this does not touch the measured
improvement: no scored metric in the campaign depends on whether the agent hangs
up. It is recorded as a declared post-optimisation operational patch, and the
champion sha is re-pinned afterwards so the preflight keeps guarding the file.

    python scripts/patch_closing_end_interaction.py            # dry run
    python scripts/patch_closing_end_interaction.py --apply
    python scripts/patch_closing_end_interaction.py --revert
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework.evaluation.adapters import indus_authoring as A  # noqa: E402

BACKUP = ROOT / "artifacts" / "campaign2" / "prompt.pre_end_interaction.md"
PIN = ROOT / "artifacts" / "campaign2" / "v4_champion.json"

OLD = ("**Turn two — close.** Only once `record_call_outcome` has returned, "
       "thank them by name in one\nshort sentence and end the interaction.")

NEW = ("**Turn two — close.** Only once `record_call_outcome` has returned, "
       "thank them by name in one\nshort sentence and end the call by calling "
       "`end_interaction`, passing that sentence as `end_message`.\n"
       "Speaking the closing is not ending the call. If you say goodbye and do "
       "not call `end_interaction`,\nthe line stays open, the customer is left "
       "waiting, and the platform fills the silence on your behalf.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--revert", action="store_true")
    args = parser.parse_args()

    live = A.read_instructions()
    sha = hashlib.sha256(live.encode()).hexdigest()[:16]
    print(f"  live prompt {len(live):,} chars  sha {sha}")

    if args.revert:
        if not BACKUP.exists():
            raise SystemExit("  no backup to revert to")
        updated = BACKUP.read_text(encoding="utf-8")
    else:
        if NEW in live:
            print("  already patched — nothing to do")
            return 0
        if OLD not in live:
            raise SystemExit(
                "  anchor text not found; the closing rule has changed.\n"
                "  Refusing to guess — re-read the Closing section and update OLD.")
        if not BACKUP.exists():
            BACKUP.write_text(live, encoding="utf-8")
            print(f"  saved original -> {BACKUP.relative_to(ROOT)}")
        updated = live.replace(OLD, NEW, 1)

    print(f"  new prompt  {len(updated):,} chars "
          f"({len(updated) - len(live):+,} chars)")
    if not (args.apply or args.revert):
        print("\n  dry run — pass --apply to write")
        return 0

    A.write_instructions(updated)

    back = A.read_instructions()
    if back != updated:
        raise SystemExit("  write did not round-trip — prompt left in an unknown state")
    new_sha = hashlib.sha256(back.encode()).hexdigest()[:16]

    record = json.loads(PIN.read_text()) if PIN.exists() else {}
    record.update({
        "sha": new_sha,
        "chars": len(back),
        "note": ("generation-2 GEPA champion, plus one declared operational patch: "
                 "the closing rule now names end_interaction. Call termination was "
                 "not a GEPA objective and no scored metric depends on it."),
        "gepa_sha": record.get("gepa_sha", record.get("sha")),
    })
    PIN.write_text(json.dumps(record, indent=1))
    print(f"\n  wrote prompt; sha {sha} -> {new_sha}")
    print(f"  re-pinned {PIN.relative_to(ROOT)} (gepa_sha kept as {record['gepa_sha']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
