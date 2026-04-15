from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from automation.review.score_engine import score_review_facts

POLICY_VERSION = "deterministic_review_policy.v2"
BLOCKING_FAILURE_CODES = (
    "touched_forbidden_file",
    "hidden_runtime_semantics",
    "contract_drift",
    "prompt_noncompliance",
)


def _decide_recovery(
    *,
    score_total: float,
    failure_codes: list[str],
) -> tuple[str, list[str]]:
    blocking_codes = [code for code in failure_codes if code in BLOCKING_FAILURE_CODES]
    if blocking_codes:
        return "escalate", blocking_codes
    if score_total < 7.0:
        return "escalate", []
    if score_total < 8.0:
        return "reset_and_retry", []
    if score_total < 9.3:
        return "revise_current_state", []
    return "keep", []


def evaluate_recovery_policy(facts: Mapping[str, Any]) -> dict[str, Any]:
    scored = score_review_facts(facts)
    failure_codes = list(scored["failure_codes"])
    score_total = float(scored["score_total"])
    recovery_decision, blocking_codes = _decide_recovery(
        score_total=score_total,
        failure_codes=failure_codes,
    )

    decision_basis = list(scored["decision_basis"])
    for code in blocking_codes:
        marker = f"blocking_failure_code:{code}"
        if marker not in decision_basis:
            decision_basis.append(marker)

    return {
        "score_total": score_total,
        "dimension_scores": dict(scored["dimension_scores"]),
        "failure_codes": failure_codes,
        "recovery_decision": recovery_decision,
        "decision_basis": decision_basis,
        "requires_human_review": True,
        "policy_version": POLICY_VERSION,
        "blocking_failure_codes": blocking_codes,
    }
