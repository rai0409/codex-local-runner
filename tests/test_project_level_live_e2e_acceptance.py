"""Prompt654: non-live tests for the project-level live E2E acceptance harness.

These tests NEVER run a live daemon/Codex: they inject a fake bridge_runner, fake
cloner, and fake head_reader. They prove the harness gating, /tmp safety, real-outcome
handling, and that failures never mark the project complete.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_project_level_live_e2e_acceptance as harness  # noqa: E402

from automation.orchestration.planned_runner.project_live_execution_bridge import (  # noqa: E402
    DEFAULT_EXPECTED_ENABLE_TOKEN,
    run_project_live_execution_bridge,
)

_FIXED_HEAD = "deadbeefcafebabe0000000000000000deadbeef"


def _fake_cloner(src, dest):
    Path(dest).mkdir(parents=True, exist_ok=True)
    return dest


def _fake_head_reader_factory(seq):
    vals = list(seq)
    def _reader(repo):
        return vals.pop(0) if vals else _FIXED_HEAD
    return _reader


def _bridge_dry(intent, descriptors, output_queue_dir, **kwargs):
    return {
        "status": "success", "live_execution_performed": False, "dry_run": True,
        "errors": [], "warnings": ["dry-run"], "queue_dir": output_queue_dir,
        "daemon_run_summary": {"would_run": True}, "completion_gate_result": {},
        "project_complete": False, "next_action": "continue_project_loop",
    }


def _bridge_live_complete(intent, descriptors, output_queue_dir, **kwargs):
    return {
        "status": "success", "live_execution_performed": True, "dry_run": False,
        "errors": [], "warnings": [], "queue_dir": output_queue_dir,
        "daemon_run_summary": {"task_results": {"prompt654-live-e2e-t000": "done"}},
        "completion_gate_result": {"status": "complete", "complete": True},
        "project_complete": True, "next_action": "complete",
    }


def _bridge_live_failed(intent, descriptors, output_queue_dir, **kwargs):
    return {
        "status": "blocked", "live_execution_performed": True, "dry_run": False,
        "errors": [], "warnings": [], "queue_dir": output_queue_dir,
        "daemon_run_summary": {"task_results": {"prompt654-live-e2e-t000": "failed"}},
        "completion_gate_result": {"status": "failed", "complete": False},
        "project_complete": False, "next_action": "manual_review_required",
    }


def _bridge_live_partial(intent, descriptors, output_queue_dir, **kwargs):
    return {
        "status": "partial", "live_execution_performed": True, "dry_run": False,
        "errors": ["daemon outcome parsing unreliable"], "warnings": [],
        "queue_dir": output_queue_dir, "daemon_run_summary": {"task_results": {}},
        "completion_gate_result": {}, "project_complete": False,
        "next_action": "manual_review_required",
    }


def _run(work_root, queue_dir, **over):
    kw = dict(
        repo="/home/rai/codex-local-runner",
        work_root=work_root, queue_dir=queue_dir,
        cloner=_fake_cloner, head_reader=_fake_head_reader_factory([_FIXED_HEAD, _FIXED_HEAD]),
        bridge_runner=_bridge_dry,
    )
    kw.update(over)
    return harness.run_live_e2e_acceptance(**kw)


class LiveE2EAcceptanceHarnessTests(unittest.TestCase):
    def test_dry_run_default_no_live(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = _run(raw, str(Path(raw) / "queue"))
            self.assertEqual(r["prompt654_status"], "success")
            self.assertEqual(r["live_acceptance_status"], "dry_run")
            self.assertFalse(r["live_execution_performed"])
            self.assertTrue(r["main_repo_head_unchanged_during_live_run"])

    def test_non_tmp_work_root_blocked(self):
        r = _run("/home/rai/not_tmp", "/tmp/x/queue")
        self.assertEqual(r["prompt654_status"], "blocked")
        self.assertFalse(r["live_execution_performed"])

    def test_non_tmp_queue_dir_blocked(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = _run(raw, "/home/rai/queue")
            self.assertEqual(r["prompt654_status"], "blocked")

    def test_missing_repo_blocked(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = _run(raw, str(Path(raw) / "queue"), repo="/no/such/repo")
            self.assertEqual(r["prompt654_status"], "blocked")

    def test_live_requires_token_real_bridge(self):
        # Use the REAL bridge with a wrong token: it must block BEFORE any daemon run.
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = _run(
                raw, str(Path(raw) / "queue"),
                bridge_runner=run_project_live_execution_bridge,
                enable_live=True, dry_run=False, enable_token="WRONG",
            )
            self.assertFalse(r["live_execution_performed"])
            self.assertIn(r["prompt654_status"], {"blocked"})

    def test_live_fake_success_completes(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = _run(
                raw, str(Path(raw) / "queue"),
                bridge_runner=_bridge_live_complete,
                enable_live=True, dry_run=False, enable_token=DEFAULT_EXPECTED_ENABLE_TOKEN,
            )
            self.assertEqual(r["live_acceptance_status"], "success")
            self.assertTrue(r["project_complete"])
            self.assertTrue(r["real_run_report_ingested"])
            self.assertTrue(r["completion_gate_evaluated_real_outcomes"])
            self.assertTrue(r["failure_never_marked_complete"])

    def test_live_fake_failure_not_complete(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = _run(
                raw, str(Path(raw) / "queue"),
                bridge_runner=_bridge_live_failed,
                enable_live=True, dry_run=False, enable_token=DEFAULT_EXPECTED_ENABLE_TOKEN,
            )
            self.assertFalse(r["project_complete"])
            self.assertEqual(r["live_acceptance_status"], "blocked")
            self.assertTrue(r["failure_never_marked_complete"])

    def test_live_unreliable_outcome_partial(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = _run(
                raw, str(Path(raw) / "queue"),
                bridge_runner=_bridge_live_partial,
                enable_live=True, dry_run=False, enable_token=DEFAULT_EXPECTED_ENABLE_TOKEN,
            )
            self.assertEqual(r["live_acceptance_status"], "partial")
            self.assertFalse(r["project_complete"])
            self.assertEqual(r["next_action"], "manual_review_required")

    def test_main_repo_head_change_blocks(self):
        # head_reader returns different values before/after -> harness must flag it
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = _run(
                raw, str(Path(raw) / "queue"),
                bridge_runner=_bridge_live_complete,
                head_reader=_fake_head_reader_factory(["HEAD_A", "HEAD_B"]),
                enable_live=True, dry_run=False, enable_token=DEFAULT_EXPECTED_ENABLE_TOKEN,
            )
            self.assertFalse(r["main_repo_head_unchanged_during_live_run"])
            self.assertEqual(r["prompt654_status"], "blocked")

    def test_bounds_clamped(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = _run(raw, str(Path(raw) / "queue"), max_project_cycles=999, max_daemon_jobs=999, max_fix_attempts=999)
            self.assertEqual(r["bounds"], {"max_project_cycles": 1, "max_daemon_jobs": 1, "max_fix_attempts": 1})

    def test_report_has_required_fields(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = _run(raw, str(Path(raw) / "queue"))
            for field in harness._REPORT_FIELDS:
                self.assertIn(field, r)


if __name__ == "__main__":
    unittest.main()
