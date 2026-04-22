# prompts/base_token_reduction_rules.md

## Purpose
This file defines standing rules for reducing ChatGPT/Codex token usage in `codex-local-runner`
without lowering correctness, traceability, or safety.

Use these rules as the default baseline for future prompt-driven implementation work.

## Primary principle
If behavior can be expressed as:
- a Python rule
- a YAML policy
- a fixed command grammar
- a deterministic template
- a small helper function
then prefer that over repeated prompt-time reasoning.

## Token reduction rules

### 1. Rules before prose
- Prefer deterministic rule mapping over free-form explanation.
- Prefer enums/flags/thresholds over narrative classification.
- Prefer explicit precedence tables over model guesswork.

### 2. Templates before generated text
- Subjects, summaries, PR text, approval text, and compact operator text should be template-based where possible.
- Use field substitution and short stable blocks.
- Avoid long natural-language generation when concise structured text is enough.

### 3. Fixed commands before free-text parsing
- Approval replies should use fixed commands.
- Unsupported commands must be rejected or marked unsupported.
- Do not guess user intent from arbitrary prose if a fixed grammar is available.

### 4. Config before repeated prompt instructions
- Stable policies belong in `config/*.yaml`.
- Stable wording rules belong in template helpers.
- Stable mapping logic belongs in Python helpers.
- Do not keep re-explaining the same policy in every new prompt.

### 5. Base + delta prompt structure
Future prompting should use:
- base rules file(s)
- narrow delta prompt for the current PR

Do not send repeated long prompts that restate the same standing rules.

### 6. Compact wording
- Keep generated operational text short.
- Normalize wording order.
- Apply deterministic truncation.
- Prefer short labels and summaries to narrative paragraphs.

### 7. Reuse helpers
Before adding new logic, first check whether an existing helper can be reused.
Examples:
- direction mapping helpers
- reply parsing helpers
- compact rendering helpers
- git/PR text templates

### 8. Reject unsupported instead of hallucinating
If compact input is insufficient:
- mark `insufficient_truth`
- mark `unsupported`
- mark `blocked`
Do not manufacture plausible-looking guesses.

### 9. Human review only where needed
Use human approval only for:
- blocked/high-risk/manual-only cases
- explicit approval gates
- hard-stop exceptions

Do not route low-risk deterministic flows through manual review if rules can decide them.

### 10. Keep Codex focused
When writing Codex prompts:
- define exact files
- define exact scope / out-of-scope
- define required enums and mappings
- define required tests
- avoid rhetorical explanations
- avoid unnecessary examples
- keep instructions concrete

### 11. Safety-sensitive paths must remain explicit and tested
Token reduction must never remove clarity around:
- restart blocked/held posture
- manual-only posture
- fleet safety decisions
- rollback/merge guardrails
- unsupported command handling

Do not compress away safety gates.
Make them rule-based, explicit, and tested instead.

### 12. Prefer deterministic CLI/helpers for repeated operator work
If users repeatedly ask for:
- branch names
- commit messages
- PR titles/bodies
- reply normalization
- restart summaries

prefer adding helpers/scripts/templates rather than reusing LLM generation.

## Recommended token-saving assets in repo
Prefer adding or reusing:
- `config/approval_commands.yaml`
- `config/git_workflow_policy.yaml`
- deterministic template helpers
- git workflow rendering helpers
- reply normalization helpers
- branch/commit/PR generation helpers

## Prompt writing rule
For future implementation prompts:
- refer to this file
- describe only the delta
- forbid free-form NLP unless explicitly necessary
- prefer “use existing helper/config/template” wording
- prefer exact file lists

## Quality rule
Token reduction must not reduce correctness.
If a rule is safety-sensitive:
- make it explicit
- test it
- keep it deterministic
- prefer conservative fallback behavior
