# ChatGPT Runner Bridge

Prompt658 adapter for operator-controlled ChatGPT browser handoff.

Provenance:

- reused_from_commit: `d698389`
- reused_path: `browser_extension/chatgpt_runner_bridge/content.js`

## Safety Boundary

This extension operates only in a visible ChatGPT page that the operator opens.
It does not store browser credentials, cookies, tokens, passwords, or account data in
the repository. It does not bypass login, Verify, or CAPTCHA. The repo-side adapter
validates JSON envelopes offline and does not launch a browser.

## Envelope Flow

1. Create a `browser_chatgpt_request_envelope_v1` with:

   ```bash
   python scripts/run_browser_chatgpt_operator_adapter.py create-request-envelope \
     --request prompts/analysis_requests/example_chatgpt_analysis_request.md \
     --output /tmp/chatgpt_browser_request_envelope.json
   ```

2. Place that JSON envelope in the local bridge request input used by the operator.
3. Open ChatGPT manually in Chrome or Edge.
4. Load this directory as an unpacked extension.
5. Click the extension or enable the explicitly controlled run mode.
6. The content script submits the prompt and captures the ChatGPT response.
7. The result is emitted as `browser_chatgpt_response_envelope_v1`.
8. Validate and normalize offline:

   ```bash
   python scripts/run_browser_chatgpt_operator_adapter.py validate-response-envelope \
     --response /tmp/chatgpt_browser_response_envelope.json

   python scripts/run_browser_chatgpt_operator_adapter.py normalize-to-analysis-artifact \
     --response /tmp/chatgpt_browser_response_envelope.json \
     --output artifacts/autonomous_runtime/external_analysis/from_browser_artifact.json
   ```

## Live Acceptance

Live acceptance is optional and operator controlled. Do not claim live browser
acceptance unless the extension is loaded, a ChatGPT tab is manually opened, and the
produced envelope validates through the repo-side adapter and Prompt657.

## Windows + WSL Bridge URL

The default bridge URL is `http://127.0.0.1:8765`. Keep that default when Chrome
or Edge can reach the WSL listener through loopback.

If Windows can connect but resets the loopback request, use an explicit private
WSL IP bind. Do not bind to `0.0.0.0`.

1. In WSL, get the private WSL IP:

   ```bash
   hostname -I | awk '{print $1}'
   ```

2. Start the bridge server with the private bind flag:

   ```bash
   python scripts/run_chatgpt_runner_bridge_server.py serve \
     --repo-root /home/rai/codex-local-runner \
     --work-root /tmp/codex-local-runner-chatgpt-bridge \
     --host <WSL_IP> \
     --port 8765 \
     --allow-private-host-bind
   ```

3. From Windows PowerShell, verify reachability:

   ```powershell
   curl.exe http://<WSL_IP>:8765/health
   ```

4. Open the extension options page and set the bridge base URL:

   ```text
   http://<WSL_IP>:8765
   ```

   The extension accepts only `http://127.0.0.1:8765`, `http://localhost:8765`,
   or private IPv4 URLs in `10.0.0.0/8`, `172.16.0.0/12`, and
   `192.168.0.0/16`. Public URLs, credential-bearing URLs, paths, queries,
   fragments, and `0.0.0.0` are rejected.

5. Reload the ChatGPT tab and click the extension.

The extension manifest includes broad HTTP host permission so Chrome can fetch a
configured private WSL IP. The background script validates the configured URL
before every bridge request and does not store credentials, cookies, tokens, or
passwords.
