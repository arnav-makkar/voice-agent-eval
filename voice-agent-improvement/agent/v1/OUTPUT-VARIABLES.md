# Frozen v11 output contract

These are the output variables currently used by the direct EMI-recovery agent. Keep their extraction logic stable during baseline generation.

## Primary disposition

`disposition` is an enum with:

`escalation`, `alternate_number`, `wrong_number`, `dispute`, `payment_ready`, `ptp_today`, `fptp`, `callback`, `rtp`, `already_paid`, `acknowledged`, `call_disconnected`.

Apply the deployed priority funnel. `payment_ready` means the customer explicitly agreed to open/login to the official app and pay now. `ptp_today` means later today, not immediately. `fptp` means tomorrow or another confirmed future date. Acknowledgement or a vague promise is not any payment commitment.

The Indus call goal is `disposition = payment_ready`. This is an operational signal only; final CPCR uses the human-labelled audio/transcript evidence.

## Supporting outputs

- `identityConfirmed`: `true` when the person confirms they are the named customer; no OTP, reference, consent script, or additional verification is required in v10.
- `promisedToPayDate`: confirmed absolute date in `DD-MM-YYYY`, otherwise empty/`NA` according to the deployed extraction prompt.
- `callbackPreferredDate`: final confirmed absolute callback date, otherwise empty.
- `callbackPreferredTime`: final confirmed time or narrow window with IST, otherwise empty.
- `callbackDateTime`: natural-language callback time captured by the deployed extractor.
- `disputeReason`: one factual phrase from the caller; never infer fraud.
- `callSummary`: concise factual identity, issue, stance, and final outcome.
- `escalationReason`: one deployed controlled reason or `NA`.
- `escalationComment`: factual trigger summary or `NA`.
- `userUpdatedNumber`: digits only if an alternate number was actually provided; otherwise `NA`/empty.
- `paymentLinkSent`: remains the input fact `false`; the control has no real link-sending tool.

## Evaluation boundary

Indus extraction is an operational signal, not unquestioned ground truth. Phase 2 compares it with deterministic transcript evidence and a human-labelled calibration slice. The project reports disagreements instead of silently overwriting them.
