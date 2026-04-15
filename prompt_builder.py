"""Compatibility wrapper for prompt builder.

Canonical implementation lives in ``automation.planning.prompt_builder``.
Keep this module as a thin import surface for backward compatibility.
"""

from automation.planning.prompt_builder import build_prompt

__all__ = ["build_prompt"]
