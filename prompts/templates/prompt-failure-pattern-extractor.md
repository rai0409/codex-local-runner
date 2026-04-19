Analyze this failed or weak implementation attempt and extract reusable failure patterns.

Repository: codex-local-runner

Task:
[PASTE TASK HERE]

Prompt used:
[PASTE PROMPT HERE]

Observed result:
[PASTE RESULT / DIFF / REVIEW HERE]

Your job:
1. Identify the primary failure pattern.
2. Identify any secondary failure patterns.
3. Classify them using concise labels such as:
   - scope_explosion
   - forbidden_file_touch
   - hidden_runtime_semantics
   - contract_drift
   - weak_backward_compat
   - prompt_noncompliance
   - over_abstraction
4. Explain why the result was unsafe or weak.
5. State whether the branch was salvageable or should have been reset.
6. Produce a short reusable note for the bad-example library.

Output:
- primary failure code
- secondary failure codes
- concise explanation
- salvage vs reset judgment
- future prompt constraint to prevent recurrence