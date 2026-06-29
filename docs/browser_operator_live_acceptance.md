# Browser Operator Live Acceptance

This is the Prompt659 operator-controlled acceptance path for the Prompt658
ChatGPT browser operator adapter. It prepares local request artifacts and
validates a response envelope exported by the browser extension flow.

The harness does not launch a browser, read browser profiles, bypass login,
store cookies, store passwords, store tokens, call ChatGPT APIs, push, merge, or
execute generated prompts.

## Prepare

```bash
python scripts/run_operator_controlled_browser_live_acceptance.py prepare \
  --repo-root /home/rai/codex-local-runner \
  --work-root /tmp/codex-local-runner-prompt659-browser-live
```

This writes:

- `/tmp/codex-local-runner-prompt659-browser-live/request_envelope.json`
- `/tmp/codex-local-runner-prompt659-browser-live/expected_response_envelope_schema.json`

## Operator Browser Run

1. Open Chrome or Edge.
2. Load the unpacked extension from
   `/home/rai/codex-local-runner/browser_extension/chatgpt_runner_bridge`.
3. Open `https://chatgpt.com/` in a normal tab using an already logged-in user
   session.
4. Do not export, copy, or store cookies, passwords, tokens, browser profile
   data, or account/session pages.
5. Open
   `/tmp/codex-local-runner-prompt659-browser-live/request_envelope.json`.
6. Paste/import the full request envelope JSON into the Prompt658 extension
   bridge flow on the visible ChatGPT tab.
7. Submit the request through the operator-controlled extension/content flow.
8. Save the exported `browser_chatgpt_response_envelope_v1` JSON as
   `/tmp/codex-local-runner-prompt659-browser-live/live_response_envelope.json`.

## Validate

```bash
python scripts/run_operator_controlled_browser_live_acceptance.py validate-response \
  --repo-root /home/rai/codex-local-runner \
  --work-root /tmp/codex-local-runner-prompt659-browser-live \
  --response-envelope /tmp/codex-local-runner-prompt659-browser-live/live_response_envelope.json
```

Prompt659 success is allowed only when the exported response envelope is real
browser output, has the expected request id, has a capture timestamp, contains no
credential-like fields, normalizes into `analysis_artifact_v1`, validates through
Prompt657, converts into a Prompt655-compatible prompt batch, and produces a next
prompt selection.
