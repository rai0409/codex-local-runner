"""Prompt655: tests for the safe project prompt-batch controller.

Pure/offline — no arbitrary prompt execution, no daemon/Codex/network, no real git
mutation (tag/source providers are injected). All filesystem work in tmpdirs.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from automation.orchestration.planned_runner.project_prompt_batch import (
    MAX_PROMPTS_CAP,
    load_and_validate,
    validate_prompt_batch,
)
from automation.orchestration.planned_runner.project_prompt_batch_controller import (
    advance_prompt_batch,
    analyze_prompt_batch,
    determine_next_prompt,
    evaluate_prompt_result,
    record_prompt_receipt,
)
import run_project_prompt_batch as cli  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_batch(root: Path, *, prompts=None, **manifest_over) -> Path:
    """Create a batch dir under root/prompts/project_batches/<id> with prompt files."""
    batch_dir = root / "prompts" / "project_batches" / "b1"
    batch_dir.mkdir(parents=True, exist_ok=True)
    prompts = prompts if prompts is not None else [
        {
            "prompt_id": "p001", "prompt_path": "001_p.md",
            "expected_tag": "p001-tag",
            "expected_report_path": "artifacts/autonomous_runtime/p001_report.json",
            "expected_summary_path": "artifacts/autonomous_runtime/p001_summary.md",
            "required_tests": ["python -m unittest tests.test_x"],
            "pass_conditions": {"status_field": "p001_status", "status_value": "success"},
        },
        {
            "prompt_id": "p002", "prompt_path": "002_p.md",
            "expected_tag": "p002-tag",
            "expected_report_path": "artifacts/autonomous_runtime/p002_report.json",
            "expected_summary_path": "artifacts/autonomous_runtime/p002_summary.md",
            "required_tests": [],
            "pass_conditions": {"status_field": "p002_status", "status_value": "success"},
        },
    ]
    for p in prompts:
        if "/" not in p["prompt_path"] and ".." not in p["prompt_path"] and not p["prompt_path"].startswith("/"):
            _write(batch_dir / p["prompt_path"], f"example prompt {p['prompt_id']}\n")
    manifest = {
        "batch_id": "b1", "goal": "demo batch", "max_prompts": 5,
        "stop_on_failure": True, "require_clean_source_before_each_prompt": True,
        "require_commit_tag_per_prompt": True, "prompts": prompts,
    }
    manifest.update(manifest_over)
    _write(batch_dir / "manifest.json", json.dumps(manifest))
    return batch_dir


def _write_evidence(root: Path, prompt_id: str, status_field: str, status_value: str) -> None:
    rep = root / "artifacts" / "autonomous_runtime" / f"{prompt_id}_report.json"
    _write(rep, json.dumps({status_field: status_value}))
    _write(root / "artifacts" / "autonomous_runtime" / f"{prompt_id}_summary.md", f"# {prompt_id}\n")


def _tag_checker_factory(present_tags):
    return lambda repo_root, tag: tag in set(present_tags)


_CLEAN = lambda repo_root: {"clean": True}
_DIRTY = lambda repo_root: {"clean": False, "dirty_count": 3}


class PromptBatchModelTests(unittest.TestCase):
    def test_valid_manifest_loads(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            batch, errors = load_and_validate(bd)
            self.assertEqual(errors, [])
            self.assertEqual(batch["batch_id"], "b1")
            self.assertEqual(len(batch["prompts"]), 2)
            self.assertEqual([p["order"] for p in batch["prompts"]], [0, 1])

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw), prompts=[{
                "prompt_id": "p001", "prompt_path": "../../etc/passwd",
                "pass_conditions": {"status_field": "s", "status_value": "success"},
            }])
            _, errors = load_and_validate(bd)
            self.assertTrue(any("prompt_path" in e for e in errors))

    def test_absolute_path_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw), prompts=[{
                "prompt_id": "p001", "prompt_path": "/etc/passwd",
                "pass_conditions": {"status_field": "s", "status_value": "success"},
            }])
            _, errors = load_and_validate(bd)
            self.assertTrue(any("prompt_path" in e for e in errors))

    def test_missing_prompt_file_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            # nested relative path (contains '/') is NOT auto-created by _make_batch,
            # so it is a genuine missing-file case (still a safe relpath).
            bd = _make_batch(Path(raw), prompts=[{
                "prompt_id": "p001", "prompt_path": "sub/missing.md",
                "pass_conditions": {"status_field": "s", "status_value": "success"},
            }])
            _, errors = load_and_validate(bd)
            self.assertTrue(any("file not found" in e for e in errors))

    def test_max_prompts_bound_enforced(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            prompts = [{"prompt_id": f"p{i:03d}", "prompt_path": f"{i:03d}_p.md",
                        "pass_conditions": {"status_field": "s", "status_value": "success"}}
                       for i in range(3)]
            bd = _make_batch(Path(raw), prompts=prompts, max_prompts=2)
            _, errors = load_and_validate(bd)
            self.assertTrue(any("exceeds max_prompts" in e for e in errors))

    def test_hard_cap_enforced(self):
        bd_payload = {"batch_id": "b", "goal": "g", "max_prompts": 99, "prompts": [{"prompt_id": "x", "prompt_path": "x.md"}]}
        _, errors = validate_prompt_batch(bd_payload, "/tmp/nope")
        self.assertTrue(any(f"cap {MAX_PROMPTS_CAP}" in e for e in errors))


class PromptBatchControllerTests(unittest.TestCase):
    def test_next_is_first_when_no_receipts(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            nxt = determine_next_prompt(bd, repo_root=raw)
            self.assertEqual(nxt["next_prompt"]["prompt_id"], "p001")

    def test_evaluate_pass_with_full_evidence(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            _write_evidence(Path(raw), "p001", "p001_status", "success")
            ev = evaluate_prompt_result(bd, "p001", repo_root=raw, tag_checker=_tag_checker_factory(["p001-tag"]))
            self.assertTrue(ev["passed"])
            self.assertEqual(ev["score"], 100)
            self.assertEqual(ev["continue_decision"], "continue")
            for k in ("objective_achievement", "constraint_compliance", "test_evidence_quality", "risk_remaining_gaps"):
                self.assertIn(k, ev["score_breakdown"])

    def test_evaluate_fail_missing_tag(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            _write_evidence(Path(raw), "p001", "p001_status", "success")
            ev = evaluate_prompt_result(bd, "p001", repo_root=raw, tag_checker=_tag_checker_factory([]))
            self.assertFalse(ev["passed"])
            self.assertLess(ev["score"], 100)
            self.assertTrue(any("tag missing" in m for m in ev["missing_evidence"]))

    def test_evaluate_fail_wrong_status(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            _write_evidence(Path(raw), "p001", "p001_status", "blocked")
            ev = evaluate_prompt_result(bd, "p001", repo_root=raw, tag_checker=_tag_checker_factory(["p001-tag"]))
            self.assertFalse(ev["passed"])

    def test_advance_to_second_only_after_first_passes(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            # before passing p001: advance points at p001
            adv0 = advance_prompt_batch(bd, repo_root=raw, source_status_provider=_CLEAN)
            self.assertEqual(adv0["next_prompt_id"], "p001")
            # pass p001
            _write_evidence(Path(raw), "p001", "p001_status", "success")
            evaluate_prompt_result(bd, "p001", repo_root=raw, tag_checker=_tag_checker_factory(["p001-tag"]))
            adv1 = advance_prompt_batch(bd, repo_root=raw, source_status_provider=_CLEAN)
            self.assertEqual(adv1["status"], "ready")
            self.assertEqual(adv1["next_prompt_id"], "p002")
            self.assertIn("002_p.md", adv1["next_instruction"])

    def test_failed_first_blocks_second_when_stop_on_failure(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            _write_evidence(Path(raw), "p001", "p001_status", "blocked")  # fails
            evaluate_prompt_result(bd, "p001", repo_root=raw, tag_checker=_tag_checker_factory(["p001-tag"]))
            adv = advance_prompt_batch(bd, repo_root=raw, source_status_provider=_CLEAN)
            self.assertEqual(adv["status"], "blocked")
            self.assertEqual(adv["reason"], "previous_prompt_failed")
            self.assertEqual(adv["blocked_on_prompt_id"], "p001")

    def test_dirty_source_blocks_advance(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            adv = advance_prompt_batch(bd, repo_root=raw, source_status_provider=_DIRTY)
            self.assertEqual(adv["status"], "blocked")
            self.assertEqual(adv["reason"], "dirty_source")

    def test_batch_complete(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            for pid, field in [("p001", "p001_status"), ("p002", "p002_status")]:
                _write_evidence(Path(raw), pid, field, "success")
                evaluate_prompt_result(bd, pid, repo_root=raw, tag_checker=_tag_checker_factory(["p001-tag", "p002-tag"]))
            adv = advance_prompt_batch(bd, repo_root=raw, source_status_provider=_CLEAN)
            self.assertEqual(adv["status"], "complete")
            self.assertTrue(adv["batch_complete"])

    def test_record_receipt(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            res = record_prompt_receipt(bd, "p001", {"executed_by": "claude_code", "status": "done"}, repo_root=raw)
            self.assertEqual(res["status"], "ok")
            self.assertTrue(Path(res["receipt_path"]).is_file())

    def test_analyze_reports_completion(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            _write_evidence(Path(raw), "p001", "p001_status", "success")
            evaluate_prompt_result(bd, "p001", repo_root=raw, tag_checker=_tag_checker_factory(["p001-tag"]))
            a = analyze_prompt_batch(bd, repo_root=raw)
            self.assertEqual(a["completed_count"], 1)
            self.assertEqual(a["next_prompt_id"], "p002")

    def test_no_arbitrary_execution_module_has_no_exec(self):
        # The controller/model source must not contain code that executes prompt text.
        from automation.orchestration.planned_runner import project_prompt_batch_controller as ctrl
        src = Path(ctrl.__file__).read_text(encoding="utf-8")
        self.assertNotIn("exec(", src)
        self.assertNotIn("eval(", src)
        # advance result explicitly flags no arbitrary execution
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            adv = advance_prompt_batch(bd, repo_root=raw, source_status_provider=_CLEAN)
            self.assertFalse(adv.get("arbitrary_prompt_execution", True))

    def test_no_side_effects_outside_repo_root(self):
        before = set(Path(".").iterdir())
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            analyze_prompt_batch(bd, repo_root=raw)
            determine_next_prompt(bd, repo_root=raw)
        self.assertEqual(before, set(Path(".").iterdir()))


class PromptBatchCliTests(unittest.TestCase):
    def test_cli_analyze_and_next_and_evaluate(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = _make_batch(Path(raw))
            self.assertEqual(cli.main(["analyze", "--batch-dir", bd.as_posix(), "--repo-root", raw]), 0)
            self.assertEqual(cli.main(["next", "--batch-dir", bd.as_posix(), "--repo-root", raw]), 0)
            _write_evidence(Path(raw), "p001", "p001_status", "success")
            # CLI evaluate uses default (real) tag checker -> tag absent in this tmp repo,
            # so it returns fail (exit 1) but must NOT raise and must write an evaluation.
            rc = cli.main(["evaluate", "--batch-dir", bd.as_posix(), "--repo-root", raw, "--prompt-id", "p001"])
            self.assertIn(rc, (0, 1))


if __name__ == "__main__":
    unittest.main()
