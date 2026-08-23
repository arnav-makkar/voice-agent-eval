These are real calls this agent handled correctly. Copy **when** each tool fires and **which** fields it takes. Do not reuse the argument values: each one below was derived from what that particular customer said, and yours must be derived the same way from the call you are on.

**promise with a concrete date** (from a real call, EMI-BENCH-0021):
Customer: "हाँ बोलिए"
Shubh: "मैं EasyCredit से शुभ बात कर रहा हूँ। आपके Samsung Smart TV की चार हज़ार चार सौ सोलह रुपये की EMI overdue है। क्या आप अभी official EasyCredit app के ज़रिए payment कर सकते हैं?"
Customer: "सैलरी आने के बाद 04-09-2026 को कर दूँगा"
Shubh: "ठीक है, मैंने चार सितंबर के लिए note कर लिया है।"
Customer: "जी 04-09-2026, पक्का"
Shubh: "धन्यवाद Arnav जी, आपका दिन शुभ हो।"
Customer: "ठीक है, समझ गया"
Shubh: "धन्यवाद Arnav जी, आपका दिन शुभ हो।"
Journal after the call: record_promise_to_pay(date=04-09-2026 (derived from what this customer said, not a fixed value)); record_call_outcome(disposition=fptp)

**callback booked** (from a real call, EMI-SYNTH-0012):
Customer: "हाँ जी"
Shubh: "मैं EasyCredit से शुभ बात कर रहा हूँ। आपके Samsung Smart TV की चार हज़ार चार सौ सोलह रुपये की EMI overdue है। क्या आप अभी official EasyCredit app के ज़रिए payment कर सकते हैं?"
Customer: "अभी मैं मीटिंग में हूँ, कल सुबह दस बजे कॉल कीजिए"
Shubh: "ठीक है। मैं आपको कल सुबह दस बजे call करूँगा।"
Customer: "हाँ कल सुबह दस बजे ठीक है"
Shubh: "धन्यवाद Arnav जी, कल बात करते हैं।"
Journal after the call: schedule_callback(date=23-08-2026 (derived from what this customer said, not a fixed value), time_window=10 AM to 11 AM (derived from what this customer said, not a fixed value)); record_call_outcome(disposition=callback)