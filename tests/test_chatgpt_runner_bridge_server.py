"""Prompt659A tests for the ChatGPT Runner Bridge compatibility server."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.browser_chatgpt_operator_adapter import (
    BROWSER_RESPONSE_ENVELOPE_SCHEMA,
)
from automation.orchestration.planned_runner.chatgpt_runner_bridge_server import (
    DEFAULT_HOST,
    DEFAULT_REQUEST_ID,
    PROTOCOL_CLASSIFICATION,
    accept_response_envelope,
    create_server,
    current_status,
    dispatch_local_request,
    dispatch_raw_local_request,
    inspect_protocol,
    prepare_bridge_work,
    run_once_if_response_present,
)
from automation.orchestration.planned_runner.external_analysis_handoff import validate_analysis_artifact

REPO_ROOT = Path(__file__).resolve().parents[1]


def _artifact(**overrides):
    artifact = {
        "schema_version": "analysis_artifact_v1",
        "request_id": DEFAULT_REQUEST_ID,
        "source": "chatgpt_browser",
        "status": "success",
        "current_state_summary": "The local bridge server accepted and validated a browser response envelope.",
        "confirmed_completed": ["Prompt658 adapter", "Prompt659A bridge server"],
        "missing_gaps": ["Run with the live browser extension."],
        "recommended_next_action": "generate_prompt_batch",
        "recommended_prompts": [
            {
                "prompt_id": "prompt660",
                "title": "Browser to Codex full cycle acceptance",
                "body": "Validate the browser-to-Codex full cycle using local artifacts only and do not execute generated prompts.",
                "expected_tag": "prompt660-browser-to-codex-full-cycle-acceptance",
                "expected_report_path": "artifacts/autonomous_runtime/prompt660_report.json",
                "expected_summary_path": "artifacts/autonomous_runtime/prompt660_summary.md",
                "required_tests": ["python -m unittest tests.test_chatgpt_runner_bridge_server"],
                "pass_conditions": {"status_field": "prompt660_status", "status_value": "success"},
            }
        ],
        "evaluation_score_out_of_100": 90,
        "risk_notes": ["Keep browser credentials outside bridge artifacts."],
    }
    artifact.update(overrides)
    return artifact


def _response(**overrides):
    payload = {
        "schema_version": BROWSER_RESPONSE_ENVELOPE_SCHEMA,
        "adapter": "browser_chatgpt_operator_adapter",
        "request_id": DEFAULT_REQUEST_ID,
        "status": "artifact_ready",
        "chatgpt_output": json.dumps(_artifact()),
        "require_structured_artifact": True,
        "captured_at": "2026-06-17T00:00:00Z",
        "metadata": {"page_url": "https://chatgpt.com/c/prompt659a"},
        "errors": [],
    }
    payload.update(overrides)
    return payload


class ChatgptRunnerBridgeServerTests(unittest.TestCase):
    def test_historical_protocol_inspection_returns_deterministic_classification(self):
        result = inspect_protocol(REPO_ROOT)
        self.assertEqual(result["old_protocol_classification"], PROTOCOL_CLASSIFICATION)
        self.assertTrue(result["old_endpoints_found"])
        self.assertIn("/next-task", result["expected_endpoints"]["legacy"])
        self.assertIn("/result", result["expected_endpoints"]["legacy"])

    def test_prepare_writes_request_envelope(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = prepare_bridge_work(repo_root=REPO_ROOT, work_root=raw)
            self.assertEqual(result["status"], "success", msg=result["errors"])
            request_path = Path(result["request_envelope_path"])
            self.assertTrue(request_path.is_file())
            payload = json.loads(request_path.read_text())
            self.assertEqual(payload["schema_version"], "browser_chatgpt_request_envelope_v1")

    def test_server_binds_to_loopback_by_default_and_health_returns_ok(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            prepare_bridge_work(repo_root=REPO_ROOT, work_root=raw)
            status, payload = dispatch_local_request(
                method="GET",
                path="/health",
                repo_root=REPO_ROOT,
                work_root=raw,
            )
            self.assertEqual(DEFAULT_HOST, "127.0.0.1")
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"], "ok")

    def test_request_endpoint_returns_prepared_envelope(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            prepare_bridge_work(repo_root=REPO_ROOT, work_root=raw)
            status, payload = dispatch_local_request(method="GET", path="/request", repo_root=REPO_ROOT, work_root=raw)
            self.assertEqual(status, 200)
            self.assertEqual(payload["schema_version"], "browser_chatgpt_request_envelope_v1")
            status, task = dispatch_local_request(method="GET", path="/next-task", repo_root=REPO_ROOT, work_root=raw)
            self.assertEqual(status, 200)
            self.assertTrue(task["has_task"])
            self.assertIn("browser_chatgpt_request_envelope_v1", task["prompt"])

    def test_response_endpoint_rejects_malformed_json(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            status, payload = dispatch_raw_local_request(
                method="POST",
                path="/response",
                raw_body=b"{not json",
                repo_root=REPO_ROOT,
                work_root=raw,
            )
            self.assertEqual(status, 400)
            self.assertTrue(any("malformed JSON" in e for e in payload["errors"]))

    def test_response_endpoint_rejects_wrong_request_id(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            status, payload = dispatch_local_request(
                method="POST",
                path="/response",
                body=_response(request_id="wrong"),
                repo_root=REPO_ROOT,
                work_root=raw,
            )
            self.assertEqual(status, 400)
            self.assertTrue(any("request_id" in e for e in payload["errors"]))

    def test_response_endpoint_rejects_credential_like_fields(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            status, payload = dispatch_local_request(
                method="POST",
                path="/response",
                body=_response(metadata={"page_url": "https://chatgpt.com", "session_token": "nope"}),
                repo_root=REPO_ROOT,
                work_root=raw,
            )
            self.assertEqual(status, 400)
            self.assertTrue(any("secret-like" in e for e in payload["errors"]))

    def test_response_endpoint_accepts_valid_envelope_and_converts(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            status, payload = dispatch_local_request(
                method="POST",
                path="/response",
                body=_response(),
                repo_root=REPO_ROOT,
                work_root=raw,
            )
            self.assertEqual(status, 200, msg=payload.get("errors"))
            self.assertEqual(payload["status"], "success")
            self.assertTrue(payload["analysis_artifact_normalized"])
            self.assertTrue(payload["prompt657_validation_compatibility_verified"])
            self.assertTrue(payload["prompt655_batch_conversion_compatibility_verified"])
            self.assertTrue(payload["next_prompt_selection_verified"])
            artifact = json.loads((Path(raw) / "analysis_artifact.json").read_text())
            _, errors = validate_analysis_artifact(artifact)
            self.assertEqual(errors, [])

    def test_legacy_result_endpoint_accepts_stringified_response_envelope(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = accept_response_envelope(
                {"response": json.dumps(_response()), "metadata": {"page_url": "https://chatgpt.com"}},
                repo_root=REPO_ROOT,
                work_root=raw,
                legacy_result_payload=True,
            )
            self.assertEqual(result["status"], "success", msg=result["errors"])
            self.assertTrue((Path(raw) / "response_envelope.json").is_file())

    def test_status_endpoint_reflects_request_and_response_state(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            prepare_bridge_work(repo_root=REPO_ROOT, work_root=raw)
            status = current_status(raw)
            self.assertTrue(status["request_prepared"])
            self.assertFalse(status.get("response_present", False))
            result = accept_response_envelope(_response(), repo_root=REPO_ROOT, work_root=raw)
            self.assertEqual(result["status"], "success", msg=result["errors"])
            status = current_status(raw)
            self.assertTrue(status["response_present"])

    def test_run_once_if_response_present_returns_partial_without_response(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = run_once_if_response_present(repo_root=REPO_ROOT, work_root=raw)
            self.assertEqual(result["status"], "partial")
            self.assertIn("not_ready", result["reason"])

    def test_no_remote_network_browser_automation_env_or_secret_storage(self):
        import automation.orchestration.planned_runner.chatgpt_runner_bridge_server as mod

        src = Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("requests", src)
        self.assertNotIn("urllib", src)
        self.assertNotIn("sync_playwright", src)
        self.assertNotIn("async_playwright", src)
        self.assertNotIn("document.cookie", src)
        self.assertNotIn("localStorage", src)
        self.assertNotIn("sessionStorage", src)
        self.assertNotIn(".env", src)

    def test_server_rejects_non_loopback_host(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            with self.assertRaises(ValueError):
                create_server(repo_root=REPO_ROOT, work_root=raw, host="0.0.0.0", port=0)


if __name__ == "__main__":
    unittest.main()
