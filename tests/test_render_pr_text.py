from __future__ import annotations

import contextlib
import io
import json
import unittest

from automation.orchestration.pr_text_templates import render_pr_body
from automation.orchestration.pr_text_templates import render_pr_title
from scripts import render_pr_text


class RenderPrTextScriptTests(unittest.TestCase):
    def _run(self, argv: list[str]) -> str:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exit_code = render_pr_text.main(argv)
        self.assertEqual(exit_code, 0)
        return stream.getvalue()

    def test_text_output_defaults_what_changed_to_summary_and_includes_out_of_scope(self) -> None:
        summary = " Add approval safety summary surfacing to local workflow helpers "
        output = self._run(
            [
                "--summary",
                summary,
                "--out-of-scope",
                "approval flow changes",
            ]
        )

        normalized_summary = "Add approval safety summary surfacing to local workflow helpers"
        expected_title = render_pr_title(summary=normalized_summary, scope=None)
        expected_body = render_pr_body(
            summary=normalized_summary,
            what_changed=[normalized_summary],
            validation=[],
            scope_notes=["Out of scope: approval flow changes"],
        )

        self.assertIn(f"pr_title={expected_title}", output)
        self.assertIn("pr_body:", output)
        self.assertIn(expected_body, output)

    def test_json_output_is_deterministic_and_deduplicates_lines(self) -> None:
        output = self._run(
            [
                "--scope",
                "runtime",
                "--summary",
                "Add approval safety summary surfacing to local workflow helpers",
                "--change",
                "tighten normalization",
                "--change",
                " tighten   normalization ",
                "--validation",
                "uv run python -m unittest tests.test_prepare_git_workflow -v",
                "--validation",
                " uv run python -m unittest tests.test_render_pr_text -v ",
                "--scope-note",
                "narrow script-only updates",
                "--out-of-scope",
                "approval flow changes",
                "--out-of-scope",
                " approval  flow  changes ",
                "--json",
            ]
        )
        payload = json.loads(output)

        summary = "Add approval safety summary surfacing to local workflow helpers"
        expected_title = render_pr_title(summary=summary, scope="runtime")
        expected_body = render_pr_body(
            summary=summary,
            what_changed=["tighten normalization"],
            validation=[
                "uv run python -m unittest tests.test_prepare_git_workflow -v",
                "uv run python -m unittest tests.test_render_pr_text -v",
            ],
            scope_notes=[
                "narrow script-only updates",
                "Out of scope: approval flow changes",
            ],
        )

        self.assertEqual(payload["pr_title"], expected_title)
        self.assertEqual(payload["pr_body"], expected_body)

    def test_scope_is_reflected_in_policy_driven_title_rendering(self) -> None:
        summary = "Add approval safety summary surfacing"
        output = self._run(["--scope", "approval", "--summary", summary, "--json"])
        payload = json.loads(output)
        self.assertEqual(payload["pr_title"], render_pr_title(summary=summary, scope="approval"))


if __name__ == "__main__":
    unittest.main()
