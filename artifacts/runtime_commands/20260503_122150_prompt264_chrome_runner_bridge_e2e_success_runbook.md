# Prompt264 Chrome Runner Bridge E2E Success Runbook

## Status

Chrome extension bridge MVP reached end-to-end success.

## Confirmed path

```text
request.md
→ local bridge server
→ Chrome extension / ChatGPT Runner Bridge
→ logged-in normal Chrome ChatGPT tab
→ visible composer insertion
→ real send-button click
→ user message detected
→ assistant final response captured
→ response.md written
```

## Final smoke result

```text
response.md
OK
```

## Important intermediate confirmation

```text
status=sent
reason=user_message_detected
send_method=button_click

selected composer:
  role=textbox
  contenteditable=true
  visible=true

selected submit candidate:
  data-testid=send-button
  aria_label=プロンプトを送信する
  visible=true
  disabled=false
  in_same_form_as_composer=true
```

## Current stable polling configuration

```javascript
const RESPONSE_TIMEOUT_MS = 600000;
const RESPONSE_POLL_INTERVAL_MS = 10000;
const STABLE_POLLS_REQUIRED = 3;
const USER_MESSAGE_CONFIRM_TIMEOUT_MS = 30000;
const USER_MESSAGE_RETRY_INTERVAL_MS = 10000;
```

## Meaning

```text
assistant final response wait:
  max 10 minutes
  poll every 10 seconds
  save only after the same non-transient response is stable for 3 polls

user message confirmation:
  max 30 seconds
  poll every 10 seconds
```

This is intentionally conservative to reduce excessive polling and avoid saving transient states such as:

```text
思考中
Thinking
Generating
```

# One-run operating procedure

## 1. Stop old bridge server

```bash
cd /home/rai/codex-local-runner

pkill -f "scripts/chatgpt_bridge_server.py" || true
pkill -f "chatgpt_bridge_server.py" || true

curl -v http://127.0.0.1:8765/status
```

Expected stopped state:

```text
Connection refused
```

## 2. Start bridge server

Open a dedicated WSL terminal:

```bash
cd /home/rai/codex-local-runner
python scripts/chatgpt_bridge_server.py
```

Expected output:

```text
ChatGPT bridge server listening on http://0.0.0.0:8765
request.md: /tmp/codex-local-runner-chatgpt-bridge/request.md
response.md: /tmp/codex-local-runner-chatgpt-bridge/response.md
status.json: /tmp/codex-local-runner-chatgpt-bridge/status.json
```

Keep this terminal open.

## 3. Confirm server from another terminal

```bash
curl -s http://127.0.0.1:8765/status
```

Expected:

```json
{"status": "idle"}
```

## 4. Reload Chrome extension

In Chrome:

```text
chrome://extensions
→ ChatGPT Runner Bridge
→ Reload / 更新 / ↻
```

Confirm no red extension errors.

## 5. Create normal request

```bash
rm -f /tmp/codex-local-runner-chatgpt-bridge/status.json
rm -f /tmp/codex-local-runner-chatgpt-bridge/response.md

cat > /tmp/codex-local-runner-chatgpt-bridge/request.md <<'REQ'
テストです。短く「OK」とだけ返してください。
REQ

curl -s http://127.0.0.1:8765/next-task
```

Expected:

```json
{"has_task": true, "prompt": "テストです。短く「OK」とだけ返してください。\n"}
```

## 6. Start 10-second monitor

```bash
while true; do
  clear
  date
  echo "---- status.json ----"
  cat /tmp/codex-local-runner-chatgpt-bridge/status.json 2>/dev/null || echo "status.json not found yet"
  echo
  echo "---- response.md ----"
  cat /tmp/codex-local-runner-chatgpt-bridge/response.md 2>/dev/null || echo "response.md not found yet"
  sleep 10
done
```

Stop with:

```text
Ctrl + C
```

## 7. Run in Chrome

In normal logged-in Chrome:

```text
https://chatgpt.com/
→ new chat
→ empty composer
→ Verify/CAPTCHA not visible
→ click ChatGPT Runner Bridge once
```

Do not click repeatedly.

## 8. Success criteria

Expected status progression:

```text
running / task_fetched
running / composer_found
running / prompt_inserted
running / submit_candidates_collected
running / submit_attempted
sent / user_message_detected
response_saved / result_saved
```

Final expected file:

```bash
cat /tmp/codex-local-runner-chatgpt-bridge/response.md
```

Expected:

```text
OK
```

# Diagnostic mode

Use diagnostic mode when composer/submit target detection seems unstable.

```bash
rm -f /tmp/codex-local-runner-chatgpt-bridge/status.json
rm -f /tmp/codex-local-runner-chatgpt-bridge/response.md

cat > /tmp/codex-local-runner-chatgpt-bridge/request.md <<'REQ'
[BRIDGE_DIAGNOSE_ONLY]
テストです。短く「OK」とだけ返してください。
REQ

curl -s http://127.0.0.1:8765/next-task
```

Then click ChatGPT Runner Bridge once.

Expected diagnostic behavior:

```text
composer is selected
prompt is inserted
submit candidates are collected
no submit click happens
status=diagnostic_ready
reason=diagnostic_only
```

# Troubleshooting

## response.md contains 思考中 / Thinking

Cause:

```text
transient assistant status was captured too early
```

Fix:

```text
Keep transient-skip logic enabled.
Use conservative polling:
RESPONSE_POLL_INTERVAL_MS=10000
STABLE_POLLS_REQUIRED=3
```

## submit_not_confirmed

Cause:

```text
prompt insertion may have succeeded, but user message did not appear in conversation DOM
```

Check:

```text
selected submit candidate should be:
data-testid=send-button
aria_label=プロンプトを送信する
visible=true
disabled=false
in_same_form_as_composer=true
```

## run_in_progress

Cause:

```text
extension icon was clicked more than once during a run
```

Fix:

```text
close/reload ChatGPT tab
clear status/response files
recreate request.md
click extension once only
```

## Mixed Content

Cause:

```text
content.js directly fetched http://... from https://chatgpt.com
```

Expected architecture:

```text
content.js
→ chrome.runtime.sendMessage
→ background.js
→ fetch http://<WSL-IP>:8765
```

content.js must not directly fetch the bridge HTTP URL.

# Next development direction

Recommended next step:

```text
Prompt265:
  Connect response.md ingestion into planned_execution_runner.py or the dev_loop_mvp surface.
```

Keep Prompt265 small:

```text
- read response.md
- validate response is non-empty and non-transient
- parse structured JSON only when expected
- expose bridge response status in compact summary/supporting truth refs/final payload
- do not add Playwright
- do not add ChatGPT API
- do not add loops/daemon/scheduler
```
