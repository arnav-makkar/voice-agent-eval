# Connect the framework execution truth to Indus

This is the only remaining Gate-Zero integration step. The service code is in
`framework/tool_service.py`; these endpoints belong to this project, not to
Sarvam.

## 1. Start the isolated tool service

Add a new random value named `AGENT_TOOL_SECRET` to `.env`, then run:

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python scripts/run_tool_service.py --host 127.0.0.1 --port 8788
```

Expose port `8788` through one approved HTTPS deployment or authenticated
tunnel. Do not expose the SQLite file. If a firewall is used, Sarvam documents
`4.213.167.70` as the Voice Agents tool-caller IP to allowlist.

Set `AGENT_TOOL_BASE_URL=http://127.0.0.1:8788` for the local EVA adapter.
Indus itself must use the public HTTPS URL.

## 2. Create three real API tools in the V15 draft

Use **During conversation**, POST, JSON, a short timeout, and Sarvam's secure
API-key authentication input. Store the secret in the workspace secret field;
do not paste it into the prompt or an exported definition.

| Tool | Endpoint | Agent-controlled fields |
|---|---|---|
| `check_payment_status` | `/v1/tools/check-payment-status` | none |
| `record_promise_to_pay` | `/v1/tools/record-promise-to-pay` | `date` in `DD-MM-YYYY` |
| `schedule_callback` | `/v1/tools/schedule-callback` | `date` in `DD-MM-YYYY`; narrow `time_window` with IST |

Every request also sends two existing Indus input variables:

- `run_id` ← `campaignId`
- `account_id` ← `transactionReference`

Use the builder's `@` variable picker for those two mappings. Do not type an
invented template syntax. The EVA adapter overwrites both values per trial so
parallel/repeated tests cannot share state.

Add header `X-Agent-Tool-Key` through Sarvam's secure API-key auth control.
If the builder requires a header name, use exactly that name.

## 3. Test before committing

1. Seed one run through `POST /v1/evaluation/runs`.
2. Press **Test** in the Indus API-tool panel.
3. Confirm HTTP 200 and inspect `GET /v1/evaluation/runs/{run_id}`.
4. Verify one append-only event with the correct tool, arguments and result.
5. Verify the before/after state changed only for that `run_id`.
6. Run one V15 callback or future-promise EVA smoke case.
7. Confirm `server.event.tool_call`, `loopline_tool_state.json`, and the final
   scenario state all agree before starting the matched suite.

## 4. Prompt contract

The frozen V15 prompt already says when each tool may run. Do not let Genie
rewrite the tool policy after the V8 evaluator and voice suite have been
frozen. Attach the tools, review the exact prompt diff, and commit as a new
Indus version.

Official reference: <https://docs.sarvam.ai/conversations/build/tools/https-tool>

