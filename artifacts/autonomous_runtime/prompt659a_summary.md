# Prompt659A Summary

Status: success.

Inspection found that the old ChatGPT Runner Bridge used a local runner server
protocol. The historical background script fetched `/next-task`, posted
`/status`, and posted `/result`; the historical server lived at
`scripts/chatgpt_bridge_server.py` and used `request.md`, `response.md`, and
`status.json`. The old server bound to `0.0.0.0`, so the new compatibility
server binds to `127.0.0.1` by default and rejects non-loopback hosts.

Implemented:

- `automation/orchestration/planned_runner/chatgpt_runner_bridge_server.py`
- `scripts/run_chatgpt_runner_bridge_server.py`
- `tests/test_chatgpt_runner_bridge_server.py`

Supported endpoints:

- Legacy extension protocol: `GET /next-task`, `POST /status`, `POST /result`
- Envelope-native protocol: `GET /health`, `GET /request`, `POST /response`,
  `GET /status`

Validation:

- Prompt659A targeted tests passed.
- Full requested targeted regression set passed: 171 tests.
- Response envelopes validate through the Prompt658 adapter, normalize to
  `analysis_artifact_v1`, validate through Prompt657, convert to a
  Prompt655-compatible prompt batch, and produce next-prompt selection.

No browser live run was performed or claimed.

Next action:

```bash
python scripts/run_chatgpt_runner_bridge_server.py serve \
  --repo-root /home/rai/codex-local-runner \
  --work-root /tmp/codex-local-runner-chatgpt-bridge \
  --host 127.0.0.1 \
  --port 8765
```
