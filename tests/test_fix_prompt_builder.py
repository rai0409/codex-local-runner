from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from automation.orchestration.planned_runner.fix_prompt_builder import (
    build_fix_prompt_text,
    write_fix_prompt,
)


def _effect_spec(repo_path: str) -> dict:
    return {
        "repo_path": repo_path,
        "expected_modified_files": ["calculator.py"],
        "expected_unmodified_files": ["test_calculator.py"],
        "required_text": {"calculator.py": ["def subtract(a, b):", "return a - b"]},
        "forbidden_paths": ["evil.txt"],
        "allow_extra_files": False,
    }


def _effect_failure_digest() -> dict:
    return {
        "failure_class": "effect_verification_failed",
        "stop_reason": "effect_verification_failed",
        "effect_verification_errors": [
            "expected modified file did not change: calculator.py",
            "required text missing in calculator.py: 'def subtract(a, b):'",
        ],
    }


class FixPromptBuilderTests(unittest.TestCase):
    def test_effect_failure_prompt_contains_evidence_spec_and_constraints(self):
        text = build_fix_prompt_text(
            digest=_effect_failure_digest(),
            effect_spec=_effect_spec("/tmp/sandbox_repo"),
            original_prompt_text="original task text",
        )
        self.assertIn("You are operating only inside /tmp/sandbox_repo.", text)
        self.assertIn("failure_class: effect_verification_failed", text)
        self.assertIn("expected modified file did not change: calculator.py", text)
        self.assertIn("Files that must be modified: calculator.py", text)
        self.assertIn("Files that must NOT be modified: test_calculator.py", text)
        self.assertIn("def subtract(a, b):", text)
        self.assertIn("return a - b", text)
        self.assertIn("Paths that must NOT exist: evil.txt", text)
        self.assertIn("original task text", text)
        self.assertIn("Do not commit.", text)
        self.assertIn("Do not push.", text)
        self.assertIn('{"status":"success","summary":"targeted fix applied"}', text)

    def test_codex_failure_prompt_without_errors(self):
        digest = {"failure_class": "codex_execution_failed", "stop_reason": "codex_failed"}
        text = build_fix_prompt_text(digest=digest, effect_spec=_effect_spec("/tmp/r"))
        self.assertIn("failure_class: codex_execution_failed", text)
        self.assertIn("verification errors: none recorded", text)

    def test_write_fix_prompt_from_files(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            digest_path = tmp_dir / "failure_digest.json"
            digest_path.write_text(json.dumps(_effect_failure_digest()), encoding="utf-8")
            spec_path = tmp_dir / "spec.json"
            spec_path.write_text(json.dumps(_effect_spec("/tmp/sandbox_repo")), encoding="utf-8")
            out_path = tmp_dir / "fix_prompt.md"
            result = write_fix_prompt(
                digest_path=digest_path,
                effect_spec_path=spec_path,
                out_path=out_path,
            )
            content = out_path.read_text(encoding="utf-8")
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["codex_invoked"])
        self.assertIn("def subtract(a, b):", content)

    def test_write_fix_prompt_blocks_on_missing_inputs(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            result = write_fix_prompt(
                digest_path=tmp_dir / "missing_digest.json",
                effect_spec_path=tmp_dir / "missing_spec.json",
                out_path=tmp_dir / "fix_prompt.md",
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(len(result["errors"]), 2)
            self.assertFalse((tmp_dir / "fix_prompt.md").exists())


if __name__ == "__main__":
    unittest.main()
