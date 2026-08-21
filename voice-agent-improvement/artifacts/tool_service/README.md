# Tool-service inbound journal

`inbound_requests.jsonl` is the append-only record of every HTTP request that
reached the run-scoped tool service. It is the evidence that separates a tool
call the agent *claimed* from one it actually made.

## client_host values

| Value | Meaning |
|---|---|
| `4.213.167.70` | Sarvam's documented Voice Agents tool-caller. A request from here is **platform-originated** — the deployed agent really invoked the tool. |
| `127.0.0.1` | Local harness traffic: seeding runs, verification checks. |
| `tunnel-origin-redacted` | Requests that arrived through the operator's temporary public tunnel from their own network. |

## Disclosed redaction

The `tunnel-origin-redacted` value replaces a residential IP address that was
present in the original records. The address was the operator's own home IP,
embedded in the hostnames of a temporary tunnel that has long since expired.

The substitution is one-way and applied uniformly, so the analytically
meaningful distinction is fully preserved: platform-originated requests remain
separable from tunnel-origin and local ones. No timestamp, path, status code,
credential flag or body was altered.

This is recorded here rather than performed silently, because the journal is
cited as evidence and any change to evidence should be visible.
