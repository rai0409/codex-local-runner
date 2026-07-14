from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from automation.orchestration.planned_runner import live_codex_gate


def _write_spec(tmp_dir: Path, repo: Path, **overrides) -> Path:
    spec = {
        "repo_path": repo.as_posix(),
        "expected_modified_files": ["calculator.py"],
        "expected_unmodified_files": ["test_calculator.py"],
        "required_text": {
            "calculator.py": ["def subtract(a, b):", "return a - b"],
        },
        "forbidden_paths": [],
        "allow_extra_files": False,
    }
    spec.update(overrides)
    spec_path = tmp_dir / "effect_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return spec_path


def _make_sandbox_repo(tmp_dir: Path) -> Path:
    repo = tmp_dir / "sandbox_repo"
    repo.mkdir()
    (repo / "calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / "test_calculator.py").write_text(
        "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    return repo


def _write_lifecycle_fake_codex(tmp_dir: Path) -> Path:
    script = tmp_dir / "fake_codex_lifecycle.py"
    script.write_text(
        """
import json
import os
from pathlib import Path
import subprocess
import sys
import time

mode = os.environ["FAKE_CODEX_LIFECYCLE_MODE"]
repo = Path.cwd()
target = repo / "calculator.py"
target.write_text(target.read_text(encoding="utf-8") + "\\n\\ndef subtract(a, b):\\n    return a - b\\n", encoding="utf-8")
if mode == "child_holds_output":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    print(json.dumps({"status": "success", "summary": "child holds output", "child_pid": child.pid}), flush=True)
elif mode == "success_stays_alive":
    print(json.dumps({"status": "success", "summary": "parent stays alive"}), flush=True)
    time.sleep(30)
elif mode == "malformed_stays_alive":
    print('{"status":"success"', flush=True)
    time.sleep(30)
elif mode == "unauthorized_child":
    child = subprocess.Popen([sys.executable, "-c", "from pathlib import Path; Path('unauthorized.txt').write_text('bad\\\\n')"])
    child.wait()
    print(json.dumps({"status": "success", "summary": "unauthorized child artifact"}), flush=True)
else:
    print(json.dumps({"status": "success", "summary": "normal success"}), flush=True)
""".lstrip(),
        encoding="utf-8",
    )
    return script


def _write_noninteractive_fake_codex(tmp_dir: Path) -> Path:
    script = tmp_dir / "codex"
    script.write_text(
        """
#!{python}
import json
import os
from pathlib import Path
import sys

argv = sys.argv[1:]
record_path = Path(os.environ["FAKE_CODEX_ARGV_PATH"])
target = argv[argv.index("-C") + 1] if "-C" in argv and argv.index("-C") + 1 < len(argv) else ""
valid = argv[:8] == ["-a", "never", "-s", "danger-full-access", "-C", target, "exec", "--skip-git-repo-check"]
record_path.write_text(json.dumps({"argv": argv, "cwd": os.getcwd(), "stdin_isatty": os.isatty(0), "valid": valid}), encoding="utf-8")
if not valid:
    print("Would you like to run the following command?", flush=True)
    sys.stdin.read()
    raise SystemExit(9)
mode = os.environ["FAKE_CODEX_MODE"]
repo = Path(target)
if mode == "success":
    source = repo / "calculator.py"
    source.write_text(source.read_text(encoding="utf-8") + "\\n\\ndef subtract(a, b):\\n    return a - b\\n", encoding="utf-8")
elif mode == "remove_approved":
    (repo / "approved_a.py").unlink()
    (repo / "approved_b.py").unlink()
elif mode == "failure":
    print("execution failure returned to model", flush=True)
    raise SystemExit(7)
print(json.dumps({"status": "success", "summary": "noninteractive fake"}), flush=True)
""".lstrip().replace("{python}", sys.executable),
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _fake_codex_factory(side_effect=None, returncode: int = 0, record: dict | None = None):
    def _fake_run_codex_once(
        *,
        generated_prompt_path,
        stdout_path,
        stderr_path,
        timeout_seconds,
        sandbox_mode="default",
        codex_cwd=None,
    ):
        if record is not None:
            record["sandbox_mode"] = sandbox_mode
            record["codex_cwd"] = codex_cwd
        if side_effect is not None:
            side_effect()
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text('{"status":"success","summary":"fake"}\n', encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        status = "success" if returncode == 0 else "failed"
        result = live_codex_gate._base_result(
            status=status,
            returncode=returncode,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stop_reason="codex_completed" if returncode == 0 else "codex_failed",
            started_at="2026-01-01T00:00:00Z",
            finished_at="2026-01-01T00:00:01Z",
        )
        command = live_codex_gate._build_codex_command(
            "<prompt>", codex_cwd or Path.cwd().as_posix()
        )
        return result, command, True

    return _fake_run_codex_once


class LiveCodexGateEffectVerificationTests(unittest.TestCase):
    def _run_gate(self, tmp_dir: Path, fake_codex, spec_path=None, sandbox_mode="default"):
        prompt_path = tmp_dir / "prompt.md"
        prompt_path.write_text("safe prompt\n", encoding="utf-8")
        with mock.patch.object(live_codex_gate, "_run_codex_once", new=fake_codex):
            return live_codex_gate.run_live_codex_gate(
                generated_prompt_path=prompt_path,
                out_dir=tmp_dir / "out",
                live_codex_enable_token=live_codex_gate.LIVE_CODEX_GATE_ENABLE_TOKEN,
                timeout_seconds=10,
                sandbox_mode=sandbox_mode,
                effect_spec_path=spec_path,
            )

    def test_effect_verification_passes_when_change_applied(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            spec_path = _write_spec(tmp_dir, repo)

            def _apply_change():
                target = repo / "calculator.py"
                target.write_text(
                    target.read_text(encoding="utf-8")
                    + "\n\ndef subtract(a, b):\n    return a - b\n",
                    encoding="utf-8",
                )

            state = self._run_gate(tmp_dir, _fake_codex_factory(side_effect=_apply_change), spec_path)
        self.assertEqual(state["status"], "success")
        self.assertTrue(state["effect_verification_enabled"])
        self.assertEqual(state["effect_verification_status"], "passed")
        self.assertTrue(state["effect_modified_files_verified"])
        self.assertTrue(state["effect_unmodified_files_verified"])
        self.assertTrue(state["effect_required_text_verified"])
        self.assertTrue(state["effect_forbidden_paths_verified"])
        self.assertEqual(state["effect_unexpected_files"], [])
        self.assertEqual(state["effect_verification_errors"], [])
        self.assertEqual(state["next_action"], "commit_tag_gate")

    def test_terminal_codex_output_closes_stdin_before_effect_verification(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            spec_path = _write_spec(tmp_dir, repo)
            prompt_path = tmp_dir / "prompt.md"
            prompt_path.write_text("safe prompt\n", encoding="utf-8")
            observed: dict = {"effect_calls": 0}
            real_popen = subprocess.Popen

            class _FakeProcess:
                pid = 4242
                returncode = 0

                def wait(self, timeout=None):
                    return self.returncode

                def poll(self):
                    return self.returncode

            def _fake_popen(command, **kwargs):
                self.assertEqual(kwargs["stdin"], live_codex_gate.subprocess.DEVNULL)
                environment = kwargs["env"]
                cache_dir = Path(environment["PYTHONPYCACHEPREFIX"])
                self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
                self.assertTrue(cache_dir.is_relative_to(tmp_dir / "out"))
                self.assertFalse(cache_dir.is_relative_to(repo))
                self.assertIn("-q --strict-markers", environment["PYTEST_ADDOPTS"])
                self.assertEqual(environment["PYTEST_ADDOPTS"].count("no:cacheprovider"), 1)
                child = real_popen(
                    [
                        sys.executable,
                        "-c",
                        "import os; print(os.environ['PYTHONDONTWRITEBYTECODE']); "
                        "print(os.environ['PYTHONPYCACHEPREFIX']); "
                        "print(os.environ['PYTEST_ADDOPTS'])",
                    ],
                    env=environment,
                    stdout=subprocess.PIPE,
                    text=True,
                )
                child_stdout, _ = child.communicate(timeout=10)
                observed["child_environment"] = child_stdout.splitlines()
                # Simulate cache-producing Python/pytest behavior only when the
                # isolation environment is absent; the supplied environment must
                # therefore leave no cache artifacts in the target repo.
                if environment.get("PYTHONDONTWRITEBYTECODE") != "1":
                    (repo / "__pycache__").mkdir()
                    (repo / "__pycache__" / "calculator.pyc").write_text("cache")
                if "no:cacheprovider" not in environment.get("PYTEST_ADDOPTS", ""):
                    (repo / ".pytest_cache").mkdir()
                (repo / "calculator.py").write_text(
                    "def add(a, b):\n    return a + b\n\n"
                    "def subtract(a, b):\n    return a - b\n",
                    encoding="utf-8",
                )
                kwargs["stdout"].write('{"status":"success","summary":"fake"}\n')
                kwargs["stderr"].write("")
                return _FakeProcess()

            original_verify = live_codex_gate._verify_effects

            def _verify_once(**kwargs):
                observed["effect_calls"] += 1
                return original_verify(**kwargs)

            with (
                mock.patch.dict(os.environ, {"PYTEST_ADDOPTS": "-q --strict-markers"}, clear=False),
                mock.patch.object(live_codex_gate.shutil, "which", return_value="/fake/codex"),
                mock.patch.object(live_codex_gate.subprocess, "Popen", side_effect=_fake_popen),
                mock.patch.object(live_codex_gate, "_verify_effects", side_effect=_verify_once),
            ):
                state = live_codex_gate.run_live_codex_gate(
                    generated_prompt_path=prompt_path,
                    out_dir=tmp_dir / "out",
                    live_codex_enable_token=live_codex_gate.LIVE_CODEX_GATE_ENABLE_TOKEN,
                    timeout_seconds=10,
                    effect_spec_path=spec_path,
                )

        self.assertEqual(state["status"], "success")
        self.assertEqual(state["returncode"], 0)
        self.assertEqual(state["effect_verification_status"], "passed")
        self.assertEqual(observed["effect_calls"], 1)
        self.assertEqual(observed["child_environment"][0], "1")
        self.assertIn("-q --strict-markers", observed["child_environment"][2])
        self.assertFalse((repo / ".pytest_cache").exists())
        self.assertFalse((repo / "__pycache__").exists())

    def test_existing_pytest_cache_disable_option_is_not_duplicated(self):
        with tempfile.TemporaryDirectory() as raw:
            cache_dir = Path(raw) / "runner_work" / "codex_pycache"
            with mock.patch.dict(
                os.environ,
                {"PYTEST_ADDOPTS": "-q -p no:cacheprovider --strict-markers"},
                clear=False,
            ):
                environment = live_codex_gate._build_codex_environment(cache_dir)
        self.assertEqual(environment["PYTEST_ADDOPTS"].count("no:cacheprovider"), 1)
        self.assertIn("-q", environment["PYTEST_ADDOPTS"])
        self.assertIn("--strict-markers", environment["PYTEST_ADDOPTS"])

    def test_zero_returncode_without_change_is_not_success(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            spec_path = _write_spec(tmp_dir, repo)
            state = self._run_gate(tmp_dir, _fake_codex_factory(), spec_path)
            result = json.loads(Path(state["codex_result_path"]).read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["effect_verification_status"], "failed")
        self.assertEqual(state["stop_reason"], "effect_verification_failed")
        self.assertEqual(state["next_action"], "inspect_missing_expected_effects")
        self.assertFalse(state["effect_modified_files_verified"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["next_action"], "inspect_missing_expected_effects")

    def test_expected_unmodified_files_are_enforced(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            spec_path = _write_spec(tmp_dir, repo)

            def _bad_change():
                calc = repo / "calculator.py"
                calc.write_text(
                    calc.read_text(encoding="utf-8")
                    + "\n\ndef subtract(a, b):\n    return a - b\n",
                    encoding="utf-8",
                )
                (repo / "test_calculator.py").write_text("tampered\n", encoding="utf-8")

            state = self._run_gate(tmp_dir, _fake_codex_factory(side_effect=_bad_change), spec_path)
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["effect_verification_status"], "failed")
        self.assertFalse(state["effect_unmodified_files_verified"])
        self.assertTrue(
            any("test_calculator.py" in err for err in state["effect_verification_errors"])
        )

    def test_forbidden_paths_and_extra_files_are_enforced(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            spec_path = _write_spec(tmp_dir, repo, forbidden_paths=["evil.txt"])

            def _bad_change():
                calc = repo / "calculator.py"
                calc.write_text(
                    calc.read_text(encoding="utf-8")
                    + "\n\ndef subtract(a, b):\n    return a - b\n",
                    encoding="utf-8",
                )
                (repo / "evil.txt").write_text("oops\n", encoding="utf-8")

            state = self._run_gate(tmp_dir, _fake_codex_factory(side_effect=_bad_change), spec_path)
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["effect_verification_status"], "failed")
        self.assertFalse(state["effect_forbidden_paths_verified"])
        self.assertEqual(state["effect_unexpected_files"], ["evil.txt"])

    def test_scope_outside_allowed_files_blocks_success(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            spec_path = _write_spec(
                tmp_dir,
                repo,
                allowed_files=["calculator.py", "test_calculator.py"],
                expected_modified_files=["calculator.py", "test_calculator.py"],
                required_text={
                    "calculator.py": ["def subtract(a, b):"],
                    "test_calculator.py": ["def test_subtract"],
                },
            )

            def _bad_change():
                (repo / "calculator.py").write_text("def subtract(a, b):\n    return a - b\n")
                (repo / "test_calculator.py").write_text("def test_subtract():\n    assert True\n")
                (repo / "unauthorized.txt").write_text("changed = True\n")

            state = self._run_gate(tmp_dir, _fake_codex_factory(side_effect=_bad_change), spec_path)
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["effect_verification_status"], "failed")
        self.assertEqual(state["effect_unexpected_files"], ["unauthorized.txt"])
        self.assertTrue(
            any("outside allowed_files" in error for error in state["effect_verification_errors"])
        )

    def test_default_behavior_without_effect_spec_is_unchanged(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            state = self._run_gate(tmp_dir, _fake_codex_factory(), spec_path=None)
        self.assertEqual(state["status"], "success")
        self.assertEqual(state["next_action"], "commit_tag_gate")
        self.assertEqual(state["stop_reason"], "codex_completed")
        self.assertFalse(state["effect_verification_enabled"])
        self.assertEqual(state["effect_verification_status"], "not_run")
        self.assertEqual(state["sandbox_mode"], "default")
        self.assertEqual(
            state["codex_command"][:8],
            ["codex", "-a", "never", "-s", "danger-full-access", "-C", Path.cwd().as_posix(), "exec"],
        )

    def test_codex_command_is_always_noninteractive(self):
        self.assertEqual(
            live_codex_gate._build_codex_command("p", "/tmp/target_repo"),
            [
                "codex", "-a", "never", "-s", "danger-full-access", "-C",
                "/tmp/target_repo", "exec", "--skip-git-repo-check", "p",
            ],
        )
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            spec_path = _write_spec(tmp_dir, repo)
            record: dict = {}

            def _apply_change():
                target = repo / "calculator.py"
                target.write_text(
                    target.read_text(encoding="utf-8")
                    + "\n\ndef subtract(a, b):\n    return a - b\n",
                    encoding="utf-8",
                )

            state = self._run_gate(
                tmp_dir,
                _fake_codex_factory(side_effect=_apply_change, record=record),
                spec_path,
                sandbox_mode="workspace-write",
            )
        self.assertEqual(record["sandbox_mode"], "workspace-write")
        self.assertEqual(record["codex_cwd"], repo.as_posix())
        self.assertEqual(state["sandbox_mode"], "workspace-write")
        self.assertEqual(state["codex_command"][4], "danger-full-access")
        self.assertEqual(state["codex_command"][6], repo.as_posix())

    def test_invalid_effect_spec_blocks_before_codex(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            spec_path = tmp_dir / "broken_spec.json"
            spec_path.write_text("{not json", encoding="utf-8")
            calls: dict = {}
            state = self._run_gate(tmp_dir, _fake_codex_factory(record=calls), spec_path)
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["stop_reason"], "effect_spec_invalid")
        self.assertEqual(state["next_action"], "manual_review_required")
        self.assertFalse(state["codex_invoked"])
        self.assertEqual(calls, {})

    def test_nonzero_returncode_stays_failed_even_if_effects_match(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            spec_path = _write_spec(tmp_dir, repo)

            def _apply_change():
                target = repo / "calculator.py"
                target.write_text(
                    target.read_text(encoding="utf-8")
                    + "\n\ndef subtract(a, b):\n    return a - b\n",
                    encoding="utf-8",
                )

            state = self._run_gate(
                tmp_dir,
                _fake_codex_factory(side_effect=_apply_change, returncode=1),
                spec_path,
            )
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["effect_verification_status"], "passed")
        self.assertNotEqual(state["next_action"], "commit_tag_gate")


class LiveCodexProcessLifecycleTests(unittest.TestCase):
    def _run_once(self, tmp_dir: Path, repo: Path, mode: str, timeout_seconds: int = 2):
        script = _write_lifecycle_fake_codex(tmp_dir)
        prompt = tmp_dir / "prompt.md"
        prompt.write_text("bounded prompt\n", encoding="utf-8")
        with (
            mock.patch.dict(os.environ, {"FAKE_CODEX_LIFECYCLE_MODE": mode}, clear=False),
            mock.patch.object(live_codex_gate.shutil, "which", return_value=sys.executable),
            mock.patch.object(
                live_codex_gate,
                "_build_codex_command",
                return_value=[sys.executable, script.as_posix()],
            ),
        ):
            return live_codex_gate._run_codex_once(
                generated_prompt_path=prompt,
                stdout_path=tmp_dir / "out" / "codex_stdout.txt",
                stderr_path=tmp_dir / "out" / "codex_stderr.txt",
                timeout_seconds=timeout_seconds,
                codex_cwd=repo.as_posix(),
            )

    def _run_gate(self, tmp_dir: Path, repo: Path, mode: str):
        script = _write_lifecycle_fake_codex(tmp_dir)
        prompt = tmp_dir / "prompt.md"
        prompt.write_text("bounded prompt\n", encoding="utf-8")
        spec_path = _write_spec(tmp_dir, repo)
        with (
            mock.patch.dict(os.environ, {"FAKE_CODEX_LIFECYCLE_MODE": mode}, clear=False),
            mock.patch.object(live_codex_gate.shutil, "which", return_value=sys.executable),
            mock.patch.object(
                live_codex_gate,
                "_build_codex_command",
                return_value=[sys.executable, script.as_posix()],
            ),
        ):
            return live_codex_gate.run_live_codex_gate(
                generated_prompt_path=prompt,
                out_dir=tmp_dir / "out",
                live_codex_enable_token=live_codex_gate.LIVE_CODEX_GATE_ENABLE_TOKEN,
                timeout_seconds=2,
                effect_spec_path=spec_path,
            )

    def test_parent_exit_with_child_holding_output_is_reaped_before_effects(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            started = time.monotonic()
            state = self._run_gate(tmp_dir, repo, "child_holds_output")
            elapsed = time.monotonic() - started
            output = json.loads((tmp_dir / "out" / "codex_execution_result.json").read_text())
            terminal = json.loads((tmp_dir / "out" / "codex_stdout.txt").read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(terminal["child_pid"], 0)
        self.assertLess(elapsed, 5)
        self.assertEqual(state["status"], "success")
        self.assertEqual(state["effect_verification_status"], "passed")
        self.assertTrue(output["execution"]["terminal_result_valid"])
        self.assertTrue(output["execution"]["forced_termination"])

    def test_terminal_success_that_keeps_parent_alive_times_out_without_success(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            started = time.monotonic()
            result, _, invoked = self._run_once(tmp_dir, repo, "success_stays_alive", timeout_seconds=1)
            elapsed = time.monotonic() - started
        self.assertTrue(invoked)
        self.assertLess(elapsed, 5)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["timed_out"])
        self.assertTrue(result["execution"]["terminal_result_valid"])
        self.assertTrue(result["execution"]["forced_termination"])

    def test_normal_terminal_success_requires_clean_exit_and_remains_successful(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            result, _, invoked = self._run_once(tmp_dir, repo, "normal")
        self.assertTrue(invoked)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["returncode"], 0)
        self.assertTrue(result["execution"]["terminal_result_valid"])
        self.assertFalse(result["execution"]["forced_termination"])

    def test_malformed_terminal_output_never_becomes_success(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            result, _, invoked = self._run_once(tmp_dir, repo, "malformed_stays_alive", timeout_seconds=1)
        self.assertTrue(invoked)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["timed_out"])
        self.assertFalse(result["execution"]["terminal_result_valid"])

    def test_unauthorized_child_artifact_still_fails_effect_verification(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            state = self._run_gate(tmp_dir, repo, "unauthorized_child")
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["effect_verification_status"], "failed")
        self.assertIn("unauthorized.txt", state["effect_unexpected_files"])


class LiveCodexNoninteractiveInvocationTests(unittest.TestCase):
    def _run_gate(self, tmp_dir: Path, repo: Path, mode: str, spec_path: Path):
        fake_codex = _write_noninteractive_fake_codex(tmp_dir)
        prompt = tmp_dir / "prompt.md"
        prompt.write_text("safe prompt\n", encoding="utf-8")
        argv_path = tmp_dir / "received_argv.json"
        environment = {
            "PATH": f"{fake_codex.parent}{os.pathsep}{os.environ['PATH']}",
            "FAKE_CODEX_ARGV_PATH": argv_path.as_posix(),
            "FAKE_CODEX_MODE": mode,
        }
        with mock.patch.dict(os.environ, environment, clear=False):
            state = live_codex_gate.run_live_codex_gate(
                generated_prompt_path=prompt,
                out_dir=tmp_dir / "out",
                live_codex_enable_token=live_codex_gate.LIVE_CODEX_GATE_ENABLE_TOKEN,
                timeout_seconds=2,
                effect_spec_path=spec_path,
            )
        return state, json.loads(argv_path.read_text(encoding="utf-8"))

    def test_fake_codex_receives_exact_noninteractive_argv_without_approval_output(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            state, received = self._run_gate(tmp_dir, repo, "success", _write_spec(tmp_dir, repo))
            stdout = (tmp_dir / "out" / "codex_stdout.txt").read_text(encoding="utf-8")

        argv = received["argv"]
        self.assertTrue(received["valid"])
        self.assertFalse(received["stdin_isatty"])
        self.assertEqual(argv.count("exec"), 1)
        self.assertLess(argv.index("-a"), argv.index("exec"))
        self.assertLess(argv.index("never"), argv.index("exec"))
        self.assertLess(argv.index("-s"), argv.index("exec"))
        self.assertLess(argv.index("danger-full-access"), argv.index("exec"))
        self.assertLess(argv.index("-C"), argv.index("exec"))
        self.assertGreater(argv.index("--skip-git-repo-check"), argv.index("exec"))
        self.assertEqual(argv[argv.index("-a") + 1], "never")
        self.assertEqual(argv[argv.index("-s") + 1], "danger-full-access")
        self.assertEqual(argv[argv.index("-C") + 1], repo.as_posix())
        self.assertEqual(argv[-1], "safe prompt\n")
        self.assertNotIn("untrusted", argv)
        self.assertNotIn("on-request", argv)
        self.assertNotIn("Would you like to run the following command?", stdout)
        self.assertEqual(state["status"], "success")
        self.assertEqual(state["effect_verification_status"], "passed")

    def test_approved_removal_completes_without_approval_ui_and_runs_effect_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            (repo / "approved_a.py").write_text("a = 1\n", encoding="utf-8")
            (repo / "approved_b.py").write_text("b = 1\n", encoding="utf-8")
            spec_path = _write_spec(
                tmp_dir,
                repo,
                expected_modified_files=[],
                allowed_files=["approved_a.py", "approved_b.py"],
                expected_unmodified_files=["calculator.py", "test_calculator.py"],
                required_text={},
                forbidden_paths=["approved_a.py", "approved_b.py"],
            )
            state, received = self._run_gate(tmp_dir, repo, "remove_approved", spec_path)
            stdout = (tmp_dir / "out" / "codex_stdout.txt").read_text(encoding="utf-8")

        self.assertTrue(received["valid"])
        self.assertFalse(received["stdin_isatty"])
        self.assertNotIn("Would you like to run the following command?", stdout)
        self.assertFalse((repo / "approved_a.py").exists())
        self.assertFalse((repo / "approved_b.py").exists())
        self.assertEqual(state["effect_verification_status"], "passed")

    def test_execution_failure_never_retries_interactively_or_becomes_success(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            state, received = self._run_gate(tmp_dir, repo, "failure", _write_spec(tmp_dir, repo))
            stdout = (tmp_dir / "out" / "codex_stdout.txt").read_text(encoding="utf-8")

        self.assertTrue(received["valid"])
        self.assertFalse(received["stdin_isatty"])
        self.assertIn("execution failure returned to model", stdout)
        self.assertNotIn("Would you like to run the following command?", stdout)
        self.assertEqual(state["stop_reason"], "codex_failed")
        self.assertEqual(state["status"], "blocked")
        self.assertNotEqual(state["next_action"], "commit_tag_gate")


class VerifyCommandTests(unittest.TestCase):
    def _run_gate_with_commands(self, verify_commands, apply_change=True):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox_repo(tmp_dir)
            spec_path = _write_spec(tmp_dir, repo, verify_commands=verify_commands)

            def _change():
                target = repo / "calculator.py"
                target.write_text(
                    target.read_text(encoding="utf-8")
                    + "\n\ndef subtract(a, b):\n    return a - b\n",
                    encoding="utf-8",
                )

            prompt_path = tmp_dir / "prompt.md"
            prompt_path.write_text("safe prompt\n", encoding="utf-8")
            with mock.patch.object(
                live_codex_gate,
                "_run_codex_once",
                new=_fake_codex_factory(side_effect=_change if apply_change else None),
            ):
                state = live_codex_gate.run_live_codex_gate(
                    generated_prompt_path=prompt_path,
                    out_dir=tmp_dir / "out",
                    live_codex_enable_token=live_codex_gate.LIVE_CODEX_GATE_ENABLE_TOKEN,
                    timeout_seconds=10,
                    effect_spec_path=spec_path,
                )
                command_results = state.get("effect_verify_command_results", [])
                stdout_exists = all(
                    Path(item["stdout_path"]).is_file() for item in command_results
                )
        return state, command_results, stdout_exists

    def test_passing_verify_command_keeps_success(self):
        state, results, stdout_exists = self._run_gate_with_commands(
            [["python", "-c", "from calculator import subtract; assert subtract(7, 4) == 3"]]
        )
        self.assertEqual(state["status"], "success")
        self.assertEqual(state["effect_verification_status"], "passed")
        self.assertTrue(state["effect_verify_commands_passed"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["returncode"], 0)
        self.assertTrue(stdout_exists)

    def test_failing_verify_command_blocks_success(self):
        state, results, _ = self._run_gate_with_commands(
            [["python", "-c", "import sys; sys.exit(3)"]]
        )
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["effect_verification_status"], "failed")
        self.assertEqual(state["stop_reason"], "effect_verification_failed")
        self.assertEqual(state["next_action"], "inspect_missing_expected_effects")
        self.assertFalse(state["effect_verify_commands_passed"])
        self.assertEqual(results[0]["returncode"], 3)
        self.assertTrue(
            any("verify command 1 failed" in err for err in state["effect_verification_errors"])
        )

    def test_disallowed_verify_command_invalidates_spec_before_codex(self):
        state, results, _ = self._run_gate_with_commands([["rm", "-rf", "/"]], apply_change=False)
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["stop_reason"], "effect_spec_invalid")
        self.assertFalse(state["codex_invoked"])
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
