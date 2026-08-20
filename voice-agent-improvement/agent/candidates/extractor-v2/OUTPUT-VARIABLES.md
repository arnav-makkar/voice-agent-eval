# Extractor V2 — precedence and outcome-integrity patch

Apply this patch after the frozen V11 output contract. The first matching outcome wins.

1. `escalation` — an explicit unauthorized-purchase or account-fraud claim, legal threat, mental-health risk, deceased customer, hostile abuse, or supervisor demand.
2. `alternate_number` — an alternate number was captured.
3. `wrong_number` — the person says they are not `userName`.
4. `dispute` — `userName` is the caller but denies the purchase, EMI, or amount.
5. Existing payment, promise, callback, refusal, acknowledgement, and disconnected outcomes in their frozen order.

A caller saying that the AI call, payment link, or channel “looks like a scam” is a trust objection, not an account-fraud claim. Do not use `escalation` for that phrase alone. If the caller also refuses to pay or continue, use the applicable refusal outcome.

Never return `fraud_claim`; it is not an allowed disposition. For a genuine unauthorized-transaction claim, use `disposition=escalation` with `escalationReason=fraud_claim` and a factual comment.

`payment_ready` requires an explicit present-tense commitment to open or log in to the official app and pay now. “I will check,” “I will try,” or “I will verify” is `acknowledged` unless another terminal outcome has priority.

Output extraction may classify only transcript and successful tool evidence. It must not claim payment completed, records changed, escalation executed, or a callback booked without a successful supporting tool event.
