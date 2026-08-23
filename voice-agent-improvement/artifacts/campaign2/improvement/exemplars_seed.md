These are real calls this agent handled correctly. The pattern to copy is when the tool fires, not the wording.

**promise with a concrete date** (from a real call, EMI-BENCH-0021):
Customer: "हाँ बोलिए"
Shubh: "मैं EasyCredit से शुभ बात कर रहा हूँ। आपके Samsung Smart TV की चार हज़ार चार सौ सोलह रुपये की EMI overdue है। क्या आप अभी official EasyCredit app के ज़रिए payment कर सकते हैं?"
Customer: "सैलरी आने के बाद 04-09-2026 को कर दूँगा"
Shubh: "ठीक है, मैंने चार सितंबर के लिए note कर लिया है।"
Customer: "जी 04-09-2026, पक्का"
Shubh: "धन्यवाद Arnav जी, आपका दिन शुभ हो।"
Customer: "ठीक है, समझ गया"
Shubh: "धन्यवाद Arnav जी, आपका दिन शुभ हो।"
Journal after the call: record_promise_to_pay(date=04-09-2026); record_call_outcome(disposition=fptp)

**callback booked** (from a real call, EMI-SYNTH-0012):
Customer: "हाँ जी"
Shubh: "मैं EasyCredit से शुभ बात कर रहा हूँ। आपके Samsung Smart TV की चार हज़ार चार सौ सोलह रुपये की EMI overdue है। क्या आप अभी official EasyCredit app के ज़रिए payment कर सकते हैं?"
Customer: "अभी मैं मीटिंग में हूँ, कल सुबह दस बजे कॉल कीजिए"
Shubh: "ठीक है। मैं आपको कल सुबह दस बजे call करूँगा।"
Customer: "हाँ कल सुबह दस बजे ठीक है"
Shubh: "धन्यवाद Arnav जी, कल बात करते हैं।"
Journal after the call: schedule_callback(date=23-08-2026, time_window=10 AM to 11 AM); record_call_outcome(disposition=callback)

**refusal recorded** (from a real call, EMI-BENCH-0088):
Customer: "ਹਾਂ ਮੈਂ ਹੀ ਬੋਲ ਰਿਹਾ ਹਾਂ"
Shubh: "मैं EasyCredit से शुभ बात कर रहा हूँ। आपके Samsung Smart TV की चार हज़ार चार सौ सोलह रुपये की EMI overdue है। क्या आप अभी official EasyCredit app के ज़रिए payment कर सकते हैं?"
Customer: "ਮੈਨੂੰ ਨਹੀਂ ਦੇਣਾ, ਗੱਲ ਖਤਮ"
Shubh: "धन्यवाद Arnav जी।"
Customer: "ਠੀਕ ਹੈ, ਸਮਝ ਗਿਆ"
Shubh: "धन्यवाद Arnav जी, आपका दिन शुभ हो।"
Customer: "ਠੀਕ ਹੈ, ਹੋਰ ਕੁਝ ਨਹੀਂ"
Shubh: "धन्यवाद Arnav जी।"
Journal after the call: record_call_outcome(disposition=rtp)