# Campaign 2 · new Indus agent setup

Everything needed to stand the agent up, in the order it has to happen. The
ordering rule is binding and was learned the expensive way:

> **transport → tools → platform proof → commit → only then any measurement**

A paid round against mock tools or an unreachable service produces a number that
looks like an answer and is not one.

---

## 1 · Create the agent

New Indus conversation agent, EMI recovery domain.

| Field | Value |
|---|---|
| Name | `Loopline C2 — Shubh` |
| System prompt | contents of `BASE-SYSTEM-PROMPT.md` |
| Opening | agent speaks first |
| Languages | Hindi primary; Hinglish, English, Punjabi permitted |

Do not commit a version yet.

## 2 · Input variables

Set these as agent input variables. The values are the frozen campaign-2
fixture — the same account is used across every tier so before and after are
comparable.

| Variable | Value |
|---|---|
| `userName` | `Arnav` |
| `merchantName` | `EasyCredit` |
| `productName` | `Samsung Smart TV` |
| `outstandingAmount` | `4416` |
| `lateChargeAmount` | `250` |
| `currentDate` | set at run time, `DD-MM-YYYY` |
| `tomorrowDate` | set at run time, `DD-MM-YYYY` |
| `customerCareNumber` | `1800-500-4444` |
| `fraudHelplineNumber` | `1800-425-5555` |
| `campaignId` | the run identifier — **maps to `run_id`** |
| `transactionReference` | the account identifier — **maps to `account_id`** |

`campaignId` and `transactionReference` are what scope a tool call to one
isolated run. Without them the service cannot tell two trials apart, so the
mapping in step 4 is not optional.

## 3 · Output variables

Extracted after each call. Leave blank/default at start.

`disposition` · `identityConfirmed` · `promisedToPayDate` · `callbackDateTime`
· `callSummary` · `disputeReason` · `escalationReason` · `escalationComment`
· `userUpdatedNumber`

`disposition` is an enum: `payment_ready`, `ptp_today`, `fptp`, `callback`,
`rtp`, `acknowledged`, `already_paid`, `dispute`, `wrong_number`,
`alternate_number`, `escalation`, `call_disconnected`.

## 4 · Tools

Three HTTP tools against the run-scoped service. **Base URL** is the stable
public hostname from step 5 — not a temporary tunnel.

Common to all three:

- Method `POST`, content type `application/json`
- Auth type **api_key**, header name `X-Loopline-Tool-Key`
- The secret goes in through the **masked input** so it is stored in workspace
  Secrets. A header typed into the tool config does not survive into the test
  runtime — this is what silently broke the previous campaign.
- Enable `save_to_variables` so results return to the agent instead of vanishing.
- Timeout 8s.

### `check_payment_status`
```
POST {BASE}/v1/tools/check-payment-status
{ "run_id": "{{campaignId}}", "account_id": "{{transactionReference}}" }
```
Returns `payment_status`, `outstanding_amount`.

### `record_promise_to_pay`
```
POST {BASE}/v1/tools/record-promise-to-pay
{ "run_id": "{{campaignId}}", "account_id": "{{transactionReference}}",
  "date": "<DD-MM-YYYY>" }
```
`date` is agent-controlled. Returns `recorded`, `date`, `disposition`.

### `schedule_callback`
```
POST {BASE}/v1/tools/schedule-callback
{ "run_id": "{{campaignId}}", "account_id": "{{transactionReference}}",
  "date": "<DD-MM-YYYY>", "time_window": "<narrow IST window>" }
```
Both `date` and `time_window` are agent-controlled.

> `record_call_outcome` is recorded by the harness from the agent's declared
> outcome and is not an HTTP tool.

## 5 · Transport

Start the service locally, then expose it on a **stable hostname**:

```bash
python scripts/run_tool_service.py --host 127.0.0.1 --port 8788
```

The previous campaign used a free tunnel with a 60-minute TTL and a hostname
that changed on restart. It expired mid-campaign, the agent's tool calls died at
the network layer, and the harness scored the silence as agent failure. Use a
named tunnel or a small always-on host so the URL outlives the run.

Sarvam's tool caller originates from `4.213.167.70` if you want to allowlist.

## 6 · Platform-originated proof — the hard gate

Seed a throwaway run, then fire each tool once from the Indus **test console**:

```bash
curl -sX POST "$BASE/v1/evaluation/runs" \
  -H "X-Loopline-Tool-Key: $LOOPLINE_TOOL_SECRET" \
  -H 'content-type: application/json' \
  -d '{"run_id":"c2-smoke","account_id":"EC-DEMO-4416","outstanding_amount":"4416"}'
```

The gate is a line in `artifacts/tool_service/inbound_requests.jsonl` showing:

- `client_host` = `4.213.167.70`
- `credential_presented` = `true`
- status `200`
- a real state delta on read-back

**No journal line, no paid calls.** A direct `curl` from this machine proves the
service works; it does not prove the platform can reach it, and that difference
is exactly what went wrong last time.

## 7 · Free smoke, then commit BASE

Run one text scenario per family against the prompt before spending anything —
it costs nothing and catches a broken agent before the voice round. Then commit
the agent as **version 1** and record the prompt text and its hash in the
deployment manifest, since Indus exposes no prompt export.

---

## What is deliberately absent from the BASE prompt

The baseline has to be able to fail, or there is nothing to improve. These are
known weaknesses and they are **not** patched in v1 — the improvement round is
supposed to find them from evidence:

- No rule forcing a successful tool result *before* success language, so the
  agent can say "I have noted your promise" without having written anything.
- No explicit once-only opening.
- No structured date normalisation beyond a general instruction.
- No handling for tool failure or timeout.

If any of these are added to BASE, the campaign measures a repair nobody made.
