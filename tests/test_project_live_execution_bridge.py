"""Prompt653: tests for the live auto-execution bridge.

Dry-run by default; the live path is exercised ONLY with a FAKE daemon adapter.
No live Codex/daemon/network/git in tests.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.project_live_execution_bridge import (
    BRIDGE_MAX_PROJECT_CYCLES_CAP,
    DEFAULT_EXPECTED_ENABLE_TOKEN,
    run_project_live_execution_bridge,
)


def _intent(max_tasks: int = 3) -> dict:
    return {
        "project_id": "proj-alpha",
        "project_name": "Alpha",
        "goal": "Add helpers",
        "repo_target": "/tmp/r",
        "allowed_task_kinds": ["add_function"],
        "safety_limits": {"max_tasks": max_tasks},
    }


def _descs() -> list[dict]:
    return [
        {"target_file": "pkg/a.py", "function_name": "fa", "expression": "a + b"},
        {"target_file": "pkg/b.py", "function_name": "fb", "expression": "a + b", "depends_on": [0]},
    ]


_IDS = ["proj-alpha-t000", "proj-alpha-t001"]


def _fake_adapter_factory(statuses_by_cycle, calls):
    """statuses_by_cycle[i] = {task_id: status} written as run_reports in cycle i."""
    def _fake(*, queue_dir, runs_dir, work_dir, max_jobs, max_fix_attempts, cycle_index):
        calls.append({"cycle": cycle_index, "max_jobs": max_jobs, "max_fix_attempts": max_fix_attempts})
        mapping = statuses_by_cycle[min(cycle_index, len(statuses_by_cycle) - 1)]
        for tid, status in mapping.items():
            d = Path(runs_dir) / tid
            d.mkdir(parents=True, exist_ok=True)
            (d / "run_report.json").write_text(
                json.dumps({"task_id": tid, "status": status}), encoding="utf-8"
            )
        return {"adapter": "fake", "cycle_index": cycle_index, "exit_code": 0}
    return _fake


def _live_kwargs(**over):
    kw = dict(enable_live=True, dry_run=False, enable_token=DEFAULT_EXPECTED_ENABLE_TOKEN)
    kw.update(over)
    return kw


class LiveAutoExecutionBridgeTests(unittest.TestCase):
    def test_dry_run_default_no_execution(self):
        calls = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            q = Path(raw) / "queue"
            r = run_project_live_execution_bridge(
                _intent(), _descs(), q.as_posix(),
                daemon_runner=_fake_adapter_factory([{}], calls),
            )
        self.assertEqual(r["status"], "success")
        self.assertFalse(r["live_execution_performed"])
        self.assertTrue(r["dry_run"])
        self.assertEqual(r["next_action"], "continue_project_loop")
        self.assertEqual(r["queue_population_result"]["task_count"], 2)
        self.assertEqual(calls, [])  # adapter never invoked in dry-run

    def test_enable_live_false_blocks_execution(self):
        calls = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = run_project_live_execution_bridge(
                _intent(), _descs(), (Path(raw) / "q").as_posix(),
                enable_live=False, dry_run=False, enable_token=DEFAULT_EXPECTED_ENABLE_TOKEN,
                daemon_runner=_fake_adapter_factory([{}], calls),
            )
        self.assertFalse(r["live_execution_performed"])
        self.assertTrue(r["dry_run"])
        self.assertEqual(calls, [])

    def test_wrong_token_blocks_live(self):
        calls = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = run_project_live_execution_bridge(
                _intent(), _descs(), (Path(raw) / "q").as_posix(),
                **_live_kwargs(enable_token="WRONG"),
                daemon_runner=_fake_adapter_factory([{}], calls),
            )
        self.assertEqual(r["status"], "blocked")
        self.assertFalse(r["live_execution_performed"])
        self.assertEqual(r["next_action"], "manual_review_required")
        self.assertEqual(calls, [])

    def test_missing_output_dir_blocks(self):
        r = run_project_live_execution_bridge(_intent(), _descs(), None, **_live_kwargs())
        self.assertEqual(r["status"], "blocked")
        self.assertEqual(r["queue_population_result"], {})

    def test_live_fake_success_completes_project(self):
        calls = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = run_project_live_execution_bridge(
                _intent(), _descs(), (Path(raw) / "q").as_posix(),
                **_live_kwargs(),
                daemon_runner=_fake_adapter_factory([{_IDS[0]: "success", _IDS[1]: "success"}], calls),
            )
        self.assertEqual(r["status"], "success")
        self.assertTrue(r["live_execution_performed"])
        self.assertTrue(r["project_complete"])
        self.assertEqual(r["next_action"], "complete")
        self.assertEqual(len(calls), 1)

    def test_live_fake_failure_never_completes(self):
        calls = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = run_project_live_execution_bridge(
                _intent(), _descs(), (Path(raw) / "q").as_posix(),
                **_live_kwargs(),
                daemon_runner=_fake_adapter_factory([{_IDS[0]: "success", _IDS[1]: "blocked"}], calls),
            )
        self.assertFalse(r["project_complete"])
        self.assertEqual(r["status"], "blocked")
        self.assertEqual(r["next_action"], "manual_review_required")
        self.assertEqual(r["completion_gate_result"]["status"], "failed")

    def test_unreadable_outcome_blocks_safely(self):
        # adapter writes NO run_reports -> unreliable parsing -> partial/manual_review
        calls = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = run_project_live_execution_bridge(
                _intent(), _descs(), (Path(raw) / "q").as_posix(),
                **_live_kwargs(),
                daemon_runner=_fake_adapter_factory([{}], calls),  # writes nothing
            )
        self.assertEqual(r["status"], "partial")
        self.assertTrue(r["live_execution_performed"])
        self.assertFalse(r["project_complete"])
        self.assertEqual(r["next_action"], "manual_review_required")

    def test_iterates_until_complete_across_cycles(self):
        calls = []
        snaps = [{_IDS[0]: "success"}, {_IDS[0]: "success", _IDS[1]: "success"}]
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = run_project_live_execution_bridge(
                _intent(), _descs(), (Path(raw) / "q").as_posix(),
                **_live_kwargs(max_project_cycles=3),
                daemon_runner=_fake_adapter_factory(snaps, calls),
            )
        self.assertTrue(r["project_complete"])
        self.assertEqual(r["next_action"], "complete")
        self.assertEqual(len(calls), 2)  # completed on second cycle

    def test_bounds_clamped(self):
        calls = []
        # always in_progress -> should stop at the clamped project-cycle cap
        snaps = [{_IDS[0]: "success"}]  # t001 never done -> in_progress every cycle
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = run_project_live_execution_bridge(
                _intent(), _descs(), (Path(raw) / "q").as_posix(),
                **_live_kwargs(max_project_cycles=999, max_daemon_jobs=999, max_fix_attempts=999),
                daemon_runner=_fake_adapter_factory(snaps, calls),
            )
        self.assertLessEqual(len(calls), BRIDGE_MAX_PROJECT_CYCLES_CAP)
        self.assertLessEqual(calls[0]["max_jobs"], 5)
        self.assertLessEqual(calls[0]["max_fix_attempts"], 2)

    def test_dry_run_deterministic(self):
        calls = []
        with tempfile.TemporaryDirectory(dir="/tmp") as r1, tempfile.TemporaryDirectory(dir="/tmp") as r2:
            a = run_project_live_execution_bridge(_intent(), _descs(), (Path(r1) / "q").as_posix(),
                                                  daemon_runner=_fake_adapter_factory([{}], calls))
            b = run_project_live_execution_bridge(_intent(), _descs(), (Path(r2) / "q").as_posix(),
                                                  daemon_runner=_fake_adapter_factory([{}], calls))
        for key in ("status", "live_execution_performed", "dry_run", "next_action", "project_complete"):
            self.assertEqual(a[key], b[key])
        self.assertEqual(a["plan_result"]["plan"]["tasks"], b["plan_result"]["plan"]["tasks"])

    def test_invalid_intent_blocks_no_queue(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            r = run_project_live_execution_bridge({"project_id": "BAD"}, _descs(), (Path(raw) / "q").as_posix())
        self.assertEqual(r["status"], "blocked")
        self.assertEqual(r["queue_population_result"], {})
        self.assertEqual(r["next_action"], "manual_review_required")

    def test_no_side_effects_outside_explicit_dir(self):
        before = set(Path(".").iterdir())
        calls = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            run_project_live_execution_bridge(
                _intent(), _descs(), (Path(raw) / "q").as_posix(), **_live_kwargs(),
                daemon_runner=_fake_adapter_factory([{_IDS[0]: "success", _IDS[1]: "success"}], calls),
            )
        self.assertEqual(before, set(Path(".").iterdir()))


if __name__ == "__main__":
    unittest.main()
