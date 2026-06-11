from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from automation.orchestration.planned_runner import autonomous_live_loop
from automation.orchestration.planned_runner.autonomous_cycle import (
    AUTONOMOUS_CYCLE_ENABLE_TOKEN,
)
from automation.orchestration.planned_runner.live_codex_gate import (
    LIVE_CODEX_GATE_ENABLE_TOKEN,
)


def _clean_dirty_state(**_kwargs):
    return {
        "status": "ready",
        "dirty_paths": [],
        "dirty_paths_outside_allowed_artifacts": [],
    }


def _fake_gate_factory(calls: list[dict], effect_status: str = "passed", codex_status: str = "success"):
    def _fake_gate(*, generated_prompt_path, out_dir, sandbox_mode="default", effect_spec_path=None, **_kwargs):
        calls.append(
            {
                "generated_prompt_path": str(generated_prompt_path),
                "sandbox_mode": sandbox_mode,
                "effect_spec_path": effect_spec_path,
            }
        )
        output_root = Path(out_dir)
        result_path = output_root / "codex_execution_result.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(
                {
                    "status": codex_status,
                    "returncode": 0 if codex_status == "success" else 1,
                    "returncode_classification": codex_status,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "status": "success" if codex_status == "success" else "blocked",
            "codex_invoked": True,
            "codex_result_path": result_path.as_posix(),
            "effect_verification_status": effect_status,
            "next_action": "commit_tag_gate",
        }

    return _fake_gate


class AutonomousLiveLoopEffectVerificationIntegrationTests(unittest.TestCase):
    def _make_manifest(self, tmp_dir: Path, cycle_count: int = 2) -> Path:
        cycles = []
        for index in range(1, cycle_count + 1):
            prompt = tmp_dir / f"cycle{index}_prompt.md"
            prompt.write_text(f"cycle {index} prompt\n", encoding="utf-8")
            spec = tmp_dir / f"cycle{index}_spec.json"
            spec.write_text("{}", encoding="utf-8")
            cycles.append(
                {
                    "generated_prompt_path": prompt.as_posix(),
                    "repo_path": (tmp_dir / f"repo{index}").as_posix(),
                    "effect_spec_path": spec.as_posix(),
                }
            )
        manifest = tmp_dir / "manifest.json"
        manifest.write_text(json.dumps({"cycles": cycles}), encoding="utf-8")
        return manifest

    def _run_loop(self, tmp_dir: Path, calls: list[dict], **overrides):
        kwargs = dict(
            repo_path=tmp_dir,
            out_dir=tmp_dir / "out",
            generated_prompt_path=None,
            max_cycles=2,
            max_seconds=120,
            autonomous_enable_token=AUTONOMOUS_CYCLE_ENABLE_TOKEN,
            live_codex_enable_token=LIVE_CODEX_GATE_ENABLE_TOKEN,
            verification_continue=True,
        )
        kwargs.update(overrides)
        fake_gate = overrides.pop("fake_gate", None) or _fake_gate_factory(calls)
        kwargs.pop("fake_gate", None)
        with mock.patch.object(autonomous_live_loop, "run_live_codex_gate", new=fake_gate), mock.patch.object(
            autonomous_live_loop, "dirty_paths_outside_allowed_artifacts", new=_clean_dirty_state
        ):
            return autonomous_live_loop.run_autonomous_live_loop(**kwargs)

    def test_manifest_assigns_prompt_and_spec_per_cycle(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            manifest = self._make_manifest(tmp_dir)
            calls: list[dict] = []
            payload = self._run_loop(
                tmp_dir,
                calls,
                generated_prompt_manifest_path=manifest,
                sandbox_mode="workspace-write",
            )
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["cycle_count"], 2)
        self.assertEqual(payload["codex_invoked_count"], 2)
        self.assertEqual(payload["stop_reason"], "verification_max_cycles_reached")
        self.assertEqual(len(calls), 2)
        self.assertIn("cycle1_prompt.md", calls[0]["generated_prompt_path"])
        self.assertIn("cycle1_spec.json", calls[0]["effect_spec_path"])
        self.assertIn("cycle2_prompt.md", calls[1]["generated_prompt_path"])
        self.assertIn("cycle2_spec.json", calls[1]["effect_spec_path"])
        self.assertEqual(calls[0]["sandbox_mode"], "workspace-write")
        self.assertEqual(calls[1]["sandbox_mode"], "workspace-write")
        self.assertEqual(payload["per_cycle_effect_verification_statuses"], ["passed", "passed"])
        self.assertEqual(payload["manifest_cycle_count"], 2)

    def test_default_single_prompt_behavior_unchanged(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            prompt = tmp_dir / "prompt.md"
            prompt.write_text("single prompt\n", encoding="utf-8")
            calls: list[dict] = []
            payload = self._run_loop(
                tmp_dir,
                calls,
                generated_prompt_path=prompt,
                verification_continue=False,
            )
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["cycle_count"], 1)
        self.assertEqual(payload["stop_reason"], "commit_tag_gate")
        self.assertEqual(len(calls), 1)
        self.assertIn("prompt.md", calls[0]["generated_prompt_path"])
        self.assertIsNone(calls[0]["effect_spec_path"])
        self.assertEqual(calls[0]["sandbox_mode"], "default")
        self.assertEqual(payload["sandbox_mode"], "default")
        self.assertEqual(payload["generated_prompt_manifest_path"], "")

    def test_invalid_manifest_blocks_without_invoking_codex(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            manifest = tmp_dir / "manifest.json"
            manifest.write_text("{\"cycles\": []}", encoding="utf-8")
            calls: list[dict] = []
            payload = self._run_loop(tmp_dir, calls, generated_prompt_manifest_path=manifest)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["stop_reason"], "invalid_prompt_manifest")
        self.assertEqual(payload["codex_invoked_count"], 0)
        self.assertEqual(calls, [])

    def test_manifest_bounds_cycles_below_max_cycles(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            manifest = self._make_manifest(tmp_dir, cycle_count=1)
            calls: list[dict] = []
            payload = self._run_loop(
                tmp_dir,
                calls,
                generated_prompt_manifest_path=manifest,
                max_cycles=3,
            )
        self.assertEqual(payload["cycle_count"], 1)
        self.assertEqual(payload["effective_max_cycles"], 1)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["stop_reason"], "verification_max_cycles_reached")
        self.assertEqual(len(calls), 1)

    def test_effect_failure_stops_loop_without_success(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            manifest = self._make_manifest(tmp_dir)
            calls: list[dict] = []
            fake_gate = _fake_gate_factory(calls, effect_status="failed", codex_status="failed")
            payload = self._run_loop(
                tmp_dir,
                calls,
                generated_prompt_manifest_path=manifest,
                fake_gate=fake_gate,
            )
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["cycle_count"], 1)
        self.assertEqual(payload["stop_reason"], "targeted_fix_required")
        self.assertEqual(payload["per_cycle_effect_verification_statuses"], ["failed"])
        self.assertFalse(payload["commit_performed"])
        self.assertFalse(payload["tag_performed"])


if __name__ == "__main__":
    unittest.main()
