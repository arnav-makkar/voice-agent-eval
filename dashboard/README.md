# Presentation site

A Next.js shell whose only job is to serve the static walkthrough under
`public/c2/` and the call evidence under `public/evidence/`.

```bash
npm install
npm run dev     # http://localhost:3000 → redirects to /c2/overview.html
```

Seven sections, one page each, in the order of the talk:
overview → the failure mode → the instrument → diagnosis → the loop →
results → call evidence → limits & references.

`public/evidence/audio/{phone-v3,phone-v4,bot-v3,bot-v4}/` each carry an
`index.json` (transcript, journal writes, verdicts, durations) plus the call
mp3s — 40 calls in total, playable from the Call evidence page.
