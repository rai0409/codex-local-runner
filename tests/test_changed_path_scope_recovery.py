from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from automation.orchestration.repository_resolved_single_task_controller import (
    MAX_SAFE_SCOPE_AUTO_EXPANSIONS,
    _recover_safe_changed_path_scope,
)


class ChangedPathScopeRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _create(self, *paths: str) -> None:
        for path in paths:
            candidate = self.root / path
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_text("x\n", encoding="utf-8")

    def _recover(self, declared: tuple[str, ...], actual: tuple[str, ...], *, task_id="edinet-fetch-attempt-ledger", untracked: tuple[str, ...] | None = None):
        self._create(*actual)
        return _recover_safe_changed_path_scope(
            self.root, declared, actual, task_id=task_id,
            untracked_files=actual if untracked is None else untracked,
        )

    def test_no_unexpected_files_is_not_needed(self):
        result = self._recover(("src/feature.py",), ("src/feature.py",))
        self.assertFalse(result.scope_recovery_attempted)
        self.assertEqual(result.scope_recovery_status, "not_needed")
        self.assertEqual(result.effective_allowed_changed_paths, ("src/feature.py",))

    def test_real_topix_drift_keeps_declared_scope_and_marks_all_drift_for_trimming(self):
        declared = (
            "alembic/versions/20260823_0008_edinet_fetch_attempt_ledger.py",
            "packages/common/tests/test_existing_ledger.py",
        )
        actual = (
            "alembic/versions/20260824_0008_edinet_fetch_attempt_ledger.py",
            "docs/disclosure_gold_readiness.md",
            "packages/common/tests/test_edinet_fetch_attempt_ledger.py",
        )
        result = self._recover(declared, actual)
        self.assertEqual(result.scope_recovery_status, "trim_required")
        self.assertEqual(result.auto_expanded_paths, ())
        self.assertEqual(result.unresolved_unexpected_changed_files, tuple(sorted(actual)))
        self.assertNotIn("docs/disclosure_gold_readiness.md", result.effective_allowed_changed_paths)
        self.assertEqual(result.declared_allowed_changed_paths, tuple(sorted(declared)))

    def test_real_task_three_normal_db_init_and_metadata_test_reach_trimming(self):
        declared = (
            "alembic/versions/20260823_0009_edinet_fetch_attempt_artifacts.py",
            "packages/common/src/common/db/models/edinet_api.py",
        )
        actual = (
            "alembic/versions/20260825_0009_edinet_fetch_attempt_artifacts.py",
            "packages/common/src/common/db/models/__init__.py",
            "packages/common/tests/test_metadata.py",
        )
        result = self._recover(declared, actual, task_id="edinet-fetch-attempt-artifact-retention")
        self.assertEqual(result.scope_recovery_status, "trim_required")
        self.assertEqual(result.auto_expanded_paths, ())
        self.assertEqual(result.unresolved_unexpected_changed_files, (
            "alembic/versions/20260825_0009_edinet_fetch_attempt_artifacts.py",
            "packages/common/src/common/db/models/__init__.py",
            "packages/common/tests/test_metadata.py",
        ))
        self.assertNotIn("packages/common/src/common/db/models/__init__.py", result.effective_allowed_changed_paths)
        self.assertNotIn("packages/common/tests/test_metadata.py", result.effective_allowed_changed_paths)

    def test_unrelated_new_test_and_existing_test_modification_require_trimming(self):
        declared = ("packages/common/tests/test_existing_ledger.py",)
        for actual, untracked in (
            ("packages/common/tests/test_unrelated.py", ("packages/common/tests/test_unrelated.py",)),
            ("packages/common/tests/test_other.py", ()),
        ):
            with self.subTest(actual=actual):
                result = self._recover(declared, (actual,), untracked=untracked)
                self.assertEqual(result.scope_recovery_status, "trim_required")
                self.assertEqual(result.auto_expanded_paths, ())

    def test_unrelated_migration_and_deletion_require_trimming(self):
        declared = ("alembic/versions/20260823_0008_edinet_fetch_attempt_ledger.py",)
        unrelated = self._recover(declared, ("alembic/versions/20260824_0009_other.py",))
        self.assertEqual(unrelated.scope_recovery_status, "trim_required")
        deletion = _recover_safe_changed_path_scope(
            self.root, ("src/feature.py",), ("src/deleted.py",),
            task_id="task", untracked_files=(),
        )
        self.assertEqual(deletion.scope_recovery_status, "trim_required")

    def test_high_authority_escape_and_absolute_paths_are_blocked(self):
        for path in (
            ".github/workflows/ci.yml", "credentials/token.txt", "../tests/test_feature.py",
            "/tmp/outside.py", "tests\\test_feature.py", "docs/escape\npath.md",
        ):
            with self.subTest(path=path):
                if not path.startswith(("/", "..")) and "\\" not in path and "\n" not in path:
                    self._create(path)
                result = _recover_safe_changed_path_scope(
                    self.root, ("src/feature.py",), (path,), task_id="task",
                    untracked_files=(path,),
                )
                self.assertEqual(result.scope_recovery_status, "blocked")

    def test_symlink_escape_is_blocked_and_generated_name_count_never_expands_scope(self):
        outside = self.root.parent / "outside.py"
        outside.write_text("x\n", encoding="utf-8")
        link = self.root / "packages/common/tests/test_edinet_fetch_attempt_ledger.py"
        link.parent.mkdir(parents=True)
        link.symlink_to(outside)
        relative = str(link.relative_to(self.root))
        symlink = _recover_safe_changed_path_scope(
            self.root, ("packages/common/tests/test_existing.py",), (relative,),
            task_id="edinet-fetch-attempt-ledger", untracked_files=(relative,),
        )
        self.assertEqual(symlink.scope_recovery_status, "blocked")
        declared = tuple(f"alembic/versions/20260823_{number:04d}_task_{number}.py" for number in range(4))
        actual = tuple(f"alembic/versions/20260824_{number:04d}_task_{number}.py" for number in range(4))
        result = self._recover(declared, actual, task_id="task")
        self.assertEqual(MAX_SAFE_SCOPE_AUTO_EXPANSIONS, 3)
        self.assertEqual(result.scope_recovery_status, "trim_required")
        self.assertEqual(result.auto_expanded_paths, ())


if __name__ == "__main__":
    unittest.main()
