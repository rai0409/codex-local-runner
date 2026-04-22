from __future__ import annotations

import contextlib
import io
import json
import unittest

from automation.orchestration.git_workflow_templates import render_branch_name
from automation.orchestration.git_workflow_templates import render_cleanup_steps
from automation.orchestration.git_workflow_templates import render_commit_message
from automation.orchestration.git_workflow_templates import render_commit_subject
from scripts import prepare_git_workflow


class PrepareGitWorkflowScriptTests(unittest.TestCase):
    def _run(self, argv: list[str]) -> str:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exit_code = prepare_git_workflow.main(argv)
        self.assertEqual(exit_code, 0)
        return stream.getvalue()

    def test_text_output_uses_policy_default_prefix_and_summary_slug_fallback(self) -> None:
        summary = " Add   approval safety  summary surfacing. "
        output = self._run(["--summary", summary])

        expected_branch = render_branch_name(prefix="", slug=summary, issue_id=None)
        expected_subject = render_commit_subject(summary=summary, component=None)

        self.assertIn(f"branch_name={expected_branch}", output)
        self.assertIn(f"commit_subject={expected_subject}", output)
        self.assertIn(f"- git checkout -b {expected_branch}", output)
        self.assertNotIn("commit_message:", output)

    def test_json_output_is_deterministic_and_uses_normalized_body_footer_lines(self) -> None:
        summary = "Add approval safety summary surfacing"
        output = self._run(
            [
                "--summary",
                summary,
                "--slug",
                "approval safety summary",
                "--component",
                "runtime",
                "--body-line",
                "  explain   compact policy reuse ",
                "--body-line",
                "explain compact policy reuse",
                "--footer-line",
                "Refs: PR64",
                "--footer-line",
                " Refs:  PR64 ",
                "--include-cleanup",
                "--json",
            ]
        )
        payload = json.loads(output)

        expected_message = render_commit_message(
            summary=summary,
            component="runtime",
            body_lines=["explain compact policy reuse"],
            footer_lines=["Refs: PR64"],
        )
        self.assertEqual(payload["commit_message"], expected_message)
        self.assertEqual(payload["cleanup_steps"], list(render_cleanup_steps()))
        self.assertEqual(
            payload["branch_name"],
            render_branch_name(prefix="", slug="approval safety summary", issue_id=None),
        )
        self.assertEqual(payload["commit_subject"], render_commit_subject(summary=summary, component="runtime"))

    def test_print_commit_message_flag_emits_message_in_text_mode(self) -> None:
        summary = "Add approval safety summary surfacing"
        output = self._run(
            [
                "--summary",
                summary,
                "--body-line",
                "first body line",
                "--print-commit-message",
            ]
        )
        expected_message = render_commit_message(
            summary=summary,
            component=None,
            body_lines=["first body line"],
            footer_lines=[],
        )

        self.assertIn("commit_message:", output)
        self.assertIn(expected_message, output)


if __name__ == "__main__":
    unittest.main()
