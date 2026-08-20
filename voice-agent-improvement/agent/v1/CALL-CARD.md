# Frozen v10 voice-validation card — Samsung TV EMI recovery

All people, companies, account data, and outcomes are synthetic. The card is for controlled calls to the project owner's consenting phone only.

## Fixed account facts

| Field | Synthetic value |
|---|---|
| Customer | Arnav |
| Lender / merchant | EasyCredit Finance |
| Retailer | Croma |
| Product | Samsung TV |
| EMI | 7 of 12; 9 remaining |
| EMI amount | ₹4,166 |
| Due date | 11-08-2026 |
| Days overdue at baseline | 6 |
| Late charge | ₹250 |
| Total outstanding | ₹4,416 |
| Payment route | Official EasyCredit demo app → Help → EMI & repayments |

The agent must never claim that payment succeeded because this build has no payment-status tool.

## Five matched human scripts

Run each script once on v10 and once on the frozen final candidate. Use the same caller, facts, wording at branch points, and scoring rules.

1. **Immediate payment:** confirm the name, sound uninterested, then agree only after a direct ask to open the official app and pay now.
2. **App trust objection:** say you will not click a payment link. Agree only if the agent tells you to use the official app without sharing credentials.
3. **Vague delay:** say “baad mein dekhunga.” Agree only if the agent gives a short concrete reason and asks you to open the app now within two recovery attempts.
4. **Busy callback:** say you cannot talk. Give 18-08-2026 at 18:00 IST only if asked for both date and time.
5. **Transaction dispute:** say you do not recognize the Samsung TV purchase. The agent must stop recovery, avoid further payment pressure, and provide the official support route.

## Primary result

Full success requires an explicit statement equivalent to: “I will open/login to the official app and pay now.” Acknowledgement, “I will see,” a future promise, callback, dispute, or correct disposition does not count as primary TSR.

Do not include no-answer attempts in this agent-quality denominator.
