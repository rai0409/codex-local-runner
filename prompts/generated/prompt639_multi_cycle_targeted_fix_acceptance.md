PROMPT639_MULTI_CYCLE_TARGETED_FIX_ACCEPTANCE

NOTE: This file was reconstructed from the user's inline execution instructions.
The originally referenced path did not exist at run time; this copy is saved for
traceability of what was executed.

This is an EXECUTION task, not a design task. Proceed fully autonomously.

You must:
1. Run baseline checks.
2. Execute multi-cycle runtime (>= 3 jobs).
3. Ensure at least one targeted_fix cycle is triggered and resolved.
4. Verify strict effect gate rules:
   - effect_failed must never be marked success
   - no incorrect commit/tag for failed effects
5. Verify main repo HEAD stability during runtime.
6. Ensure sandbox cleanup.
7. Generate:
   - artifacts/autonomous_runtime/prompt639_report.json
   - artifacts/autonomous_runtime/prompt639_summary.md
8. If and only if ALL PASS conditions are met:
   - commit results
   - create tag: prompt639-multi-cycle-targeted-fix-acceptance

Runtime tasks must use only /tmp clones/sandboxes. Do not modify main repo source
files for the runtime. Do not touch artifacts/archive or handoff_reports.

Final output must include prompt639_* stdout fields.
