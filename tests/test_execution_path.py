from __future__ import annotations

import json
import importlib.util
import subprocess
import tempfile
import unittest
import sys
from dataclasses import replace
from pathlib import Path
from unittest import mock

from adapters.chatgpt_tasks import ChatgptTasksAdapter
from adapters.codex_cli import _build_review_handoff_summary
from adapters.codex_cli import _build_reviewer_handoff
from adapters.codex_cli import CodexCliAdapter
from adapters.codex_cli import _derive_result_interpretation
from adapters.codex_cli import _derive_review_recommendation
from adapters.local_llm import LocalLlmAdapter
from automation.orchestration.repository_profile import APPROVAL_ACTIONS
from automation.orchestration.repository_profile import FORBIDDEN_GIT_OPERATION_IDS
from automation.orchestration.repository_profile import validate_repository_profile
from automation.orchestration.safe_validation_executor import ValidationCommandResult
from automation.orchestration.safe_validation_executor import ValidationExecutionResult
from orchestrator.codex_execution import execute_codex_cli
from orchestrator import main as orchestrator_main
from orchestrator.policy_loader import get_change_category_policy


class CodexExecutionArtifactTests(unittest.TestCase):
    def test_default_execution_persists_prompt_for_backward_compatibility(self) -> None:
        captured: dict[str, str] = {}

        def transport(command, **kwargs):
            captured["input"] = kwargs["input"]
            return subprocess.CompletedProcess(command, 0, "ok", "")

        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
            result = execute_codex_cli(
                task={"repo_path": repo_dir},
                prompt="backward compatible prompt",
                work_root=work_root,
                which=lambda _: "/usr/bin/codex",
                run_subprocess=transport,
            )

            persisted_prompt = Path(result["prompt_path"]).read_text(encoding="utf-8")
            self.assertEqual(persisted_prompt, captured["input"])
            self.assertTrue(persisted_prompt.endswith("backward compatible prompt"))
            self.assertIn("backward compatible prompt", persisted_prompt)
            self.assertNotIn("backward compatible prompt", Path(result["meta_path"]).read_text(encoding="utf-8"))
            self.assertIn("prompt", {artifact["name"] for artifact in result["artifacts"]})

    def test_no_persistence_mode_passes_prompt_but_redacts_runner_artifacts(self) -> None:
        prompt = "DISTINCTIVE-PROMPT-MARKER-7f3d\nA detailed task instruction."
        captured: dict[str, object] = {}

        def transport(command, **kwargs):
            captured["command"] = command
            captured["input"] = kwargs["input"]
            return subprocess.CompletedProcess(
                command,
                0,
                f"echoed prompt: {prompt}\nDISTINCTIVE-PROMPT-MARKER-7f3d\nuseful stdout",
                f"error context: {prompt}",
            )

        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
            result = execute_codex_cli(
                task={"repo_path": repo_dir}, prompt=prompt, work_root=work_root,
                which=lambda _: "/usr/bin/codex", run_subprocess=transport,
                persist_prompt=False,
                model=" gpt-5.5 ",
                model_reasoning_effort="medium",
            )
            run_dir = Path(result["run_dir"])
            persisted = [
                Path(result["stdout_path"]).read_text(encoding="utf-8"),
                Path(result["stderr_path"]).read_text(encoding="utf-8"),
                Path(result["meta_path"]).read_text(encoding="utf-8"),
            ]

            self.assertEqual(captured["command"][-1], "-")
            self.assertNotIn(prompt, captured["command"])
            self.assertIn(prompt, captured["input"])
            self.assertEqual(captured["command"][captured["command"].index("-m") + 1], "gpt-5.5")
            self.assertEqual(
                captured["command"][captured["command"].index('model_reasoning_effort="medium"')],
                'model_reasoning_effort="medium"',
            )
            self.assertEqual(result["prompt_path"], "")
            self.assertFalse((run_dir / "prompt.txt").exists())
            self.assertNotIn("prompt", {artifact["name"] for artifact in result["artifacts"]})
            for content in persisted:
                self.assertNotIn(prompt, content)
                self.assertNotIn("DISTINCTIVE-PROMPT-MARKER-7f3d", content)
            self.assertIn("useful stdout", persisted[0])

    def test_model_profile_injection_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
            commands: list[list[str]] = []

            def transport(command, **kwargs):
                commands.append(command)
                return subprocess.CompletedProcess(command, 0, "", "")

            default_result = execute_codex_cli(
                task={"repo_path": repo_dir},
                prompt="prompt",
                work_root=work_root,
                which=lambda _: "/usr/bin/codex",
                run_subprocess=transport,
            )
            self.assertEqual(default_result["status"], "completed")
            self.assertEqual(commands[-1], [
                "codex", "exec", "--sandbox", "workspace-write", "--config",
                'approval_policy="never"', "--skip-git-repo-check", "-",
            ])

            model_only = execute_codex_cli(
                task={"repo_path": repo_dir},
                prompt="prompt",
                work_root=work_root,
                which=lambda _: "/usr/bin/codex",
                run_subprocess=transport,
                model="gpt-5.6",
            )
            self.assertEqual(model_only["status"], "completed")
            self.assertEqual(commands[-1][commands[-1].index("-m") + 1], "gpt-5.6")
            self.assertNotIn("model_reasoning_effort", " ".join(commands[-1]))

            effort_only = execute_codex_cli(
                task={"repo_path": repo_dir},
                prompt="prompt",
                work_root=work_root,
                which=lambda _: "/usr/bin/codex",
                run_subprocess=transport,
                model_reasoning_effort="low",
            )
            self.assertEqual(effort_only["status"], "completed")
            self.assertNotIn("-m", commands[-1])
            self.assertIn('model_reasoning_effort="low"', commands[-1])

            for effort in ("low", "medium", "high", "xhigh"):
                result = execute_codex_cli(
                    task={"repo_path": repo_dir},
                    prompt="prompt",
                    work_root=work_root,
                    which=lambda _: "/usr/bin/codex",
                    run_subprocess=transport,
                    model="gpt-5.6",
                    model_reasoning_effort=effort,
                )
                self.assertEqual(result["status"], "completed")
                command = commands[-1]
                self.assertEqual(command[:2], ["codex", "exec"])
                self.assertEqual(command[-1], "-")
                self.assertEqual(command[command.index("-m") + 1], "gpt-5.6")
                self.assertIn(f'model_reasoning_effort="{effort}"', command)

            for kwargs in (
                {"model": ""},
                {"model_reasoning_effort": ""},
                {"model_reasoning_effort": "none"},
                {"model_reasoning_effort": "invalid"},
            ):
                result = execute_codex_cli(
                    task={"repo_path": repo_dir},
                    prompt="prompt",
                    work_root=work_root,
                    which=lambda _: "/usr/bin/codex",
                    run_subprocess=transport,
                    **kwargs,
                )
                self.assertEqual(result["status"], "not_started")
            self.assertEqual(len(commands), 7)

    def test_json_event_mode_preserves_stdin_contract_and_redacts_jsonl(self) -> None:
        prompt = "JSON-PROMPT-MARKER-4c9e\nJSON-PROMPT-SECOND-LINE"

        def execute(stdout: str, *, emit_json: bool) -> tuple[dict, list[str]]:
            command: list[str] = []

            def transport(argv, **kwargs):
                command.extend(argv)
                self.assertIn(prompt, kwargs["input"])
                return subprocess.CompletedProcess(argv, 0, stdout, "")

            with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
                result = execute_codex_cli(
                    task={"repo_path": repo_dir},
                    prompt=prompt,
                    work_root=work_root,
                    which=lambda _: "/usr/bin/codex",
                    run_subprocess=transport,
                    persist_prompt=False,
                    emit_json=emit_json,
                )
                result["meta"] = json.loads(Path(result["meta_path"]).read_text(encoding="utf-8"))
                result["persisted_stdout"] = Path(result["stdout_path"]).read_text(encoding="utf-8")
            return result, command

        plain_result, plain_command = execute("plain output", emit_json=False)
        self.assertNotIn("--json", plain_command)
        self.assertEqual(plain_command[-1], "-")
        self.assertNotIn("json_events", plain_result["meta"])

        valid_stdout = '{"type":"thread.started"}\n{"type":"item.completed"}\n'
        valid_result, valid_command = execute(valid_stdout, emit_json=True)
        self.assertEqual(valid_command[:2], ["codex", "exec"])
        self.assertEqual(valid_command[-1], "-")
        self.assertLess(valid_command.index("--json"), len(valid_command) - 1)
        self.assertNotIn(prompt, valid_command)
        self.assertEqual(valid_result["meta"]["json_events"], {
            "enabled": True,
            "parse_status": "parsed",
            "event_count": 2,
            "invalid_line_count": 0,
            "event_types": ["item.completed", "thread.started"],
            "usage": {
                "status": "absent",
                "event_count": 0,
                "invalid_event_count": 0,
                "events": [],
            },
        })

        cases = (
            ('{"type":"one"}\nnot-json\n{"type":"two"}\n', "partial", 2, 1),
            ("not-json\n[]\n", "invalid", 0, 2),
            (" \n\t\n", "empty", 0, 0),
        )
        for stdout, parse_status, event_count, invalid_line_count in cases:
            with self.subTest(parse_status=parse_status):
                result, _ = execute(stdout, emit_json=True)
                summary = result["meta"]["json_events"]
                self.assertEqual(summary["parse_status"], parse_status)
                self.assertEqual(summary["event_count"], event_count)
                self.assertEqual(summary["invalid_line_count"], invalid_line_count)
                self.assertEqual(result["status"], "completed")
                self.assertTrue(result["success"])

        nested_stdout = json.dumps({
            "type": "example",
            "nested": {"values": ["safe", prompt]},
        }, ensure_ascii=False) + "\n" + f"invalid {prompt.splitlines()[0]}\n"
        private_result, _ = execute(nested_stdout, emit_json=True)
        persisted_lines = private_result["persisted_stdout"].splitlines()
        self.assertEqual(len(persisted_lines), 2)
        sanitized_event = json.loads(persisted_lines[0])
        self.assertEqual(sanitized_event["nested"]["values"][0], "safe")
        self.assertNotIn(prompt, private_result["persisted_stdout"])
        self.assertNotIn("JSON-PROMPT-MARKER-4c9e", private_result["persisted_stdout"])
        self.assertNotIn("JSON-PROMPT-SECOND-LINE", private_result["persisted_stdout"])
        self.assertNotIn(prompt, json.dumps(private_result["meta"], ensure_ascii=False))
        self.assertEqual(private_result["meta"]["json_events"]["parse_status"], "partial")

    def test_json_event_usage_observations_follow_observed_schema(self) -> None:
        def execute(lines: list[str]) -> dict:
            def transport(argv, **kwargs):
                return subprocess.CompletedProcess(argv, 0, "\n".join(lines), "")

            with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
                result = execute_codex_cli(
                    task={"repo_path": repo_dir},
                    prompt="usage observation prompt",
                    work_root=work_root,
                    which=lambda _: "/usr/bin/codex",
                    run_subprocess=transport,
                    emit_json=True,
                )
                return json.loads(Path(result["meta_path"]).read_text(encoding="utf-8"))

        observed = execute([
            '{"type":"turn.started"}',
            (
                '{"type":"turn.completed","usage":{"input_tokens":18643,'
                '"cached_input_tokens":2432,"cache_write_input_tokens":0,'
                '"output_tokens":31,"reasoning_output_tokens":19}}'
            ),
        ])["json_events"]["usage"]
        self.assertEqual(observed, {
            "status": "observed",
            "event_count": 1,
            "invalid_event_count": 0,
            "events": [{
                "input_tokens": 18643,
                "cached_input_tokens": 2432,
                "cache_write_input_tokens": 0,
                "output_tokens": 31,
                "reasoning_output_tokens": 19,
            }],
        })
        self.assertFalse(
            {"total_tokens", "billable_tokens", "uncached_input_tokens", "cost", "quota", "remaining"}
            & set(observed)
        )

        for name, lines, expected in (
            (
                "absent_usage",
                ['{"type":"turn.completed"}'],
                {"status": "absent", "event_count": 0, "invalid_event_count": 0, "events": []},
            ),
            (
                "no_turn_completed",
                ['{"type":"thread.started"}', '{"type":"turn.started"}'],
                {"status": "absent", "event_count": 0, "invalid_event_count": 0, "events": []},
            ),
            (
                "invalid_mapping",
                ['{"type":"turn.completed","usage":"bad"}'],
                {"status": "invalid", "event_count": 0, "invalid_event_count": 1, "events": []},
            ),
            (
                "invalid_string_field",
                ['{"type":"turn.completed","usage":{"input_tokens":"18643"}}'],
                {"status": "invalid", "event_count": 0, "invalid_event_count": 1, "events": []},
            ),
            (
                "invalid_bool_field",
                ['{"type":"turn.completed","usage":{"input_tokens":true}}'],
                {"status": "invalid", "event_count": 0, "invalid_event_count": 1, "events": []},
            ),
            (
                "invalid_negative_field",
                ['{"type":"turn.completed","usage":{"output_tokens":-1}}'],
                {"status": "invalid", "event_count": 0, "invalid_event_count": 1, "events": []},
            ),
            (
                "invalid_without_recognized_fields",
                ['{"type":"turn.completed","usage":{"future_usage_field":999}}'],
                {"status": "invalid", "event_count": 0, "invalid_event_count": 1, "events": []},
            ),
            (
                "unknown_field_is_ignored",
                ['{"type":"turn.completed","usage":{"input_tokens":100,"future_usage_field":999}}'],
                {
                    "status": "observed",
                    "event_count": 1,
                    "invalid_event_count": 0,
                    "events": [{"input_tokens": 100}],
                },
            ),
            (
                "multiple_events_preserve_order",
                [
                    '{"type":"turn.completed","usage":{"input_tokens":1}}',
                    '{"type":"turn.completed","usage":{"output_tokens":2}}',
                ],
                {
                    "status": "observed",
                    "event_count": 2,
                    "invalid_event_count": 0,
                    "events": [{"input_tokens": 1}, {"output_tokens": 2}],
                },
            ),
            (
                "mixed_valid_invalid",
                [
                    '{"type":"turn.completed","usage":{"input_tokens":1}}',
                    '{"type":"turn.completed","usage":{"output_tokens":-1}}',
                ],
                {
                    "status": "invalid",
                    "event_count": 1,
                    "invalid_event_count": 1,
                    "events": [{"input_tokens": 1}],
                },
            ),
        ):
            with self.subTest(name=name):
                self.assertEqual(execute(lines)["json_events"]["usage"], expected)

        partial = execute([
            '{"type":"turn.completed","usage":{"input_tokens":7}}',
            "not-json",
        ])["json_events"]
        self.assertEqual(partial["parse_status"], "partial")
        self.assertEqual(partial["usage"], {
            "status": "observed",
            "event_count": 1,
            "invalid_event_count": 0,
            "events": [{"input_tokens": 7}],
        })

    def test_transient_stdout_is_opt_in_and_never_persisted(self) -> None:
        prompt = "TASK_COMPLETION_EVALUATION_JSON_BEGIN\nDISTINCTIVE-PROMPT-MARKER-7f3d\nTASK_COMPLETION_EVALUATION_JSON_END"
        raw_stdout = (
            "TASK_COMPLETION_EVALUATION_JSON_BEGIN\n"
            '{"status":"completed","reason_code":"task.ok","satisfied_criteria":["done"],"unsatisfied_criteria":[],"evidence_refs":["git:diff"]}\n'
            "TASK_COMPLETION_EVALUATION_JSON_END"
        )

        def transport(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, raw_stdout, f"error context: {prompt}")

        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_root:
            default_result = execute_codex_cli(
                task={"repo_path": repo_dir}, prompt=prompt, work_root=work_root,
                which=lambda _: "/usr/bin/codex", run_subprocess=transport, persist_prompt=False,
            )
            self.assertNotIn("transient_stdout", default_result)

            result = execute_codex_cli(
                task={"repo_path": repo_dir}, prompt=prompt, work_root=work_root,
                which=lambda _: "/usr/bin/codex", run_subprocess=transport, persist_prompt=False,
                return_transient_stdout=True,
            )
            run_dir = Path(result["run_dir"])
            self.assertEqual(result["transient_stdout"], raw_stdout)
            self.assertFalse((run_dir / "prompt.txt").exists())
            self.assertNotIn("prompt", {artifact["name"] for artifact in result["artifacts"]})
            self.assertNotIn("transient", {artifact["name"] for artifact in result["artifacts"]})
            for path in (result["stdout_path"], result["stderr_path"], result["meta_path"]):
                persisted = Path(path).read_text(encoding="utf-8")
                self.assertNotIn(raw_stdout, persisted)
                self.assertNotIn("DISTINCTIVE-PROMPT-MARKER-7f3d", persisted)
                self.assertNotIn("TASK_COMPLETION_EVALUATION_JSON_BEGIN", persisted)
                self.assertNotIn("TASK_COMPLETION_EVALUATION_JSON_END", persisted)


class CodexCliExecutionTests(unittest.TestCase):
    def _assert_review_handoff_summary_consistency(self, result: dict) -> None:
        summary = result["review_handoff_summary"]
        self.assertEqual(
            set(summary.keys()),
            {
                "final_status",
                "final_verify_status",
                "final_verify_reason",
                "retry_attempted",
                "retry_outcome",
                "result_interpretation",
                "review_recommendation",
            },
        )
        self.assertEqual(summary["final_status"], result["status"])
        self.assertEqual(summary["final_verify_status"], result["verify"]["status"])
        self.assertEqual(summary["final_verify_reason"], result["verify"]["reason"])
        self.assertEqual(summary["retry_attempted"], result["retry"]["attempted"])
        self.assertEqual(summary["retry_outcome"], result["retry"]["outcome"])
        self.assertEqual(summary["result_interpretation"], result["result_interpretation"])
        self.assertEqual(summary["review_recommendation"], result["review_recommendation"])

    def _assert_reviewer_handoff_consistency(self, result: dict) -> None:
        handoff = result["reviewer_handoff"]
        self.assertEqual(set(handoff.keys()), {"summary", "execution", "validation"})
        summary = handoff["summary"]
        self.assertEqual(
            set(summary.keys()),
            {
                "final_status",
                "final_verify_status",
                "final_verify_reason",
                "retry_attempted",
                "retry_outcome",
                "result_interpretation",
                "review_recommendation",
            },
        )
        self.assertEqual(summary, result["review_handoff_summary"])
        self.assertEqual(summary["final_status"], result["status"])
        self.assertEqual(summary["final_verify_status"], result["verify"]["status"])
        self.assertEqual(summary["final_verify_reason"], result["verify"]["reason"])
        self.assertEqual(summary["retry_attempted"], result["retry"]["attempted"])
        self.assertEqual(summary["retry_outcome"], result["retry"]["outcome"])
        self.assertEqual(summary["result_interpretation"], result["result_interpretation"])
        self.assertEqual(summary["review_recommendation"], result["review_recommendation"])

        execution = handoff["execution"]
        self.assertEqual(set(execution.keys()), {"status", "attempt_count", "return_code"})
        self.assertEqual(execution["status"], result["status"])
        self.assertEqual(execution["attempt_count"], result["attempt_count"])
        self.assertEqual(execution["return_code"], result["return_code"])

        validation = handoff["validation"]
        self.assertEqual(validation["verify_status"], result["verify"]["status"])
        self.assertEqual(validation["verify_reason"], result["verify"]["reason"])
        if "summary" in result["verify"]:
            self.assertEqual(set(validation.keys()), {"verify_status", "verify_reason", "summary"})
            self.assertEqual(validation["summary"], result["verify"]["summary"])
        else:
            self.assertEqual(set(validation.keys()), {"verify_status", "verify_reason"})

        self.assertNotIn("diff", handoff)
        self.assertNotIn("tests", handoff)

    def test_codex_cli_execute_completed(self) -> None:
        _replacement_adapter_completed(self)
        return
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            execution_dir = Path(work_dir) / "execution_runs" / "20260101_000000"
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": repo_dir,
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ):
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ):
                    with mock.patch(
                        "adapters.codex_cli.run_codex",
                        return_value={
                            "status": "completed",
                            "success": True,
                            "return_code": 0,
                            "started_at": "2026-01-01T00:00:00",
                            "finished_at": "2026-01-01T00:00:01",
                            "artifacts": [
                                {"name": "stdout", "path": str(execution_dir / "stdout.txt")},
                                {"name": "stderr", "path": str(execution_dir / "stderr.txt")},
                                {"name": "meta", "path": str(execution_dir / "meta.json")},
                            ],
                            "stdout_path": str(execution_dir / "stdout.txt"),
                            "stderr_path": str(execution_dir / "stderr.txt"),
                            "meta_path": str(execution_dir / "meta.json"),
                            "error": "",
                        },
                    ) as run_codex_mock:
                        result = adapter.execute(
                            {
                                "prompt": "test prompt",
                                "repo_path": repo_dir,
                                "work_dir": work_dir,
                                "timeout_seconds": 30,
                            }
                        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["started_at"], "2026-01-01T00:00:00")
        self.assertEqual(result["finished_at"], "2026-01-01T00:00:01")
        self.assertIsNone(result["error"])
        self.assertEqual(len(result["artifacts"]), 3)
        run_codex_mock.assert_called_once()
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["retry"],
            {"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )
        self.assertEqual(result["verify"]["status"], "not_run")
        self.assertEqual(result["result_interpretation"], "completed_verified_passed")
        self.assertEqual(result["review_recommendation"], "no_review_needed")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_execute_failure_is_reported(self) -> None:
        _replacement_adapter_failed_execution(self)
        return
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": repo_dir,
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ):
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ):
                    with mock.patch("adapters.codex_cli.run_validation_commands") as verify_mock:
                        with mock.patch(
                            "adapters.codex_cli.run_codex",
                            return_value={
                                "status": "failed",
                                "success": False,
                                "return_code": 2,
                                "started_at": "2026-01-01T00:00:00",
                                "finished_at": "2026-01-01T00:00:01",
                                "artifacts": [
                                    {
                                        "name": "stderr",
                                        "path": str(Path(work_dir) / "execution_runs" / "stderr.txt"),
                                    }
                                ],
                                "stdout_path": str(Path(work_dir) / "execution_runs" / "stdout.txt"),
                                "stderr_path": str(Path(work_dir) / "execution_runs" / "stderr.txt"),
                                "meta_path": str(Path(work_dir) / "execution_runs" / "meta.json"),
                                "error": "execution failed",
                            },
                        ) as run_codex_mock:
                            result = adapter.execute(
                                {
                                    "prompt": "test prompt",
                                    "repo_path": repo_dir,
                                    "work_dir": work_dir,
                                    "timeout_seconds": 30,
                                }
                            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["started_at"], "2026-01-01T00:00:00")
        self.assertEqual(result["finished_at"], "2026-01-01T00:00:01")
        self.assertIn("execution failed", result["error"])
        run_codex_mock.assert_called_once()
        verify_mock.assert_not_called()
        self.assertEqual(result["verify"]["status"], "not_run")
        self.assertEqual(
            set(result["verify"].keys()),
            {"status", "success", "commands", "error", "reason"},
        )
        self.assertNotIn("command_results", result["verify"])
        self.assertNotIn("summary", result["verify"])
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["retry"],
            {"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )
        self.assertEqual(result["result_interpretation"], "execution_not_completed")
        self.assertEqual(result["review_recommendation"], "review_recommended")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_execute_uses_prepared_worktree_path(self) -> None:
        _replacement_adapter_completed(self)
        return
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": "/source/repo",
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ) as prepare_mock:
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ) as cleanup_mock:
                    with mock.patch(
                        "adapters.codex_cli.run_validation_commands",
                        return_value={
                            "status": "passed",
                            "success": True,
                            "commands": [
                                {
                                    "command": "echo verify",
                                    "return_code": 0,
                                    "stdout": "ok\n",
                                    "stderr": "",
                                    "success": True,
                                }
                            ],
                            "command_results": [
                                {
                                    "command": "echo verify",
                                    "status": "passed",
                                    "return_code": 0,
                                    "stdout": "ok\n",
                                    "stderr": "",
                                }
                            ],
                            "error": "",
                            "summary": {"total": 1, "passed": 1, "failed": 0},
                            "reason": "validation_passed",
                        },
                    ) as verify_mock:
                        with mock.patch(
                            "adapters.codex_cli.run_codex",
                            return_value={
                                "status": "completed",
                                "success": True,
                                "return_code": 0,
                                "started_at": "2026-01-01T00:00:00",
                                "finished_at": "2026-01-01T00:00:01",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "",
                            },
                        ) as run_codex_mock:
                            result = adapter.execute(
                                {
                                    "prompt": "test prompt",
                                    "repo_path": "/source/repo",
                                    "work_dir": work_dir,
                                    "validation_commands": ["echo verify"],
                                }
                            )

        prepare_mock.assert_called_once_with(
            source_repo_path="/source/repo",
            worktree_parent=str(Path(work_dir) / "worktrees"),
        )
        run_codex_mock.assert_called_once_with(
            task={"repo_path": "/prepared/worktree"},
            prompt="test prompt",
            work_root=str(Path(work_dir) / "execution_runs"),
        )
        cleanup_mock.assert_called_once_with(
            source_repo_path="/source/repo",
            worktree_path="/prepared/worktree",
            branch_name="codex-run/20260101_000000",
        )
        verify_mock.assert_called_once_with(
            validation_commands=["echo verify"],
            cwd="/prepared/worktree",
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["verify"]["status"], "passed")
        self.assertEqual(result["verify"]["summary"], {"total": 1, "passed": 1, "failed": 0})
        self.assertEqual(result["verify"]["command_results"][0]["status"], "passed")
        self.assertEqual(result["verify"]["reason"], "validation_passed")
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["retry"],
            {"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )
        self.assertEqual(result["result_interpretation"], "completed_verified_passed")
        self.assertEqual(result["review_recommendation"], "no_review_needed")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_execute_fails_when_worktree_preparation_fails(self) -> None:
        _replacement_adapter_failed_execution(self)
        return
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": "/source/repo",
                    "worktree_path": "",
                    "branch_name": "",
                    "created": False,
                    "cleanup_needed": False,
                    "error": "source repo path is not a git working tree: not a git repository",
                },
            ):
                with mock.patch("adapters.codex_cli.run_validation_commands") as verify_mock:
                    with mock.patch("adapters.codex_cli.run_codex") as run_codex_mock:
                        result = adapter.execute(
                            {
                                "prompt": "test prompt",
                                "repo_path": "/source/repo",
                                "work_dir": work_dir,
                            }
                        )

        run_codex_mock.assert_not_called()
        verify_mock.assert_not_called()
        self.assertEqual(result["status"], "failed")
        self.assertIn("not a git working tree", result["error"])
        self.assertEqual(result["verify"]["status"], "not_run")
        self.assertEqual(result["verify"]["reason"], "validation_not_run_execution_status_failed")
        self.assertNotIn("command_results", result["verify"])
        self.assertNotIn("summary", result["verify"])
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["retry"],
            {"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )
        self.assertEqual(result["result_interpretation"], "execution_not_completed")
        self.assertEqual(result["review_recommendation"], "review_recommended")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_execute_timed_out_sets_verify_not_run(self) -> None:
        _replacement_adapter_failed_execution(self)
        return
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": repo_dir,
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ):
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ):
                    with mock.patch("adapters.codex_cli.run_validation_commands") as verify_mock:
                        with mock.patch(
                            "adapters.codex_cli.run_codex",
                            return_value={
                                "status": "timed_out",
                                "success": False,
                                "return_code": None,
                                "started_at": "2026-01-01T00:00:00",
                                "finished_at": "2026-01-01T00:10:00",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "timed out",
                            },
                        ) as run_codex_mock:
                            result = adapter.execute(
                                {
                                    "prompt": "test prompt",
                                    "repo_path": repo_dir,
                                    "work_dir": work_dir,
                                    "validation_commands": ["echo verify"],
                                }
                            )

        verify_mock.assert_not_called()
        run_codex_mock.assert_called_once()
        self.assertEqual(result["status"], "timed_out")
        self.assertEqual(result["verify"]["status"], "not_run")
        self.assertEqual(result["verify"]["reason"], "validation_not_run_execution_status_timed_out")
        self.assertNotIn("command_results", result["verify"])
        self.assertNotIn("summary", result["verify"])
        self.assertEqual(result["attempt_count"], 1)
        self.assertEqual(
            result["retry"],
            {"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )
        self.assertEqual(result["result_interpretation"], "execution_not_completed")
        self.assertEqual(result["review_recommendation"], "review_recommended")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_retries_once_when_verify_failed_and_second_attempt_passes(self) -> None:
        _replacement_adapter_retry(self)
        return
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": repo_dir,
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ):
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ):
                    with mock.patch(
                        "adapters.codex_cli.run_codex",
                        side_effect=[
                            {
                                "status": "completed",
                                "success": True,
                                "return_code": 0,
                                "started_at": "2026-01-01T00:00:00",
                                "finished_at": "2026-01-01T00:00:01",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "",
                            },
                            {
                                "status": "completed",
                                "success": True,
                                "return_code": 0,
                                "started_at": "2026-01-01T00:00:02",
                                "finished_at": "2026-01-01T00:00:03",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "",
                            },
                        ],
                    ) as run_codex_mock:
                        with mock.patch(
                            "adapters.codex_cli.run_validation_commands",
                            side_effect=[
                                {
                                    "status": "failed",
                                    "success": False,
                                    "commands": [
                                        {
                                            "command": "echo verify",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "first failure",
                                            "success": False,
                                        }
                                    ],
                                    "command_results": [
                                        {
                                            "command": "echo verify",
                                            "status": "failed",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "first failure",
                                        }
                                    ],
                                    "error": "first failure",
                                    "summary": {"total": 1, "passed": 0, "failed": 1},
                                    "reason": "validation_failed",
                                },
                                {
                                    "status": "passed",
                                    "success": True,
                                    "commands": [
                                        {
                                            "command": "echo verify",
                                            "return_code": 0,
                                            "stdout": "ok\n",
                                            "stderr": "",
                                            "success": True,
                                        }
                                    ],
                                    "command_results": [
                                        {
                                            "command": "echo verify",
                                            "status": "passed",
                                            "return_code": 0,
                                            "stdout": "ok\n",
                                            "stderr": "",
                                        }
                                    ],
                                    "error": "",
                                    "summary": {"total": 1, "passed": 1, "failed": 0},
                                    "reason": "validation_passed",
                                },
                            ],
                        ) as verify_mock:
                            result = adapter.execute(
                                {
                                    "prompt": "test prompt",
                                    "repo_path": repo_dir,
                                    "work_dir": work_dir,
                                    "validation_commands": ["echo verify"],
                                }
                            )

        self.assertEqual(run_codex_mock.call_count, 2)
        self.assertEqual(verify_mock.call_count, 2)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["started_at"], "2026-01-01T00:00:02")
        self.assertEqual(result["finished_at"], "2026-01-01T00:00:03")
        self.assertEqual(result["verify"]["status"], "passed")
        self.assertEqual(result["verify"]["reason"], "validation_passed")
        self.assertEqual(result["verify"]["error"], "")
        self.assertIn("commands", result["verify"])
        self.assertIn("command_results", result["verify"])
        self.assertIn("summary", result["verify"])
        self.assertEqual(result["verify"]["summary"], {"total": 1, "passed": 1, "failed": 0})
        self.assertEqual(len(result["verify"]["command_results"]), result["verify"]["summary"]["total"])
        self.assertEqual(len(result["verify"]["command_results"]), 1)
        self.assertEqual(result["verify"]["command_results"][0]["status"], "passed")
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(
            result["retry"],
            {"attempted": True, "trigger": "verify_failed", "outcome": "retry_succeeded"},
        )
        self.assertEqual(result["result_interpretation"], "completed_verified_passed_after_retry")
        self.assertEqual(result["review_recommendation"], "review_recommended")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_codex_cli_retry_outcome_failed_when_second_attempt_verify_fails(self) -> None:
        _replacement_adapter_retry(self)
        return
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as work_dir:
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "source_repo_path": repo_dir,
                    "worktree_path": "/prepared/worktree",
                    "branch_name": "codex-run/20260101_000000",
                    "created": True,
                    "cleanup_needed": True,
                    "error": "",
                },
            ):
                with mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={
                        "worktree_path": "/prepared/worktree",
                        "branch_name": "codex-run/20260101_000000",
                        "cleaned": True,
                        "error": "",
                    },
                ):
                    with mock.patch(
                        "adapters.codex_cli.run_codex",
                        side_effect=[
                            {
                                "status": "completed",
                                "success": True,
                                "return_code": 0,
                                "started_at": "2026-01-01T00:00:00",
                                "finished_at": "2026-01-01T00:00:01",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "",
                            },
                            {
                                "status": "completed",
                                "success": True,
                                "return_code": 0,
                                "started_at": "2026-01-01T00:00:02",
                                "finished_at": "2026-01-01T00:00:03",
                                "artifacts": [],
                                "stdout_path": "",
                                "stderr_path": "",
                                "meta_path": "",
                                "error": "",
                            },
                        ],
                    ):
                        with mock.patch(
                            "adapters.codex_cli.run_validation_commands",
                            side_effect=[
                                {
                                    "status": "failed",
                                    "success": False,
                                    "commands": [
                                        {
                                            "command": "echo verify",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "first failure",
                                            "success": False,
                                        }
                                    ],
                                    "command_results": [
                                        {
                                            "command": "echo verify",
                                            "status": "failed",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "first failure",
                                        }
                                    ],
                                    "error": "first failure",
                                    "summary": {"total": 1, "passed": 0, "failed": 1},
                                    "reason": "validation_failed",
                                },
                                {
                                    "status": "failed",
                                    "success": False,
                                    "commands": [
                                        {
                                            "command": "echo verify",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "second failure",
                                            "success": False,
                                        }
                                    ],
                                    "command_results": [
                                        {
                                            "command": "echo verify",
                                            "status": "failed",
                                            "return_code": 1,
                                            "stdout": "",
                                            "stderr": "second failure",
                                        }
                                    ],
                                    "error": "second failure",
                                    "summary": {"total": 1, "passed": 0, "failed": 1},
                                    "reason": "validation_failed",
                                },
                            ],
                        ):
                            result = adapter.execute(
                                {
                                    "prompt": "test prompt",
                                    "repo_path": repo_dir,
                                    "work_dir": work_dir,
                                    "validation_commands": ["echo verify"],
                                }
                            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["verify"]["status"], "failed")
        self.assertEqual(result["verify"]["reason"], "validation_failed")
        self.assertEqual(result["verify"]["error"], "second failure")
        self.assertIn("commands", result["verify"])
        self.assertIn("command_results", result["verify"])
        self.assertIn("summary", result["verify"])
        self.assertEqual(result["verify"]["summary"], {"total": 1, "passed": 0, "failed": 1})
        self.assertEqual(len(result["verify"]["command_results"]), result["verify"]["summary"]["total"])
        self.assertEqual(len(result["verify"]["command_results"]), 1)
        self.assertEqual(result["verify"]["command_results"][0]["status"], "failed")
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(
            result["retry"],
            {"attempted": True, "trigger": "verify_failed", "outcome": "retry_failed"},
        )
        self.assertEqual(result["result_interpretation"], "completed_verified_failed_after_retry")
        self.assertEqual(result["review_recommendation"], "review_recommended_after_retry_failure")
        self._assert_review_handoff_summary_consistency(result)
        self._assert_reviewer_handoff_consistency(result)

    def test_result_interpretation_completed_verify_failed_without_retry(self) -> None:
        interpretation = _derive_result_interpretation(
            execution_status="completed",
            verify_result={"status": "failed"},
            retry={"attempted": False, "trigger": "not_applicable", "outcome": "not_attempted"},
        )

        self.assertEqual(interpretation, "completed_verified_failed")
        self.assertEqual(_derive_review_recommendation(interpretation), "review_recommended")

    def test_review_handoff_summary_completed_verify_failed_without_retry(self) -> None:
        summary = _build_review_handoff_summary(
            final_status="completed",
            final_verify_status="failed",
            final_verify_reason="validation_failed",
            retry_attempted=False,
            retry_outcome="not_attempted",
            result_interpretation="completed_verified_failed",
            review_recommendation="review_recommended",
        )

        self.assertEqual(
            summary,
            {
                "final_status": "completed",
                "final_verify_status": "failed",
                "final_verify_reason": "validation_failed",
                "retry_attempted": False,
                "retry_outcome": "not_attempted",
                "result_interpretation": "completed_verified_failed",
                "review_recommendation": "review_recommended",
            },
        )

    def test_review_handoff_summary_is_direct_scalar_mirror_without_coercion(self) -> None:
        interpretation_marker = object()
        summary = _build_review_handoff_summary(
            final_status=123,  # type: ignore[arg-type]
            final_verify_status=456,  # type: ignore[arg-type]
            final_verify_reason=None,  # type: ignore[arg-type]
            retry_attempted="yes",  # type: ignore[arg-type]
            retry_outcome=789,  # type: ignore[arg-type]
            result_interpretation=interpretation_marker,  # type: ignore[arg-type]
            review_recommendation=[],
        )

        self.assertEqual(summary["final_status"], 123)
        self.assertEqual(summary["final_verify_status"], 456)
        self.assertIsNone(summary["final_verify_reason"])
        self.assertEqual(summary["retry_attempted"], "yes")
        self.assertEqual(summary["retry_outcome"], 789)
        self.assertIs(summary["result_interpretation"], interpretation_marker)
        self.assertEqual(summary["review_recommendation"], [])

    def test_reviewer_handoff_completed_verify_failed_without_retry(self) -> None:
        summary = _build_review_handoff_summary(
            final_status="completed",
            final_verify_status="failed",
            final_verify_reason="validation_failed",
            retry_attempted=False,
            retry_outcome="not_attempted",
            result_interpretation="completed_verified_failed",
            review_recommendation="review_recommended",
        )
        handoff = _build_reviewer_handoff(
            review_handoff_summary=summary,
            final_status="completed",
            attempt_count=1,
            return_code=1,
            verify_result={"status": "failed", "reason": "validation_failed"},
        )

        self.assertEqual(
            handoff,
            {
                "summary": summary,
                "execution": {"status": "completed", "attempt_count": 1, "return_code": 1},
                "validation": {"verify_status": "failed", "verify_reason": "validation_failed"},
            },
        )

    def test_codex_execution_profile_resolution_and_evidence(self) -> None:
        def run_case(
            payload_overrides: dict[str, object],
            *,
            model: str | None = None,
            model_reasoning_effort: str | None = None,
        ) -> tuple[dict, list[mock._Call]]:
            with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as work_dir:
                root = Path(raw)
                _prepared_git_directory(root)
                profile = replace(
                    _safe_adapter_profile(root),
                    model=model,
                    model_reasoning_effort=model_reasoning_effort,
                )
                execution = {
                    "status": "completed", "return_code": 0, "started_at": "a",
                    "finished_at": "b", "artifacts": [], "error": "",
                }
                with mock.patch(
                    "adapters.codex_cli.run_codex", return_value=execution,
                ) as codex, mock.patch(
                    "adapters.codex_cli.execute_repository_validation",
                    return_value=_safe_execution_result("passed"),
                ):
                    result = CodexCliAdapter().execute_prepared_worktree({
                        "prompt": "test prompt", "worktree_path": str(root),
                        "work_dir": work_dir, "repository_profile": profile,
                        **payload_overrides,
                    })
                    return result, list(codex.call_args_list)

        cases = (
            ({}, None, None, "gpt-5.6-terra", "default", "low", "default"),
            ({}, "profile-model", "high", "profile-model", "repository_profile", "high", "repository_profile"),
            ({"declared_category": "docs_only"}, "profile-model", "high", "gpt-5.6-terra", "category", "low", "category"),
            ({"declared_category": "runtime_fix_high_risk"}, None, None, "gpt-5.6", "category", "medium", "category"),
            ({"declared_category": "runtime_fix_high_risk", "model": "task-model", "model_reasoning_effort": "xhigh"}, "profile-model", "low", "task-model", "task", "xhigh", "task"),
            ({"declared_category": "docs_only", "model": "task-model"}, "profile-model", "high", "task-model", "task", "low", "category"),
        )
        for payload, profile_model, profile_effort, model, model_source, effort, effort_source in cases:
            with self.subTest(payload=payload):
                result, calls = run_case(
                    payload,
                    model=profile_model,
                    model_reasoning_effort=profile_effort,
                )
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0].kwargs["model"], model)
                self.assertEqual(calls[0].kwargs["model_reasoning_effort"], effort)
                evidence = result["validation_attempts"][0]
                self.assertEqual(
                    {key: evidence[key] for key in (
                        "model", "model_source", "model_reasoning_effort",
                        "model_reasoning_effort_source",
                    )},
                    {
                        "model": model,
                        "model_source": model_source,
                        "model_reasoning_effort": effort,
                        "model_reasoning_effort_source": effort_source,
                    },
                )

    def test_legacy_model_categories_use_chatgpt_compatible_model(self) -> None:
        categories = (
            "docs_only", "ci_only", "test_only", "contract_guard_only",
            "runtime_fix_low_risk",
        )
        for category_name in categories:
            with self.subTest(category_name=category_name):
                category = get_change_category_policy(category_name)
                assert category is not None
                self.assertEqual(
                    category["codex_profile"]["model"], "gpt-5.6-terra",
                )

    def test_codex_execution_profile_invalid_inputs_do_not_run_codex(self) -> None:
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as work_dir:
            root = Path(raw)
            _prepared_git_directory(root)
            profile = _safe_adapter_profile(root)
            for payload, reason in (
                ({"declared_category": "unknown_category"}, "codex_execution.category.invalid"),
                ({"model": ""}, "codex_execution.model.invalid"),
                ({"model_reasoning_effort": "none"}, "codex_execution.model_reasoning_effort.invalid"),
                ({"model_reasoning_effort": "invalid"}, "codex_execution.model_reasoning_effort.invalid"),
            ):
                with self.subTest(payload=payload), mock.patch(
                    "adapters.codex_cli.run_codex",
                ) as codex:
                    result = CodexCliAdapter().execute_prepared_worktree({
                        "prompt": "test prompt", "worktree_path": str(root),
                        "work_dir": work_dir, "repository_profile": profile,
                        **payload,
                    })
                self.assertEqual(result["error"], reason)
                codex.assert_not_called()

    def test_codex_execution_profile_is_fixed_for_timeout_retry_and_repair(self) -> None:
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as work_dir:
            root = Path(raw)
            _prepared_git_directory(root)
            profile = _safe_adapter_profile(root)
            timed_out = {
                "status": "timed_out", "return_code": None, "started_at": "a",
                "finished_at": "b", "artifacts": [], "error": "timeout",
            }
            completed = {
                "status": "completed", "return_code": 0, "started_at": "a",
                "finished_at": "b", "artifacts": [], "error": "",
            }
            payload = {
                "prompt": "test prompt", "worktree_path": str(root), "work_dir": work_dir,
                "repository_profile": profile, "declared_category": "runtime_fix_high_risk",
            }
            with mock.patch(
                "adapters.codex_cli.run_codex", side_effect=[timed_out, completed],
            ) as codex, mock.patch(
                "adapters.codex_cli.execute_repository_validation",
                return_value=_safe_execution_result("passed"),
            ):
                timeout_result = CodexCliAdapter().execute_prepared_worktree(payload)
            self.assertEqual(timeout_result["status"], "completed")
            self.assertEqual(len(codex.call_args_list), 2)
            self.assertEqual(
                [
                    (call.kwargs["model"], call.kwargs["model_reasoning_effort"])
                    for call in codex.call_args_list
                ],
                [("gpt-5.6", "medium"), ("gpt-5.6", "medium")],
            )

            with mock.patch(
                "adapters.codex_cli.run_codex", side_effect=[completed, completed],
            ) as codex, mock.patch(
                "adapters.codex_cli.execute_repository_validation",
                side_effect=[_safe_execution_result("failed"), _safe_execution_result("passed")],
            ):
                repair_result = CodexCliAdapter().execute_prepared_worktree(payload)
            self.assertEqual([item["phase"] for item in repair_result["validation_attempts"]], ["initial", "repair"])
            self.assertEqual(len(codex.call_args_list), 2)
            for call in codex.call_args_list:
                self.assertEqual(call.kwargs["model"], "gpt-5.6")
                self.assertEqual(call.kwargs["model_reasoning_effort"], "medium")
            for evidence in repair_result["validation_attempts"]:
                self.assertEqual(evidence["model_source"], "category")
                self.assertEqual(evidence["model_reasoning_effort_source"], "category")

    def test_execute_transports_explicit_profile_fields_to_prepared_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as work_dir:
            root = Path(raw)
            _prepared_git_directory(root)
            payload = _adapter_payload(root, work_dir)
            payload["repository_profile"] = replace(
                payload["repository_profile"],
                model="repository-model",
                model_reasoning_effort="medium",
            )
            payload.update({
                "declared_category": "docs_only",
                "model": "task-model",
                "model_reasoning_effort": "high",
            })
            prepared_result = {
                "adapter": "codex_cli", "status": "completed", "started_at": "a",
                "finished_at": "b", "artifacts": [], "error": None, "return_code": 0,
            }
            with mock.patch(
                "adapters.codex_cli.prepare_git_worktree",
                return_value={
                    "created": True, "cleanup_needed": False,
                    "worktree_path": str(root), "branch_name": "branch", "error": "",
                },
            ), mock.patch.object(
                CodexCliAdapter,
                "execute_prepared_worktree",
                return_value=prepared_result,
            ) as prepared:
                result = CodexCliAdapter().execute(payload)
        self.assertEqual(result, prepared_result)
        prepared_payload = prepared.call_args.args[0]
        self.assertEqual(prepared_payload["declared_category"], "docs_only")
        self.assertEqual(prepared_payload["model"], "task-model")
        self.assertEqual(prepared_payload["model_reasoning_effort"], "high")
        self.assertEqual(prepared_payload["repository_profile"].model, "repository-model")
        self.assertEqual(
            prepared_payload["repository_profile"].model_reasoning_effort,
            "medium",
        )

    def test_execution_profile_end_to_end_acceptance(self) -> None:
        """Exercise category resolution through the real stdin command path.

        Only the Codex binary and safe-validation process boundaries are faked;
        policy loading, profile resolution, run_codex transport, command building,
        and execution-artifact persistence remain production code.
        """
        prompt = "E2E-PROFILE-PROMPT-9df1"
        original_subprocess_run = subprocess.run

        def run_case(
            payload_overrides: dict[str, object],
            *,
            profile_model: str | None = None,
            profile_effort: str | None = None,
            validation_results: list[ValidationExecutionResult] | None = None,
            timeout_first: bool = False,
        ) -> tuple[dict, list[tuple[list[str], str]], list[Path]]:
            calls: list[tuple[list[str], str]] = []

            def transport(command, **kwargs):
                if "input" not in kwargs:
                    return original_subprocess_run(command, **kwargs)
                calls.append((list(command), kwargs["input"]))
                if timeout_first and len(calls) == 1:
                    raise subprocess.TimeoutExpired(command, kwargs["timeout"], output="", stderr="")
                return subprocess.CompletedProcess(command, 0, kwargs["input"], kwargs["input"])

            with tempfile.TemporaryDirectory(dir="/tmp") as raw, tempfile.TemporaryDirectory(dir="/tmp") as work_dir:
                root = Path(raw)
                (root / ".git").mkdir()
                profile = _safe_adapter_profile(root)
                profile = replace(
                    profile,
                    model=profile_model,
                    model_reasoning_effort=profile_effort,
                )
                payload = {
                    "prompt": prompt,
                    "worktree_path": str(root),
                    "work_dir": work_dir,
                    "repository_profile": profile,
                    **payload_overrides,
                }
                validation = validation_results or [_safe_execution_result("passed")]
                with mock.patch("run_codex.shutil.which", return_value="/fake/codex"), mock.patch(
                    "run_codex.subprocess.run", side_effect=transport,
                ), mock.patch(
                    "adapters.codex_cli.execute_repository_validation",
                    side_effect=validation,
                ):
                    result = CodexCliAdapter().execute_prepared_worktree(payload)
                run_root = Path(work_dir) / "execution_runs"
                artifacts = sorted(run_root.iterdir()) if run_root.exists() else []
                artifact_snapshots = [
                    (
                        run_dir / "stdout.txt",
                        run_dir / "stderr.txt",
                        run_dir / "meta.json",
                        run_dir / "prompt.txt",
                    )
                    for run_dir in artifacts
                ]
                copied_artifacts: list[Path] = []
                for stdout_path, stderr_path, meta_path, prompt_path in artifact_snapshots:
                    self.assertFalse(prompt_path.exists())
                    for path in (stdout_path, stderr_path, meta_path):
                        self.assertNotIn(prompt, path.read_text(encoding="utf-8"))
                    copied_artifacts.append(meta_path)
                return result, calls, copied_artifacts

        def assert_command_profile(command: list[str], model: str, effort: str) -> None:
            self.assertEqual(command[:2], ["codex", "exec"])
            self.assertEqual(command[-1], "-")
            self.assertNotIn(prompt, command)
            self.assertEqual(command[command.index("-m") + 1], model)
            self.assertIn(f'model_reasoning_effort="{effort}"', command)

        category_result, category_calls, category_artifacts = run_case({"declared_category": "docs_only"})
        self.assertEqual(len(category_calls), 1)
        category_command, category_stdin = category_calls[0]
        assert_command_profile(category_command, "gpt-5.6-terra", "low")
        self.assertIn(prompt, category_stdin)
        self.assertEqual(len(category_artifacts), 1)
        category_evidence = category_result["validation_attempts"][0]
        self.assertEqual(
            {key: category_evidence[key] for key in (
                "model", "model_source", "model_reasoning_effort", "model_reasoning_effort_source",
            )},
            {
                "model": "gpt-5.6-terra",
                "model_source": "category",
                "model_reasoning_effort": "low",
                "model_reasoning_effort_source": "category",
            },
        )

        field_result, field_calls, _ = run_case(
            {"declared_category": "docs_only", "model": "task-model"},
            profile_model="repo-model",
            profile_effort="high",
        )
        assert_command_profile(field_calls[0][0], "task-model", "low")
        field_evidence = field_result["validation_attempts"][0]
        self.assertEqual(field_evidence["model_source"], "task")
        self.assertEqual(field_evidence["model_reasoning_effort_source"], "category")

        repository_result, repository_calls, _ = run_case(
            {}, profile_model="repo-model", profile_effort="high",
        )
        assert_command_profile(repository_calls[0][0], "repo-model", "high")
        repository_evidence = repository_result["validation_attempts"][0]
        self.assertEqual(repository_evidence["model_source"], "repository_profile")
        self.assertEqual(repository_evidence["model_reasoning_effort_source"], "repository_profile")

        default_result, default_calls, _ = run_case({})
        assert_command_profile(default_calls[0][0], "gpt-5.6-terra", "low")
        default_evidence = default_result["validation_attempts"][0]
        self.assertEqual(default_evidence["model_source"], "default")
        self.assertEqual(default_evidence["model_reasoning_effort_source"], "default")

        timeout_result, timeout_calls, _ = run_case(
            {"declared_category": "runtime_fix_high_risk"}, timeout_first=True,
        )
        self.assertEqual(timeout_result["status"], "completed")
        self.assertEqual(len(timeout_calls), 2)
        for command, stdin in timeout_calls:
            assert_command_profile(command, "gpt-5.6", "medium")
            self.assertIn(prompt, stdin)

        repair_result, repair_calls, _ = run_case(
            {"declared_category": "runtime_fix_high_risk"},
            validation_results=[_safe_execution_result("failed"), _safe_execution_result("passed")],
        )
        self.assertEqual([entry["phase"] for entry in repair_result["validation_attempts"]], ["initial", "repair"])
        self.assertEqual(len(repair_calls), 2)
        for command, _ in repair_calls:
            assert_command_profile(command, "gpt-5.6", "medium")

        with tempfile.TemporaryDirectory(dir="/tmp") as raw, tempfile.TemporaryDirectory(dir="/tmp") as work_dir:
            root = Path(raw)
            (root / ".git").mkdir()
            with mock.patch("adapters.codex_cli.run_codex") as run_codex_mock:
                invalid_result = CodexCliAdapter().execute_prepared_worktree({
                    "prompt": prompt,
                    "worktree_path": str(root),
                    "work_dir": work_dir,
                    "repository_profile": _safe_adapter_profile(root),
                    "declared_category": "unsupported_category",
                })
        self.assertEqual(invalid_result["status"], "failed")
        self.assertEqual(invalid_result["error"], "codex_execution.category.invalid")
        run_codex_mock.assert_not_called()

    def test_stub_adapters_do_not_execute(self) -> None:
        with self.assertRaises(NotImplementedError):
            ChatgptTasksAdapter().execute({})
        with self.assertRaises(NotImplementedError):
            LocalLlmAdapter().execute({})


def _safe_adapter_profile(root: Path):
    return validate_repository_profile({
        "schema_version": "1", "profile_id": "execution-path", "repository_root": str(root),
        "base_branch": "main", "python_executable": sys.executable,
        "validation_commands": [{"command_id": kind, "kind": kind,
            "argv": [sys.executable, "-m", "py_compile", "x.py"], "cwd": str(root),
            "timeout_seconds": 10, "required": True, "stop_on_failure": True}
            for kind in ("focused", "related_regression", "full", "compile", "diff_check")],
        "artifact_requirements": [], "forbidden_git_operations": list(FORBIDDEN_GIT_OPERATION_IDS),
        "max_changed_files": 2,
        "approval_boundary": {action: "automatic" for action in APPROVAL_ACTIONS},
        "environment_allowlist": [],
    })


def _prepared_git_directory(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)


def _safe_execution_result(status: str) -> ValidationExecutionResult:
    command_status = "passed" if status == "passed" else "failed"
    command = ValidationCommandResult("focused", "focused", (sys.executable, "-m", "py_compile", "x.py"), "/tmp", True, True, command_status, 0 if command_status == "passed" else 1, f"safe_validation.command.{command_status}", "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:01.000000Z", 1.0, "", "", False, False)
    return ValidationExecutionResult(1, "execution-path", "/tmp", status, "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:01.000000Z", 1.0, (command,), () if status == "passed" else ("focused",), (), False, None)


def _adapter_payload(root: Path, work_dir: str) -> dict:
    return {"prompt": "test prompt", "repo_path": str(root), "work_dir": work_dir,
            "repository_profile": _safe_adapter_profile(root)}


def _replacement_adapter_completed(self) -> None:
    adapter = CodexCliAdapter()
    with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as work_dir:
        root = Path(raw)
        _prepared_git_directory(root)
        execution = {"status": "completed", "return_code": 0, "started_at": "a", "finished_at": "b", "artifacts": [], "error": ""}
        with mock.patch("adapters.codex_cli.prepare_git_worktree", return_value={"created": True, "cleanup_needed": True, "worktree_path": str(root), "branch_name": "branch", "error": ""}), mock.patch("adapters.codex_cli.cleanup_git_worktree", return_value={"error": ""}), mock.patch("adapters.codex_cli.bind_repository_profile_to_worktree", side_effect=lambda profile, _: profile), mock.patch("adapters.codex_cli.run_codex", return_value=execution) as codex, mock.patch("adapters.codex_cli.execute_repository_validation", return_value=_safe_execution_result("passed")) as validation:
            result = adapter.execute(_adapter_payload(root, work_dir))
    self.assertEqual(result["status"], "completed")
    self.assertEqual(result["verify"]["reason"], "validation_passed")
    codex.assert_called_once()
    validation.assert_called_once()


def _replacement_adapter_failed_execution(self) -> None:
    adapter = CodexCliAdapter()
    with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as work_dir:
        root = Path(raw)
        _prepared_git_directory(root)
        execution = {"status": "failed", "return_code": 1, "started_at": "a", "finished_at": "b", "artifacts": [], "error": "failed"}
        with mock.patch("adapters.codex_cli.prepare_git_worktree", return_value={"created": True, "cleanup_needed": True, "worktree_path": str(root), "branch_name": "branch", "error": ""}), mock.patch("adapters.codex_cli.cleanup_git_worktree", return_value={"error": ""}), mock.patch("adapters.codex_cli.bind_repository_profile_to_worktree", side_effect=lambda profile, _: profile), mock.patch("adapters.codex_cli.run_codex", return_value=execution), mock.patch("adapters.codex_cli.execute_repository_validation") as validation:
            result = adapter.execute(_adapter_payload(root, work_dir))
    self.assertEqual(result["verify"]["status"], "not_run")
    validation.assert_not_called()


def _replacement_adapter_retry(self) -> None:
    adapter = CodexCliAdapter()
    with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as work_dir:
        root = Path(raw)
        _prepared_git_directory(root)
        execution = {"status": "completed", "return_code": 0, "started_at": "a", "finished_at": "b", "artifacts": [], "error": ""}
        with mock.patch("adapters.codex_cli.prepare_git_worktree", return_value={"created": True, "cleanup_needed": True, "worktree_path": str(root), "branch_name": "branch", "error": ""}), mock.patch("adapters.codex_cli.cleanup_git_worktree", return_value={"error": ""}), mock.patch("adapters.codex_cli.bind_repository_profile_to_worktree", side_effect=lambda profile, _: profile), mock.patch("adapters.codex_cli.run_codex", side_effect=[execution, execution]) as codex, mock.patch("adapters.codex_cli.execute_repository_validation", side_effect=[_safe_execution_result("failed"), _safe_execution_result("passed")]) as validation:
            result = adapter.execute(_adapter_payload(root, work_dir))
    self.assertEqual(result["retry"]["outcome"], "retry_succeeded")
    self.assertEqual(codex.call_count, 2)
    self.assertEqual(validation.call_count, 2)


class OrchestratorExecutionSemanticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._profile_loader = mock.patch(
            "orchestrator.main.load_repository_profile",
            return_value=_safe_adapter_profile(Path.cwd()),
        )
        self._profile_loader.start()
        self.addCleanup(self._profile_loader.stop)

    def _fake_evaluation_result(self, job_id: str) -> dict:
        return {
            "job_id": job_id,
            "classification": {
                "declared_category": "feature",
                "observed_category": "feature",
            },
            "rubric": {"merge_eligible": False},
            "merge_gate": {"passed": False},
            "assumptions": {"fallbacks_used": []},
        }

    def _candidate_evaluation_result(self, job_id: str) -> dict:
        return {
            "job_id": job_id,
            "classification": {
                "declared_category": "docs_only",
                "observed_category": "docs_only",
            },
            "rubric": {"merge_eligible": True},
            "merge_gate": {"passed": True, "auto_merge_allowed": True},
            "assumptions": {"fallbacks_used": []},
        }

    def _single_output_dir(self, output_root: str) -> Path:
        output_dirs = list(Path(output_root).iterdir())
        self.assertEqual(len(output_dirs), 1)
        return output_dirs[0]

    def _read_single_result(self, output_root: str) -> dict:
        output_dir = self._single_output_dir(output_root)
        return json.loads((output_dir / "result.json").read_text(encoding="utf-8"))

    def _read_single_request(self, output_root: str) -> dict:
        output_dir = self._single_output_dir(output_root)
        return json.loads((output_dir / "request.json").read_text(encoding="utf-8"))

    def _run_git(self, repo_dir: str, args: list[str]) -> str:
        proc = subprocess.run(
            ["git", "-C", repo_dir, *args],
            check=True,
            text=True,
            capture_output=True,
        )
        return proc.stdout.strip()

    def _git_commit(self, repo_dir: str, message: str) -> None:
        self._run_git(
            repo_dir,
            [
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                message,
            ],
        )

    def _init_mergeable_repo(self, repo_dir: str) -> dict[str, str]:
        self._run_git(repo_dir, ["init"])
        self._run_git(repo_dir, ["checkout", "-b", "main"])
        (Path(repo_dir) / "README.md").write_text("base\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "README.md"])
        self._git_commit(repo_dir, "base")
        base_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "-b", "feature"])
        (Path(repo_dir) / "feature.txt").write_text("feature\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "feature.txt"])
        self._git_commit(repo_dir, "feature")
        source_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "main"])
        return {
            "target_ref": "refs/heads/main",
            "base_sha": base_sha,
            "source_sha": source_sha,
        }

    def _init_repo_with_merge_commit(self, repo_dir: str) -> dict[str, str]:
        identity = self._init_mergeable_repo(repo_dir)
        self._run_git(
            repo_dir,
            [
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "merge",
                "--no-ff",
                "--no-edit",
                identity["source_sha"],
            ],
        )
        post_merge_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])
        return {
            "target_ref": identity["target_ref"],
            "pre_merge_sha": identity["base_sha"],
            "post_merge_sha": post_merge_sha,
            "source_sha": identity["source_sha"],
            "base_sha": identity["base_sha"],
        }

    def test_accepted_status_is_kept_when_execution_fails(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "failed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": "simulated execution failure",
                },
            ) as execute_mock:
                with mock.patch(
                    "sys.argv",
                    [
                        "main.py",
                        "--repo",
                        "codex-local-runner",
                        "--task-type",
                        "orchestration",
                        "--declared-category",
                        "docs_only",
                        "--goal",
                        "verify semantics",
                        "--provider",
                        "codex_cli",
                        "--output-root",
                        output_root,
                    ],
                ):
                    rc = orchestrator_main.main()

            result = self._read_single_result(output_root)
            request_payload = self._read_single_request(output_root)
            output_dir = self._single_output_dir(output_root)
            rubric = json.loads((output_dir / "rubric.json").read_text(encoding="utf-8"))
            merge_gate = json.loads((output_dir / "merge_gate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["execution"]["status"], "failed")
        self.assertEqual(request_payload["declared_category"], "docs_only")
        self.assertEqual(execute_mock.call_args.args[0]["declared_category"], "docs_only")
        self.assertEqual(
            set(result["persistence"].keys()),
            {"evaluation_artifacts", "ledger", "execution_target", "merge_execution", "merge_receipt"},
        )
        self.assertIn("merge_eligible", rubric)
        self.assertIn("required_tests_declared", rubric)
        self.assertIn("passed", merge_gate)
        self.assertIn("auto_merge_allowed", merge_gate)

    def test_acceptance_failure_sets_execution_not_started(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "sys.argv",
                [
                    "main.py",
                    "--repo",
                    "codex-local-runner",
                    "--task-type",
                    "orchestration",
                    "--goal",
                    "verify semantics",
                    "--provider",
                    "unknown_provider",
                    "--output-root",
                    output_root,
                ],
            ):
                rc = orchestrator_main.main()

            result = self._read_single_result(output_root)
            output_dir = self._single_output_dir(output_root)

        self.assertEqual(rc, 1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["execution"]["status"], "not_started")
        self.assertEqual(
            result["persistence"],
            {
                "evaluation_artifacts": "skipped",
                "ledger": "skipped",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        self.assertFalse((output_dir / "rubric.json").exists())
        self.assertFalse((output_dir / "merge_gate.json").exists())

    def test_validation_commands_are_routed_to_execution_payload(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                    "return_code": 0,
                    "attempt_count": 1,
                    "retry": {
                        "attempted": False,
                        "trigger": "not_applicable",
                        "outcome": "not_attempted",
                    },
                    "verify": {
                        "status": "not_run",
                        "success": True,
                        "commands": [],
                        "error": "",
                        "reason": "validation_not_run_execution_status_unknown",
                    },
                    "result_interpretation": "completed_verified_passed",
                    "review_recommendation": "no_review_needed",
                    "review_handoff_summary": {
                        "final_status": "completed",
                        "final_verify_status": "not_run",
                        "final_verify_reason": "validation_not_run_execution_status_unknown",
                        "retry_attempted": False,
                        "retry_outcome": "not_attempted",
                        "result_interpretation": "completed_verified_passed",
                        "review_recommendation": "no_review_needed",
                    },
                    "reviewer_handoff": {
                        "summary": {
                            "final_status": "completed",
                            "final_verify_status": "not_run",
                            "final_verify_reason": "validation_not_run_execution_status_unknown",
                            "retry_attempted": False,
                            "retry_outcome": "not_attempted",
                            "result_interpretation": "completed_verified_passed",
                            "review_recommendation": "no_review_needed",
                        },
                        "execution": {"status": "completed", "attempt_count": 1, "return_code": 0},
                        "validation": {
                            "verify_status": "not_run",
                            "verify_reason": "validation_not_run_execution_status_unknown",
                        },
                    },
                },
            ) as execute_mock:
                with mock.patch(
                    "sys.argv",
                    [
                        "main.py",
                        "--repo",
                        "codex-local-runner",
                        "--task-type",
                        "orchestration",
                        "--goal",
                        "verify semantics",
                        "--provider",
                        "codex_cli",
                        "--output-root",
                        output_root,
                        "--validation-command",
                        "echo one",
                        "--validation-command",
                        "echo two",
                    ],
                ):
                    rc = orchestrator_main.main()

            request_payload = self._read_single_request(output_root)
            result_payload = self._read_single_result(output_root)
            output_dir = self._single_output_dir(output_root)
            rubric = json.loads((output_dir / "rubric.json").read_text(encoding="utf-8"))
            merge_gate = json.loads((output_dir / "merge_gate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        execute_mock.assert_not_called()
        self.assertEqual(request_payload["validation_commands"], [])
        self.assertNotIn("validation_command", request_payload)
        self.assertFalse(rubric["required_tests_declared"])
        self.assertFalse(rubric["required_tests_executed"])
        self.assertFalse(rubric["required_tests_passed"])
        self.assertFalse(rubric["ci_required_checks_green"])
        self.assertFalse(rubric["rollback_metadata_recorded"])
        self.assertIn("passed", merge_gate)
        self.assertIn("auto_merge_allowed", merge_gate)
        self.assertEqual(result_payload["execution"]["error"], "legacy_validation_commands_forbidden")
        self.assertEqual(result_payload["execution"]["status"], "failed")
        self.assertEqual(
            set(result_payload["persistence"].keys()),
            {"evaluation_artifacts", "ledger", "execution_target", "merge_execution", "merge_receipt"},
        )

    def test_persistence_written_when_accepted_and_persistence_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._fake_evaluation_result("job-persist-ok"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation") as record_mock:
                            with mock.patch(
                                "sys.argv",
                                [
                                    "main.py",
                                    "--repo",
                                    "codex-local-runner",
                                    "--task-type",
                                    "orchestration",
                                    "--goal",
                                    "persistence observability",
                                    "--provider",
                                    "codex_cli",
                                    "--output-root",
                                    output_root,
                                ],
                            ):
                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        record_mock.assert_called_once()

    def test_persistence_evaluation_failure_remains_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._fake_evaluation_result("job-persist-fail"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        side_effect=RuntimeError("persist failed"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch(
                                "sys.argv",
                                [
                                    "main.py",
                                    "--repo",
                                    "codex-local-runner",
                                    "--task-type",
                                    "orchestration",
                                    "--goal",
                                    "persistence observability",
                                    "--provider",
                                    "codex_cli",
                                    "--output-root",
                                    output_root,
                                ],
                            ):
                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "failed",
                "ledger": "written",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )

    def test_accepted_flow_records_ledger_row(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "failed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": "simulated execution failure",
                },
            ):
                with mock.patch("orchestrator.main.record_job_evaluation") as record_mock:
                    with mock.patch(
                        "sys.argv",
                        [
                            "main.py",
                            "--repo",
                            "codex-local-runner",
                            "--task-type",
                            "orchestration",
                            "--goal",
                            "record ledger",
                            "--provider",
                            "codex_cli",
                            "--output-root",
                            output_root,
                        ],
                    ):
                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)
            output_dir = self._single_output_dir(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        record_mock.assert_called_once()
        kwargs = record_mock.call_args.kwargs
        self.assertEqual(kwargs["accepted_status"], "accepted")
        self.assertEqual(kwargs["request_path"], str(output_dir / "request.json"))
        self.assertEqual(kwargs["result_path"], str(output_dir / "result.json"))
        self.assertEqual(kwargs["rubric_path"], str(output_dir / "rubric.json"))
        self.assertEqual(kwargs["merge_gate_path"], str(output_dir / "merge_gate.json"))
        self.assertIsNone(kwargs["classification_path"])

    def test_acceptance_failure_skips_ledger_recording(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch("orchestrator.main.record_job_evaluation") as record_mock:
                with mock.patch(
                    "sys.argv",
                    [
                        "main.py",
                        "--repo",
                        "codex-local-runner",
                        "--task-type",
                        "orchestration",
                        "--goal",
                        "record ledger",
                        "--provider",
                        "unknown_provider",
                        "--output-root",
                        output_root,
                    ],
                ):
                    rc = orchestrator_main.main()

            result = self._read_single_result(output_root)
            output_dir = self._single_output_dir(output_root)

        self.assertEqual(rc, 1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["execution"]["status"], "not_started")
        record_mock.assert_not_called()
        self.assertFalse((output_dir / "rubric.json").exists())
        self.assertFalse((output_dir / "merge_gate.json").exists())

    def test_ledger_write_failure_does_not_flip_accepted_status(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._fake_evaluation_result("job-ledger-fail"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch(
                            "orchestrator.main.record_job_evaluation",
                            side_effect=RuntimeError("ledger write failed"),
                        ):
                            with mock.patch(
                                "sys.argv",
                                [
                                    "main.py",
                                    "--repo",
                                    "codex-local-runner",
                                    "--task-type",
                                    "orchestration",
                                    "--goal",
                                    "record ledger",
                                    "--provider",
                                    "codex_cli",
                                    "--output-root",
                                    output_root,
                                ],
                            ):
                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)
        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["status"], "completed")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "failed",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )

    def test_execution_target_capture_written_for_accepted_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-candidate-written"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target") as capture_mock:
                                with mock.patch(
                                    "sys.argv",
                                    [
                                        "main.py",
                                        "--repo",
                                        "codex-local-runner",
                                        "--task-type",
                                        "orchestration",
                                        "--goal",
                                        "capture execution target",
                                        "--provider",
                                        "codex_cli",
                                        "--output-root",
                                        output_root,
                                        "--target-ref",
                                        "refs/heads/main",
                                        "--source-sha",
                                        "a" * 40,
                                        "--base-sha",
                                        "b" * 40,
                                    ],
                                ):
                                    rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        capture_mock.assert_called_once()
        self.assertEqual(capture_mock.call_args.kwargs["target_ref"], "refs/heads/main")
        self.assertEqual(capture_mock.call_args.kwargs["source_sha"], "a" * 40)
        self.assertEqual(capture_mock.call_args.kwargs["base_sha"], "b" * 40)

    def test_execution_target_capture_skipped_when_identity_prereqs_missing(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-candidate-skipped"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target") as capture_mock:
                                with mock.patch(
                                    "sys.argv",
                                    [
                                        "main.py",
                                        "--repo",
                                        "codex-local-runner",
                                        "--task-type",
                                        "orchestration",
                                        "--goal",
                                        "capture execution target",
                                        "--provider",
                                        "codex_cli",
                                        "--output-root",
                                        output_root,
                                    ],
                                ):
                                    rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        capture_mock.assert_not_called()

    def test_execution_target_capture_failure_remains_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-candidate-failed"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch(
                                "orchestrator.main.record_execution_target",
                                side_effect=RuntimeError("capture failed"),
                            ):
                                with mock.patch(
                                    "sys.argv",
                                    [
                                        "main.py",
                                        "--repo",
                                        "codex-local-runner",
                                        "--task-type",
                                        "orchestration",
                                        "--goal",
                                        "capture execution target",
                                        "--provider",
                                        "codex_cli",
                                        "--output-root",
                                        output_root,
                                        "--target-ref",
                                        "refs/heads/main",
                                        "--source-sha",
                                        "a" * 40,
                                        "--base-sha",
                                        "b" * 40,
                                    ],
                                ):
                                    rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["status"], "completed")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "failed",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )

    def test_merge_receipt_written_when_attempt_signal_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                    "merge_attempt": {
                        "status": "failed",
                        "attempted_at": "2026-01-01T00:00:02+00:00",
                        "result_sha": None,
                        "error": "simulated conflict",
                    },
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-receipt-written"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.record_merge_attempt_receipt"
                                ) as receipt_mock:
                                    with mock.patch(
                                        "sys.argv",
                                        [
                                            "main.py",
                                            "--repo",
                                            "codex-local-runner",
                                            "--task-type",
                                            "orchestration",
                                            "--goal",
                                            "record merge receipt",
                                            "--provider",
                                            "codex_cli",
                                            "--output-root",
                                            output_root,
                                            "--target-ref",
                                            "refs/heads/main",
                                            "--source-sha",
                                            "a" * 40,
                                            "--base-sha",
                                            "b" * 40,
                                        ],
                                    ):
                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "skipped",
                "merge_receipt": "written",
            },
        )
        receipt_mock.assert_called_once()
        self.assertEqual(receipt_mock.call_args.kwargs["merge_attempt_status"], "failed")
        self.assertEqual(
            receipt_mock.call_args.kwargs["merge_attempted_at"],
            "2026-01-01T00:00:02+00:00",
        )

    def test_merge_receipt_skipped_when_no_trustworthy_attempt_signal(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-receipt-skipped"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.record_merge_attempt_receipt"
                                ) as receipt_mock:
                                    with mock.patch(
                                        "sys.argv",
                                        [
                                            "main.py",
                                            "--repo",
                                            "codex-local-runner",
                                            "--task-type",
                                            "orchestration",
                                            "--goal",
                                            "record merge receipt",
                                            "--provider",
                                            "codex_cli",
                                            "--output-root",
                                            output_root,
                                            "--target-ref",
                                            "refs/heads/main",
                                            "--source-sha",
                                            "a" * 40,
                                            "--base-sha",
                                            "b" * 40,
                                        ],
                                    ):
                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        receipt_mock.assert_not_called()

    def test_merge_receipt_skips_when_signal_present_but_linkage_identity_missing(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                    "merge_attempt": {
                        "status": "attempted",
                        "attempted_at": "2026-01-01T00:00:02+00:00",
                        "result_sha": None,
                        "error": None,
                    },
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-receipt-no-linkage"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target") as target_mock:
                                with mock.patch(
                                    "orchestrator.main.record_merge_attempt_receipt"
                                ) as receipt_mock:
                                    with mock.patch(
                                        "sys.argv",
                                        [
                                            "main.py",
                                            "--repo",
                                            "codex-local-runner",
                                            "--task-type",
                                            "orchestration",
                                            "--goal",
                                            "record merge receipt",
                                            "--provider",
                                            "codex_cli",
                                            "--output-root",
                                            output_root,
                                        ],
                                    ):
                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "skipped",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
            },
        )
        target_mock.assert_not_called()
        receipt_mock.assert_not_called()

    def test_merge_receipt_write_failure_remains_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as output_root:
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                    "merge_attempt": {
                        "status": "failed",
                        "attempted_at": "2026-01-01T00:00:02+00:00",
                        "result_sha": None,
                        "error": "simulated conflict",
                    },
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-receipt-failed"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.record_merge_attempt_receipt",
                                    side_effect=RuntimeError("receipt write failed"),
                                ):
                                    with mock.patch(
                                        "sys.argv",
                                        [
                                            "main.py",
                                            "--repo",
                                            "codex-local-runner",
                                            "--task-type",
                                            "orchestration",
                                            "--goal",
                                            "record merge receipt",
                                            "--provider",
                                            "codex_cli",
                                            "--output-root",
                                            output_root,
                                            "--target-ref",
                                            "refs/heads/main",
                                            "--source-sha",
                                            "a" * 40,
                                            "--base-sha",
                                            "b" * 40,
                                        ],
                                    ):
                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["status"], "completed")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "skipped",
                "merge_receipt": "failed",
            },
        )

    def test_constrained_merge_execution_succeeds_with_persisted_target_identity(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_identity = self._init_mergeable_repo(repo_dir)
            candidate_key = "c" * 64
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-exec-success"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.get_execution_target_by_identity",
                                    return_value={"candidate_idempotency_key": candidate_key},
                                ):
                                    with mock.patch(
                                        "orchestrator.main.get_merge_execution_by_candidate_idempotency_key",
                                        return_value=None,
                                    ):
                                        with mock.patch(
                                            "orchestrator.main.record_merge_execution_outcome"
                                        ) as merge_state_mock:
                                            with mock.patch(
                                                "orchestrator.main.record_merge_attempt_receipt"
                                            ) as receipt_mock:
                                                with mock.patch(
                                                    "orchestrator.main.record_rollback_traceability_for_candidate",
                                                    return_value={
                                                        "rollback_trace_id": "rt-1",
                                                        "rollback_eligible": 1,
                                                        "ineligible_reason": None,
                                                    },
                                                ) as rollback_trace_mock:
                                                    with mock.patch(
                                                        "sys.argv",
                                                        [
                                                            "main.py",
                                                            "--repo",
                                                            "codex-local-runner",
                                                            "--task-type",
                                                            "orchestration",
                                                            "--goal",
                                                            "execute constrained merge",
                                                            "--provider",
                                                            "codex_cli",
                                                            "--output-root",
                                                            output_root,
                                                            "--execution-repo-path",
                                                            repo_dir,
                                                            "--target-ref",
                                                            merge_identity["target_ref"],
                                                            "--source-sha",
                                                            merge_identity["source_sha"],
                                                            "--base-sha",
                                                            merge_identity["base_sha"],
                                                            "--execute-merge",
                                                        ],
                                                    ):
                                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)
            post_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        merge_execution = result_payload["execution"]["merge_execution"]
        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(merge_execution["status"], "succeeded")
        self.assertTrue(merge_execution["attempted"])
        self.assertEqual(merge_execution["candidate_idempotency_key"], candidate_key)
        self.assertEqual(merge_execution["pre_merge_sha"], merge_identity["base_sha"])
        self.assertEqual(merge_execution["post_merge_sha"], post_sha)
        self.assertEqual(merge_execution["merge_result_sha"], post_sha)
        self.assertTrue(merge_execution["rollback_trace"]["recorded"])
        self.assertTrue(merge_execution["rollback_trace"]["eligible"])
        self.assertEqual(merge_execution["rollback_trace"]["rollback_trace_id"], "rt-1")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "written",
                "merge_receipt": "written",
                "rollback_trace": "written",
            },
        )
        merge_state_mock.assert_called_once()
        self.assertEqual(merge_state_mock.call_args.kwargs["pre_merge_sha"], merge_identity["base_sha"])
        self.assertEqual(merge_state_mock.call_args.kwargs["post_merge_sha"], post_sha)
        receipt_mock.assert_called_once()
        self.assertEqual(receipt_mock.call_args.kwargs["merge_attempt_status"], "succeeded")
        rollback_trace_mock.assert_called_once()

    def test_constrained_merge_execution_skips_when_persisted_identity_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_identity = self._init_mergeable_repo(repo_dir)
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-exec-skip-missing"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.get_execution_target_by_identity",
                                    return_value=None,
                                ):
                                    with mock.patch(
                                        "orchestrator.main.execute_constrained_merge"
                                    ) as execute_merge_mock:
                                        with mock.patch(
                                            "sys.argv",
                                            [
                                                "main.py",
                                                "--repo",
                                                "codex-local-runner",
                                                "--task-type",
                                                "orchestration",
                                                "--goal",
                                                "execute constrained merge",
                                                "--provider",
                                                "codex_cli",
                                                "--output-root",
                                                output_root,
                                                "--execution-repo-path",
                                                repo_dir,
                                                "--target-ref",
                                                merge_identity["target_ref"],
                                                "--source-sha",
                                                merge_identity["source_sha"],
                                                "--base-sha",
                                                merge_identity["base_sha"],
                                                "--execute-merge",
                                            ],
                                        ):
                                            rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["merge_execution"]["status"], "skipped")
        self.assertEqual(
            result_payload["execution"]["merge_execution"]["error"],
            "execution_target_not_persisted_or_mismatched",
        )
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "skipped",
                "merge_receipt": "skipped",
                "rollback_trace": "skipped",
            },
        )
        execute_merge_mock.assert_not_called()

    def test_constrained_merge_execution_is_protected_from_duplicate_success(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_identity = self._init_mergeable_repo(repo_dir)
            candidate_key = "c" * 64
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-exec-idempotent"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.get_execution_target_by_identity",
                                    return_value={"candidate_idempotency_key": candidate_key},
                                ):
                                    with mock.patch(
                                        "orchestrator.main.get_merge_execution_by_candidate_idempotency_key",
                                        return_value={
                                            "execution_status": "succeeded",
                                            "executed_at": "2026-01-01T00:00:02+00:00",
                                            "pre_merge_sha": merge_identity["base_sha"],
                                            "post_merge_sha": "d" * 40,
                                            "merge_result_sha": "d" * 40,
                                        },
                                    ):
                                        with mock.patch(
                                            "orchestrator.main.execute_constrained_merge"
                                        ) as execute_merge_mock:
                                            with mock.patch(
                                                "orchestrator.main.record_merge_execution_outcome"
                                            ) as merge_state_mock:
                                                with mock.patch(
                                                    "orchestrator.main.record_merge_attempt_receipt"
                                                ) as receipt_mock:
                                                    with mock.patch(
                                                        "orchestrator.main.record_rollback_traceability_for_candidate",
                                                        return_value={
                                                            "rollback_trace_id": "rt-duplicate",
                                                            "rollback_eligible": 0,
                                                            "ineligible_reason": "merge_execution_not_succeeded",
                                                        },
                                                    ) as rollback_trace_mock:
                                                        with mock.patch(
                                                            "sys.argv",
                                                            [
                                                                "main.py",
                                                                "--repo",
                                                                "codex-local-runner",
                                                                "--task-type",
                                                                "orchestration",
                                                                "--goal",
                                                                "execute constrained merge",
                                                                "--provider",
                                                                "codex_cli",
                                                                "--output-root",
                                                                output_root,
                                                                "--execution-repo-path",
                                                                repo_dir,
                                                                "--target-ref",
                                                                merge_identity["target_ref"],
                                                                "--source-sha",
                                                                merge_identity["source_sha"],
                                                                "--base-sha",
                                                                merge_identity["base_sha"],
                                                                "--execute-merge",
                                                            ],
                                                        ):
                                                            rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["merge_execution"]["status"], "skipped")
        self.assertEqual(
            result_payload["execution"]["merge_execution"]["error"],
            "already_merged_for_candidate",
        )
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "written",
                "merge_receipt": "written",
                "rollback_trace": "written",
            },
        )
        execute_merge_mock.assert_not_called()
        merge_state_mock.assert_called_once()
        receipt_mock.assert_called_once()
        self.assertEqual(receipt_mock.call_args.kwargs["merge_attempt_status"], "skipped")
        rollback_trace_mock.assert_called_once()
        self.assertFalse(result_payload["execution"]["merge_execution"]["rollback_trace"]["eligible"])

    def test_merge_execution_success_with_receipt_persistence_failure_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_identity = self._init_mergeable_repo(repo_dir)
            candidate_key = "c" * 64
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-exec-receipt-fail"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.get_execution_target_by_identity",
                                    return_value={"candidate_idempotency_key": candidate_key},
                                ):
                                    with mock.patch(
                                        "orchestrator.main.get_merge_execution_by_candidate_idempotency_key",
                                        return_value=None,
                                    ):
                                        with mock.patch(
                                            "orchestrator.main.record_merge_execution_outcome"
                                        ):
                                            with mock.patch(
                                                "orchestrator.main.record_merge_attempt_receipt",
                                                side_effect=RuntimeError("receipt persistence failed"),
                                            ):
                                                with mock.patch(
                                                    "orchestrator.main.record_rollback_traceability_for_candidate",
                                                    return_value={
                                                        "rollback_trace_id": "rt-receipt-failed",
                                                        "rollback_eligible": 1,
                                                        "ineligible_reason": None,
                                                    },
                                                ) as rollback_trace_mock:
                                                    with mock.patch(
                                                        "sys.argv",
                                                        [
                                                            "main.py",
                                                            "--repo",
                                                            "codex-local-runner",
                                                            "--task-type",
                                                            "orchestration",
                                                            "--goal",
                                                            "execute constrained merge",
                                                            "--provider",
                                                            "codex_cli",
                                                            "--output-root",
                                                            output_root,
                                                            "--execution-repo-path",
                                                            repo_dir,
                                                            "--target-ref",
                                                            merge_identity["target_ref"],
                                                            "--source-sha",
                                                            merge_identity["source_sha"],
                                                            "--base-sha",
                                                            merge_identity["base_sha"],
                                                            "--execute-merge",
                                                        ],
                                                    ):
                                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["merge_execution"]["status"], "succeeded")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "written",
                "merge_receipt": "failed",
                "rollback_trace": "written",
            },
        )
        rollback_trace_mock.assert_called_once()

    def test_merge_execution_rollback_trace_persistence_failure_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_identity = self._init_mergeable_repo(repo_dir)
            candidate_key = "c" * 64
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-merge-exec-rollback-trace-fail"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.record_execution_target"):
                                with mock.patch(
                                    "orchestrator.main.get_execution_target_by_identity",
                                    return_value={"candidate_idempotency_key": candidate_key},
                                ):
                                    with mock.patch(
                                        "orchestrator.main.get_merge_execution_by_candidate_idempotency_key",
                                        return_value=None,
                                    ):
                                        with mock.patch(
                                            "orchestrator.main.record_merge_execution_outcome"
                                        ):
                                            with mock.patch(
                                                "orchestrator.main.record_merge_attempt_receipt",
                                                return_value="receipt-1",
                                            ):
                                                with mock.patch(
                                                    "orchestrator.main.record_rollback_traceability_for_candidate",
                                                    side_effect=RuntimeError("rollback trace write failed"),
                                                ):
                                                    with mock.patch(
                                                        "sys.argv",
                                                        [
                                                            "main.py",
                                                            "--repo",
                                                            "codex-local-runner",
                                                            "--task-type",
                                                            "orchestration",
                                                            "--goal",
                                                            "execute constrained merge",
                                                            "--provider",
                                                            "codex_cli",
                                                            "--output-root",
                                                            output_root,
                                                            "--execution-repo-path",
                                                            repo_dir,
                                                            "--target-ref",
                                                            merge_identity["target_ref"],
                                                            "--source-sha",
                                                            merge_identity["source_sha"],
                                                            "--base-sha",
                                                            merge_identity["base_sha"],
                                                            "--execute-merge",
                                                        ],
                                                    ):
                                                        rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        self.assertEqual(result_payload["execution"]["merge_execution"]["status"], "succeeded")
        self.assertEqual(
            result_payload["persistence"],
            {
                "evaluation_artifacts": "written",
                "ledger": "written",
                "execution_target": "written",
                "merge_execution": "written",
                "merge_receipt": "written",
                "rollback_trace": "failed",
            },
        )
        self.assertFalse(result_payload["execution"]["merge_execution"]["rollback_trace"]["recorded"])
        self.assertFalse(result_payload["execution"]["merge_execution"]["rollback_trace"]["eligible"])

    def test_constrained_rollback_execution_succeeds_with_eligible_trace(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_state = self._init_repo_with_merge_commit(repo_dir)
            trace_id = "trace-rollback-success"
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-rollback-exec-success"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.get_rollback_trace_by_id", return_value={
                                "rollback_trace_id": trace_id,
                                "candidate_idempotency_key": "c" * 64,
                                "job_id": "job-rollback-exec-success",
                                "repo": "codex-local-runner",
                                "target_ref": merge_state["target_ref"],
                                "source_sha": merge_state["source_sha"],
                                "base_sha": merge_state["base_sha"],
                                "pre_merge_sha": merge_state["pre_merge_sha"],
                                "post_merge_sha": merge_state["post_merge_sha"],
                                "rollback_eligible": 1,
                                "ineligible_reason": None,
                            }):
                                with mock.patch(
                                    "orchestrator.main.get_rollback_execution_by_trace_id",
                                    return_value=None,
                                ):
                                    with mock.patch(
                                        "orchestrator.main.record_rollback_execution_outcome"
                                    ) as record_rollback_mock:
                                        with mock.patch(
                                            "sys.argv",
                                            [
                                                "main.py",
                                                "--repo",
                                                "codex-local-runner",
                                                "--task-type",
                                                "orchestration",
                                                "--goal",
                                                "execute constrained rollback",
                                                "--provider",
                                                "codex_cli",
                                                "--output-root",
                                                output_root,
                                                "--execution-repo-path",
                                                repo_dir,
                                                "--execute-rollback",
                                                "--rollback-trace-id",
                                                trace_id,
                                            ],
                                        ):
                                            rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)
            head_after = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["status"], "accepted")
        rollback_execution = result_payload["execution"]["rollback_execution"]
        self.assertEqual(rollback_execution["status"], "succeeded")
        self.assertTrue(rollback_execution["attempted"])
        self.assertEqual(rollback_execution["rollback_trace_id"], trace_id)
        self.assertEqual(rollback_execution["rollback_result_sha"], head_after)
        self.assertEqual(
            result_payload["persistence"]["rollback_execution"],
            "written",
        )
        record_rollback_mock.assert_called_once()

    def test_constrained_rollback_execution_skips_when_trace_is_ineligible(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            merge_state = self._init_repo_with_merge_commit(repo_dir)
            trace_id = "trace-rollback-ineligible"
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-rollback-exec-ineligible"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.get_rollback_trace_by_id", return_value={
                                "rollback_trace_id": trace_id,
                                "repo": "codex-local-runner",
                                "target_ref": merge_state["target_ref"],
                                "pre_merge_sha": merge_state["pre_merge_sha"],
                                "post_merge_sha": merge_state["post_merge_sha"],
                                "rollback_eligible": 0,
                                "ineligible_reason": "merge_execution_not_succeeded",
                            }):
                                with mock.patch(
                                    "orchestrator.main.execute_constrained_rollback"
                                ) as execute_rollback_mock:
                                    with mock.patch(
                                        "orchestrator.main.record_rollback_execution_outcome"
                                    ) as record_rollback_mock:
                                        with mock.patch(
                                            "sys.argv",
                                            [
                                                "main.py",
                                                "--repo",
                                                "codex-local-runner",
                                                "--task-type",
                                                "orchestration",
                                                "--goal",
                                                "execute constrained rollback",
                                                "--provider",
                                                "codex_cli",
                                                "--output-root",
                                                output_root,
                                                "--execution-repo-path",
                                                repo_dir,
                                                "--execute-rollback",
                                                "--rollback-trace-id",
                                                trace_id,
                                            ],
                                        ):
                                            rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["execution"]["rollback_execution"]["status"], "skipped")
        self.assertEqual(
            result_payload["execution"]["rollback_execution"]["error"],
            "merge_execution_not_succeeded",
        )
        self.assertEqual(result_payload["persistence"]["rollback_execution"], "written")
        execute_rollback_mock.assert_not_called()
        record_rollback_mock.assert_called_once()

    def test_constrained_rollback_execution_skips_on_current_state_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            trace_id = "trace-rollback-mismatch"
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-rollback-exec-mismatch"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.get_rollback_trace_by_id", return_value={
                                "rollback_trace_id": trace_id,
                                "candidate_idempotency_key": "c" * 64,
                                "job_id": "job-rollback-exec-mismatch",
                                "repo": "codex-local-runner",
                                "target_ref": "refs/heads/main",
                                "source_sha": "a" * 40,
                                "base_sha": "b" * 40,
                                "pre_merge_sha": "b" * 40,
                                "post_merge_sha": "c" * 40,
                                "rollback_eligible": 1,
                                "ineligible_reason": None,
                            }):
                                with mock.patch(
                                    "orchestrator.main.get_rollback_execution_by_trace_id",
                                    return_value=None,
                                ):
                                    with mock.patch(
                                        "orchestrator.main.execute_constrained_rollback",
                                        return_value={
                                            "status": "skipped",
                                            "attempted": False,
                                            "attempted_at": "2026-01-01T00:00:02+00:00",
                                            "consistency_check_passed": False,
                                            "current_head_sha": "d" * 40,
                                            "rollback_result_sha": None,
                                            "error": "current_head_mismatch_post_merge",
                                        },
                                    ) as execute_rollback_mock:
                                        with mock.patch(
                                            "orchestrator.main.record_rollback_execution_outcome"
                                        ) as record_rollback_mock:
                                            with mock.patch(
                                                "sys.argv",
                                                [
                                                    "main.py",
                                                    "--repo",
                                                    "codex-local-runner",
                                                    "--task-type",
                                                    "orchestration",
                                                    "--goal",
                                                    "execute constrained rollback",
                                                    "--provider",
                                                    "codex_cli",
                                                    "--output-root",
                                                    output_root,
                                                    "--execution-repo-path",
                                                    repo_dir,
                                                    "--execute-rollback",
                                                    "--rollback-trace-id",
                                                    trace_id,
                                                ],
                                            ):
                                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["execution"]["rollback_execution"]["status"], "skipped")
        self.assertEqual(
            result_payload["execution"]["rollback_execution"]["error"],
            "current_head_mismatch_post_merge",
        )
        self.assertEqual(result_payload["persistence"]["rollback_execution"], "written")
        execute_rollback_mock.assert_called_once()
        record_rollback_mock.assert_called_once()

    def test_constrained_rollback_execution_is_protected_from_duplicate_success(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            trace_id = "trace-rollback-duplicate"
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-rollback-exec-duplicate"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.get_rollback_trace_by_id", return_value={
                                "rollback_trace_id": trace_id,
                                "candidate_idempotency_key": "c" * 64,
                                "job_id": "job-rollback-exec-duplicate",
                                "repo": "codex-local-runner",
                                "target_ref": "refs/heads/main",
                                "source_sha": "a" * 40,
                                "base_sha": "b" * 40,
                                "pre_merge_sha": "b" * 40,
                                "post_merge_sha": "c" * 40,
                                "rollback_eligible": 1,
                                "ineligible_reason": None,
                            }):
                                with mock.patch(
                                    "orchestrator.main.get_rollback_execution_by_trace_id",
                                    return_value={
                                        "execution_status": "succeeded",
                                        "attempted_at": "2026-01-01T00:00:03+00:00",
                                        "current_head_sha": "c" * 40,
                                        "rollback_result_sha": "d" * 40,
                                        "consistency_check_passed": 1,
                                    },
                                ):
                                    with mock.patch(
                                        "orchestrator.main.execute_constrained_rollback"
                                    ) as execute_rollback_mock:
                                        with mock.patch(
                                            "orchestrator.main.record_rollback_execution_outcome"
                                        ) as record_rollback_mock:
                                            with mock.patch(
                                                "sys.argv",
                                                [
                                                    "main.py",
                                                    "--repo",
                                                    "codex-local-runner",
                                                    "--task-type",
                                                    "orchestration",
                                                    "--goal",
                                                    "execute constrained rollback",
                                                    "--provider",
                                                    "codex_cli",
                                                    "--output-root",
                                                    output_root,
                                                    "--execution-repo-path",
                                                    repo_dir,
                                                    "--execute-rollback",
                                                    "--rollback-trace-id",
                                                    trace_id,
                                                ],
                                            ):
                                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["execution"]["rollback_execution"]["status"], "skipped")
        self.assertEqual(
            result_payload["execution"]["rollback_execution"]["error"],
            "already_rolled_back_for_trace",
        )
        self.assertEqual(result_payload["persistence"]["rollback_execution"], "written")
        execute_rollback_mock.assert_not_called()
        record_rollback_mock.assert_called_once()

    def test_rollback_execution_persistence_failure_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as output_root, tempfile.TemporaryDirectory() as repo_dir:
            trace_id = "trace-rollback-persist-fail"
            with mock.patch(
                "adapters.codex_cli.CodexCliAdapter.execute",
                return_value={
                    "adapter": "codex_cli",
                    "status": "completed",
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:00:01+00:00",
                    "artifacts": [],
                    "error": None,
                },
            ):
                with mock.patch(
                    "orchestrator.main.evaluate_job_directory",
                    return_value=self._candidate_evaluation_result("job-rollback-exec-persist-fail"),
                ):
                    with mock.patch(
                        "orchestrator.main.persist_evaluation_artifacts",
                        return_value=("rubric.json", "merge_gate.json"),
                    ):
                        with mock.patch("orchestrator.main.record_job_evaluation"):
                            with mock.patch("orchestrator.main.get_rollback_trace_by_id", return_value={
                                "rollback_trace_id": trace_id,
                                "candidate_idempotency_key": "c" * 64,
                                "job_id": "job-rollback-exec-persist-fail",
                                "repo": "codex-local-runner",
                                "target_ref": "refs/heads/main",
                                "source_sha": "a" * 40,
                                "base_sha": "b" * 40,
                                "pre_merge_sha": "b" * 40,
                                "post_merge_sha": "c" * 40,
                                "rollback_eligible": 1,
                                "ineligible_reason": None,
                            }):
                                with mock.patch(
                                    "orchestrator.main.get_rollback_execution_by_trace_id",
                                    return_value=None,
                                ):
                                    with mock.patch(
                                        "orchestrator.main.execute_constrained_rollback",
                                        return_value={
                                            "status": "succeeded",
                                            "attempted": True,
                                            "attempted_at": "2026-01-01T00:00:03+00:00",
                                            "consistency_check_passed": True,
                                            "current_head_sha": "c" * 40,
                                            "rollback_result_sha": "d" * 40,
                                            "error": None,
                                        },
                                    ):
                                        with mock.patch(
                                            "orchestrator.main.record_rollback_execution_outcome",
                                            side_effect=RuntimeError("rollback execution persist failed"),
                                        ):
                                            with mock.patch(
                                                "sys.argv",
                                                [
                                                    "main.py",
                                                    "--repo",
                                                    "codex-local-runner",
                                                    "--task-type",
                                                    "orchestration",
                                                    "--goal",
                                                    "execute constrained rollback",
                                                    "--provider",
                                                    "codex_cli",
                                                    "--output-root",
                                                    output_root,
                                                    "--execution-repo-path",
                                                    repo_dir,
                                                    "--execute-rollback",
                                                    "--rollback-trace-id",
                                                    trace_id,
                                                ],
                                            ):
                                                rc = orchestrator_main.main()

            result_payload = self._read_single_result(output_root)

        self.assertEqual(rc, 0)
        self.assertEqual(result_payload["execution"]["rollback_execution"]["status"], "succeeded")
        self.assertEqual(result_payload["persistence"]["rollback_execution"], "failed")


@unittest.skipUnless(importlib.util.find_spec("flask") is not None, "flask is not installed")
class AppWorktreeIntegrationTests(unittest.TestCase):
    def test_app_run_uses_prepared_worktree_path(self) -> None:
        import app as app_module

        app_module.app.config["TESTING"] = True
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as tasks_dir:
            (Path(repo_dir) / ".git").mkdir()
            latest_task_path = Path(tasks_dir) / "latest_task.json"
            latest_prompt_path = Path(tasks_dir) / "latest_prompt.txt"
            with mock.patch("app.TASKS_DIR", Path(tasks_dir)):
                with mock.patch("app.LATEST_TASK_PATH", latest_task_path):
                    with mock.patch("app.LATEST_PROMPT_PATH", latest_prompt_path):
                        with mock.patch("app.build_prompt", return_value="prompt text"):
                            with mock.patch(
                                "app.prepare_git_worktree",
                                return_value={
                                    "source_repo_path": repo_dir,
                                    "worktree_path": "/prepared/worktree",
                                    "branch_name": "codex-run/20260101_000000",
                                    "created": True,
                                    "cleanup_needed": True,
                                    "error": "",
                                },
                            ):
                                with mock.patch(
                                    "app.cleanup_git_worktree",
                                    return_value={
                                        "worktree_path": "/prepared/worktree",
                                        "branch_name": "codex-run/20260101_000000",
                                        "cleaned": True,
                                        "error": "",
                                    },
                                ):
                                    with mock.patch(
                                        "app.run_validation_commands",
                                        return_value={
                                            "status": "passed",
                                            "success": True,
                                            "commands": [
                                                {
                                                    "command": "echo verify",
                                                    "return_code": 0,
                                                    "stdout": "ok\n",
                                                    "stderr": "",
                                                    "success": True,
                                                }
                                            ],
                                            "command_results": [
                                                {
                                                    "command": "echo verify",
                                                    "status": "passed",
                                                    "return_code": 0,
                                                    "stdout": "ok\n",
                                                    "stderr": "",
                                                }
                                            ],
                                            "error": "",
                                            "summary": {"total": 1, "passed": 1, "failed": 0},
                                            "reason": "validation_passed",
                                        },
                                    ) as verify_mock:
                                        with mock.patch(
                                            "app.run_codex",
                                            return_value={
                                                "status": "completed",
                                                "success": True,
                                                "return_code": 0,
                                                "started_at": "2026-01-01T00:00:00",
                                                "finished_at": "2026-01-01T00:00:01",
                                                "artifacts": [],
                                                "error": "",
                                            },
                                        ) as run_codex_mock:
                                            client = app_module.app.test_client()
                                            response = client.post(
                                                "/run",
                                                data={
                                                    "repo_path": repo_dir,
                                                    "goal": "execute in worktree",
                                                    "allowed_files": "",
                                                    "forbidden_files": "",
                                                    "validation_commands": "echo verify",
                                                    "notes": "",
                                                },
                                            )

        self.assertEqual(response.status_code, 200)
        run_codex_mock.assert_called_once()
        run_call = run_codex_mock.call_args.kwargs
        self.assertEqual(run_call["task"]["repo_path"], "/prepared/worktree")
        verify_mock.assert_called_once_with(
            validation_commands=["echo verify"],
            cwd="/prepared/worktree",
        )


if __name__ == "__main__":
    unittest.main()
