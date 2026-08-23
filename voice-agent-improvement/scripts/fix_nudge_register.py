"""Replace the platform's inactivity nudge with one that fits a collections call.

The stock Sarvam nudge, injected by the runtime after ``timeout_seconds`` of
caller silence, reads in Hindi:

    अरे, है क्या तू?

That is the intimate/disrespectful second person (तू) with a casual interjection —
the register you would use with a close friend, not a customer you are asking for
money. The agent's own prompt speaks entirely in आप and appends जी to the
customer's name, so the nudge breaks character the moment it fires. The English
row, "Hey are you there?", is the same line and shows what it is.

It fires only when the agent is waiting rather than hanging up, which is why it
appears on USER_ENDS calls and never on AGENT_ENDS ones: after the closing line
the agent holds the line, five seconds pass, and the runtime speaks.

This rewrites the message for the languages this agent actually serves and leaves
everything else — timeout, nudge count, ``end_interaction_after_consecutive_nudges``
— untouched, so the mechanism that eventually ends the call still works. The
agent's prompt is not modified: the champion's bytes stay exactly as the optimiser
produced them.

    python scripts/fix_nudge_register.py            # dry run
    python scripts/fix_nudge_register.py --apply
    python scripts/fix_nudge_register.py --revert
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework.evaluation.adapters.indus_authoring import (  # noqa: E402
    APP,
    BASE,
    _headers,
    get_config,
    load_token,
)

BACKUP = ROOT / "artifacts" / "campaign2" / "nudge_config.original.json"

# Same intent, correct register: polite second person, no interjection.
POLITE = {
    "English": "Are you still there?",
    "Hindi": "क्या आप सुन पा रहे हैं?",
}


def _rows(nudge: dict) -> list[dict]:
    """Every language->text mapping the nudge config carries, male and female."""
    out: list[dict] = []
    for cfg in nudge.get("user_nudge_message_configs") or []:
        for key in ("multilingual_template_messages",
                    "multilingual_template_messages_female"):
            for entry in cfg.get(key) or []:
                mapping = entry.get("language_text_mapping")
                if mapping:
                    out.append(mapping)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--revert", action="store_true")
    args = parser.parse_args()

    token = load_token()
    config = get_config(token)
    nudge = config["interaction_config"]["nudge_config"]

    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        BACKUP.write_text(json.dumps(nudge, ensure_ascii=False, indent=1))
        print(f"  saved original -> {BACKUP.relative_to(ROOT)}")

    if args.revert:
        config["interaction_config"]["nudge_config"] = json.loads(BACKUP.read_text())
        target = "original"
    else:
        for mapping in _rows(nudge):
            for language, text in POLITE.items():
                if language in mapping and mapping[language] != text:
                    print(f"  {language:8} {mapping[language]!r} -> {text!r}")
                    mapping[language] = text
        target = "polite"

    if not (args.apply or args.revert):
        print("\n  dry run — pass --apply to write")
        return 0

    response = httpx.put(
        f"{BASE}/{APP}",
        json={"app": config, "app_name": APP},
        headers=_headers(token),
        timeout=120,
    )
    response.raise_for_status()

    live = _rows(get_config(token)["interaction_config"]["nudge_config"])
    print(f"\n  wrote {target}; live Hindi row now: {live[0].get('Hindi')!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
