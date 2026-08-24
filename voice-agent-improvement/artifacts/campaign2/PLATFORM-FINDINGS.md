# Platform findings, campaign 2

Surfaced by the evaluation and about the Indus runtime rather than the agent under test.
Kept here after the site's Findings page was removed for the demo cut.

## The "are you still there" prompt is rude in Hindi

After five seconds of silence the runtime speaks its own line. The stock Hindi text uses the intimate, disrespectful form of "you", injected into a call where the agent has been formal and polite throughout. It is generated from an English source string and was never checked for register.

It was caught only because every transcript gets read rather than sampled.

## Two channels handle per-call settings differently

Phone and live voice channels accept settings passed with each individual call. The typed chat channel quietly ignores them and uses stored defaults instead. Since one of those settings decides which account a call writes to, this determines how every tier keeps its evidence separate. Getting it wrong would silently mix two calls together.

## The runtime serves the draft directly

There is no separate publish step: the live agent runs whatever the draft currently says, and the version number is a revision counter rather than a release pointer. Version control therefore has to live in this project's own fingerprint checks, not in the platform.

## Two different models, one instruction manual

Conversation runs on one model; deciding which action to take runs on a smaller, separate one. Every improvement here was achieved by instruction text steering that second, smaller model. Worth knowing before writing rules for this stack.
