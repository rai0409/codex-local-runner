from __future__ import annotations

import unittest

from automation.planning.task_classifier import classify_task_type


class TaskClassifierTests(unittest.TestCase):
    def test_known_task_types_are_preserved(self) -> None:
        self.assertEqual(classify_task_type("inspect_read_only"), "inspect_read_only")
        self.assertEqual(classify_task_type("docs_only"), "docs_only")
        self.assertEqual(classify_task_type("test_only"), "test_only")
        self.assertEqual(
            classify_task_type("correction_from_current_state"),
            "correction_from_current_state",
        )
        self.assertEqual(classify_task_type("regenerate_after_reset"), "regenerate_after_reset")

    def test_alias_and_separator_normalization(self) -> None:
        self.assertEqual(classify_task_type("inspect-read-only"), "inspect_read_only")
        self.assertEqual(classify_task_type("inspect read only"), "inspect_read_only")
        self.assertEqual(
            classify_task_type("inspect_read_only_extension"),
            "inspect_read_only",
        )

    def test_unknown_task_type_deterministically_falls_back_to_docs_only(self) -> None:
        self.assertEqual(classify_task_type("not_a_real_type"), "docs_only")
        self.assertEqual(classify_task_type(None), "docs_only")


if __name__ == "__main__":
    unittest.main()
