# Prompt649 — Project-Level Iterate-Until-Done Controller

**Status:** success · **Base:** 87de053

`project_loop_controller.py` → `run_project_loop(intent, descriptors, output_queue_dir, *, result_snapshots, max_cycles, ...)`: bounded, offline, deterministic. Chains generate→populate(explicit dir)→completion-gate, iterates over per-cycle result snapshots up to max_cycles (hard cap 10), and emits next_step (finish / wait_for_execution_results / fix_failures / manual_review). No daemon/Codex run, no live-queue mutation, no infinite loop.

Tests: 10 OK (controller) + 69 OK regression. Additive only; main repo safe.

Next: `task_kind_expansion_minimal_safe`.
