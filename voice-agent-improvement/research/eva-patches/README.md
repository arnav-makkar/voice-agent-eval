# Voice-harness patches

The bot-to-bot tier runs on the open-source **EVA** evaluation harness
(github.com/ServiceNow/eva), vendored *untracked* at `research/upstream/eva`
because it is a full third-party repository with its own history and licence.

These files are the local modifications, kept in-tree so the setup is
reproducible:

| File | Why it exists |
| --- | --- |
| `src/eva/assistant/samvaad_server.py` | The duplex bridge to the Sarvam Samvaad websocket, including the 20 ms paced caller-silence stream. The platform ends a turn by hearing silence; a caller leg that sends no packets between utterances never yields the floor, which produced looping calls until this was written. |
| `src/eva/utils/hash_utils.py` | Semantic time-window canonicalisation ("9 AM to 10 AM", "9-10 am" and "morning" hash equal), applied inside `normalize_for_comparison` so deterministic task grading does not fail on phrasing. |
| `src/eva/metrics/accuracy/task_completion.py` | Both state hashes computed live from the scenario database, so expected and actual are always compared under the same canonicalisation. |

## Setup

```bash
git clone https://github.com/ServiceNow/eva research/upstream/eva
cp -R research/eva-patches/src research/upstream/eva/
# then create its venv per the EVA README
```

Originals are preserved alongside the vendored tree as `*.prepatch`.
