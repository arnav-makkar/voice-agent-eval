# V13 output extractor patch

This is separate from the spoken prompt. The baseline proved that a good spoken fraud response can still produce an invalid output enum.

For `disposition`, keep the existing allowed values and change the extraction rule so the first matching outcome wins:

1. `escalation` — fraud claim, legal threat, mental-health risk, deceased customer, hostile abuse, or supervisor demand.
2. `alternate_number` — alternate number captured.
3. `wrong_number` — the person is not `userName`.
4. `dispute` — `userName` confirms identity but denies the purchase, EMI, or amount.
5. Existing payment and callback outcomes in their current order.

Never return `fraud_claim`; it is not an allowed disposition. Put the detail in `escalationReason=fraud_claim` and `escalationComment`.

Integrity rule: output extraction may summarize or classify only what happened in the transcript. It must not say that payment completed, records were updated, escalation was executed, or a callback was booked unless a successful tool event proves it.
