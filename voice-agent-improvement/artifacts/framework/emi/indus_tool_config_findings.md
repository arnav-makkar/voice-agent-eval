# Indus tool configuration — findings, 21 Aug 2026

Inspected and partially repaired the three custom tools on agent
`Conversatio-87b9b435-b466` while wiring Gate 2.

## What was already correct

Authentication, on all three tools:

- Auth type: **Api Key**
- Name: `X-Loopline-Tool-Key`
- Location: **header**
- Value: **workspace secret reference**, not an inline string

This is the configuration the earlier attempt got wrong, and it is now right.

## Two defects found

### 1. Stale tunnel host

The endpoint URLs pointed at `grgnm-106-219-122-250.free.pinggy.net`, a tunnel from an
earlier session that no longer resolves. Paths were correct
(`/v1/tools/check-payment-status` etc.); only the host was dead.

Free pinggy tunnels rotate their subdomain on every restart, so this will recur every
time the tunnel is re-established. Three tool configs have to be re-pointed each time.

### 2. `account_id` mapped to the wrong variable

Both body fields were mapped to the same source:

```
run_id      -> campaignId            (correct)
account_id  -> campaignId            (WRONG — should be transactionReference)
```

This matters more than it looks. The evaluation adapter sets
`campaignId = run_id` and `transactionReference = account_id` per trial
(`research/upstream/eva/src/eva/assistant/samvaad_server.py`, lines 404–405). With both
fields drawing from `campaignId`, every request would claim the account id equals the
run id, so the store's account-ownership check — the thing that guarantees one trial
cannot touch another trial's state — would be comparing a value against itself.

The isolation guarantee would have looked like it was working while enforcing nothing.

Root cause: **`transactionReference` did not exist as an input variable on the agent**,
so it could not be selected. Created it (default `EC-DEMO-0001`).

## Repaired so far

| Tool | URL host | `account_id` mapping | Saved |
|---|---|---|---|
| `check_payment_status` | repointed | → `transactionReference` | yes |
| `record_promise_to_pay` | **still stale** | **still `campaignId`** | no |
| `schedule_callback` | **still stale** | **still `campaignId`** | no |

## Not yet proven

Indus's tool test returned *"Success — Tool returned no output"*, which is ambiguous:
it does not distinguish a reachable service returning an empty body from a request that
never arrived. The service had no inbound request logging at the time, so this could not
be resolved either way.

**No live tool effect has been captured.** The gate remains open.

## Change made to close that gap

Added an inbound request journal to `framework/tool_service.py`
(`artifacts/tool_service/inbound_requests.jsonl`). Every request is recorded with
timestamp, method, path, status, client host, user agent, whether a credential was
presented, and the parsed body — including requests that fail auth or name an unknown
run. The credential value itself is never written.

This makes the next test decisive: either a request from Sarvam's tool caller appears in
the journal, or it does not.

## Next steps

1. Restart the tunnel; capture the new URL.
2. Re-point all three tools; fix the two remaining `account_id` mappings.
3. Seed a run whose `run_id` matches the agent's `campaignId` default and whose
   `account_id` matches `transactionReference`.
4. Fire the Indus tool test against `record_promise_to_pay` — a **write** tool, so a
   successful call produces a state change rather than an empty read.
5. Confirm the journal entry and the before/after state diff. That pair is the Gate 2
   evidence.
