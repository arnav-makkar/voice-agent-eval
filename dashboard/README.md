# Loopline

Local evidence dashboard for the Sarvam Indus self-improving voice-agent framework.

Loopline keeps five product views separate:

- **Overview** — the evaluate → improve → decide control loop and execution ledger.
- **Evaluate** — replayable multi-turn episodes, first-failure localization, tool events, and final state.
- **Improve** — candidate ladder, GEPA lineage, MLflow IDs, and component repair registry.
- **Decide** — paired release conditions, fresh-final seal/access, and voice-transfer status.
- **Monitor** — the redacted real Indus call corpus and trace-level failures.

The snapshot is generated from versioned framework artifacts; it does not call Sarvam or Gemini from the browser.

## Refresh evidence

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/voice-agent-improvement
source .venv/bin/activate
python -m framework.export_dashboard
```

## Run locally

```bash
cd /Users/Arnav/Claude/Projects/Sarvam/dashboard
npm run dev
```

## Verify

```bash
npm run lint
npm test
```

The dashboard is intentionally not published by default because its local snapshot contains controlled call transcripts and experiment evidence. Sanitize or protect the dataset before hosting.
