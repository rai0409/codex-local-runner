"""Prompt638B regression: the autonomous live loop must never end as success
when any cycle's effect verification failed.

Two angles:
1. Integrated path: the (fixed) classifier downgrades the effect-failed cycle.
2. Defense in depth: even if the cycle classifier were tricked into returning a
   success classification (the Prompt638A bug), the loop-level strict effect gate
   still forces a blocked final status.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
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


def _effect_failed_gate(*, generated_prompt_path, out_dir, sandbox_mode="default", effect_spec_path=None, **_kwargs):
    """Mimic a Codex run that exits 0 / emits success JSON but FAILS effects."""
    output_root = Path(out_dir)
    result_path = output_root / "codex_execution_result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(
            {
                "status": "failed",
                "returncode": 0,
                "returncode_classification": "failed",
                "stop_reason": "effect_verification_failed",
                "next_action": "inspect_missing_expected_effects",
                "effect_verification_enabled": True,
                "effect_verification_status": "failed",
                "effect_required_text_verified": False,
            }
        ),
        encoding="utf-8",
    )
    return {
        "status": "blocked",
        "codex_invoked": True,
        "codex_result_path": result_path.as_posix(),
        "effect_verification_status": "failed",
        "next_action": "inspect_missing_expected_effects",
    }


def _run_loop(tmp_dir: Path, *, effect_spec_path, classification_override=None):
    kwargs = dict(
        repo_path=tmp_dir,
        out_dir=tmp_dir / "out",
        generated_prompt_path=(tmp_dir / "prompt.md"),
        max_cycles=1,
        max_seconds=120,
        autonomous_enable_token=AUTONOMOUS_CYCLE_ENABLE_TOKEN,
        live_codex_enable_token=LIVE_CODEX_GATE_ENABLE_TOKEN,
        verification_continue=False,
        sandbox_mode="workspace-write",
        effect_spec_path=effect_spec_path,
    )
    (tmp_dir / "prompt.md").write_text("do the thing\n", encoding="utf-8")
    patches = [
        mock.patch.object(autonomous_live_loop, "run_live_codex_gate", new=_effect_failed_gate),
        mock.patch.object(
            autonomous_live_loop, "dirty_paths_outside_allowed_artifacts", new=_clean_dirty_state
        ),
    ]
    if classification_override is not None:
        patches.append(
            mock.patch.object(
                autonomous_live_loop,
                "run_autonomous_cycle_metadata",
                new=classification_override,
            )
        )
    with patches[0], patches[1]:
        if classification_override is not None:
            with patches[2]:
                return autonomous_live_loop.run_autonomous_live_loop(**kwargs)
        return autonomous_live_loop.run_autonomous_live_loop(**kwargs)


class LiveLoopEffectFailedBlocksSuccessTests(unittest.TestCase):
    def test_integrated_effect_failure_blocks_success(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            spec = tmp_dir / "effect_spec.json"
            spec.write_text("{}", encoding="utf-8")
            payload = _run_loop(tmp_dir, effect_spec_path=spec)

        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["per_cycle_effect_verification_statuses"], ["failed"])
        self.assertFalse(payload["effect_gate_passed"])
        self.assertEqual(payload["stop_reason"], "effect_verification_failed")
        self.assertEqual(payload["blocked_reason"], "effect_verification_failed")
        self.assertFalse(payload["commit_performed"])
        self.assertFalse(payload["tag_performed"])

    def test_defense_in_depth_blocks_even_if_classifier_says_success(self):
        # Simulate the Prompt638A buggy classifier returning a success
        # classification (next_action=commit_tag_gate) for the effect-failed cycle.
        def _buggy_success_classification(**kwargs):
            output_dir = Path(kwargs["output_dir"])
            state_path = output_dir / "autonomous_cycle_state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "status": "success",
                "classification": "codex_result_success",
                "next_action": "commit_tag_gate",
                "stop_reason": "none",
                "blocked_reason": "none",
                "targeted_fix_required": False,
                "artifact_paths": [state_path.as_posix()],
            }
            state_path.write_text(json.dumps(state), encoding="utf-8")
            return state

        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            spec = tmp_dir / "effect_spec.json"
            spec.write_text("{}", encoding="utf-8")
            payload = _run_loop(
                tmp_dir,
                effect_spec_path=spec,
                classification_override=_buggy_success_classification,
            )

        # The classifier said success, but the loop-level strict effect gate wins.
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["effect_gate_passed"])
        self.assertEqual(payload["per_cycle_effect_verification_statuses"], ["failed"])
        self.assertEqual(payload["blocked_reason"], "effect_verification_failed")
        self.assertFalse(payload["commit_performed"])
        self.assertFalse(payload["tag_performed"])


if __name__ == "__main__":
    unittest.main()
