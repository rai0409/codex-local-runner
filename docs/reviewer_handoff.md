# reviewer_handoff Contract

## A. Purpose

`reviewer_handoff` is a compact reviewer-facing package for quickly understanding the final run result before reading the full raw payload.

## B. Exact Current Shape

```json
{
  "reviewer_handoff": {
    "summary": { ... },
    "execution": { ... },
    "validation": { ... }
  }
}
```

## C. Field Meanings

`summary` mirrors `review_handoff_summary` semantics exactly:

- `final_status`: final execution status
- `final_verify_status`: final verify status
- `final_verify_reason`: final verify reason
- `retry_attempted`: whether retry was attempted
- `retry_outcome`: retry outcome
- `result_interpretation`: final result interpretation
- `review_recommendation`: final review recommendation

`execution`:

- `status`: final execution status
- `attempt_count`: total execution attempts (including retry attempt when used)
- `return_code`: final execution return code

`validation`:

- `verify_status`: final verify status
- `verify_reason`: final verify reason
- `summary`: included only when present in `verify_result`

## D. Omission Rule

- Optional reviewer-facing sections that are not safely available from existing structured outputs are omitted.
- Omitted sections are not represented as empty objects.

## E. Reviewer Reading Order

1. `summary`
2. `execution`
3. `validation`
4. raw payload only if needed

## F. Minimal Reviewer Checklist

- Read `summary` first.
- Confirm execution status in `execution.status`.
- Confirm verify status and reason in `validation.verify_status` and `validation.verify_reason`.
- Use `validation.summary` when present.
- Consult the raw payload only when `reviewer_handoff` is insufficient.
- Do not infer unsupported optional sections from omission alone.

## G. Example Payload (Exact Current Contract)

```json
{
  "reviewer_handoff": {
    "summary": {
      "final_status": "completed",
      "final_verify_status": "failed",
      "final_verify_reason": "validation_failed",
      "retry_attempted": false,
      "retry_outcome": "not_attempted",
      "result_interpretation": "completed_verified_failed",
      "review_recommendation": "review_recommended"
    },
    "execution": {
      "status": "completed",
      "attempt_count": 1,
      "return_code": 1
    },
    "validation": {
      "verify_status": "failed",
      "verify_reason": "validation_failed"
    }
  }
}
```
