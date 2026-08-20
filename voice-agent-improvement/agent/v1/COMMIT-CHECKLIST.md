# v11 control draft checklist

Committed v10 is the behavior source. The v11 draft is a cleaned, direct control version—not the optimized candidate. It must not be committed until the online editor and local artifacts match exactly.

Before requesting approval to commit the control:

1. Confirm v10 remains committed and Indus shows `v11 · Draft` with Shubh, 1.05× speed, caller interruption enabled, and a three-minute maximum call length.
2. Confirm the initial message is exactly the version in `INITIAL-MESSAGE.txt` with the `userName` variable chip.
3. Confirm the system prompt matches `SYSTEM-PROMPT.md`.
4. Confirm the 19 input defaults match `VARIABLES.md`; `run_id` must not be an Indus variable.
5. Confirm all three mock HTTP tools are labelled `DISABLED FOR V11 CONTROL`, the prompt says never to call a custom tool, and no tool name appears in the prompt. Do not claim these mocks are real integrations.
6. Dry-run `examples/emi-reminder.variables.json` with `--run-id BL-CTRL-01` and confirm the frozen TV facts.
7. Confirm the call goal is `disposition = payment_ready` and the enum distinguishes immediate pay-now from later-today PTP.
8. Confirm the quiet-caller nudges are generic at 8 and 12 seconds, the voicemail identifies Shubh/EasyCredit rather than Neha, and the maximum call length is three minutes.
9. Stop and obtain explicit user approval before pressing Commit.

After the control is committed, set `SARVAM_APP_VERSION=11`. Every executed call must use a unique `--run-id`; the CLI stores run ID, attempt ID, version, and timestamp in the local manifest. Later join the transcript, recording, scenario, and human label.

After the improvement gates pass, commit the selected candidate as the next version. Do not overwrite the control. Repeat the same 15 cards on the candidate, including the English-only, Punjabi-first and hard-refusal negative-control probes.
