# Autonomy Browser Orchestrator Specification

## File role
This file is the stable source-of-truth specification for the next autonomy phase.

Future narrow Codex prompts should reference this file instead of re-explaining:
- browser-UI ChatGPT orchestration
- retry / repair / restart policy
- success-proven rolling autonomy
- structured output schema
- external/high-risk action automation policy
- Playwright selector strategy
- Codex token minimization policy

This file is specification-only.
It does not itself change runtime behavior.

### Reuse rule
Future Codex prompts for this autonomy phase should reference this file path directly and avoid re-describing these rules inline unless a narrow delta is being introduced.

---

## Purpose
Build an inner autonomous development orchestrator that uses:
- browser-UI ChatGPT
- Codex
- repository rules / deterministic guards

to continue development as long as success proof remains strong, while attempting automatic recovery before stopping.

The intended system should:
- accept an existing design/spec as input
- continue implementation for long spans
- retry, repair, restart, and replan automatically
- stop only when recovery is not appropriate or minimum hard gates block progress

---

## Core operating model

### High-level principle
This system is **recover-first**, not stop-first.

When failure signs appear:
1. classify the failure
2. attempt bounded recovery
3. verify the result
4. continue if success proof remains strong
5. stop/escalate only if recovery is not appropriate

### Long-run principle
This system is **not blind infinite automation**.

Instead, it uses:
- success-proven rolling autonomy
- one-step continuation renewal
- repeated proof checks
- bounded recovery attempts per failure event

---

## Tool roles

### Browser-UI ChatGPT
Use the strongest available thinking model at all times.

Responsibilities:
- whole-project interpretation
- planning
- roadmap generation
- PR slicing
- prompt generation
- scoring / review judgment
- repair analysis
- restart / replan guidance
- test-spec generation
- high-risk action judgment
- external-operation judgment

### Codex
Responsibilities:
- implementation only
- narrow code edits
- file-local changes
- repository-constrained code generation

Codex should not be the primary tool for:
- broad planning
- large strategic reasoning
- large test design
- scoring / judgment loops

### Local LLM / Python
Responsibilities:
- test skeleton generation
- repetitive boilerplate
- parameterized case expansion
- deterministic helper generation

---

## Browser automation policy

### Browser driver
Primary browser automation must use **Playwright**.

### Why
Playwright is preferred for:
- repeated stable UI interaction
- DOM/event waiting
- long-running orchestration flows
- multi-step recovery behavior

### browser-use style tools
browser-use style approaches may be referenced conceptually, but they are not the primary orchestration mechanism.

---

## Chat session policy

### Rotation
Browser-UI ChatGPT sessions must not be used indefinitely.

Use:
- normal rotation target: **80 turns**
- when turn count approaches the rotation threshold, create a handoff summary
- open a new chat
- continue from summarized carried-forward state

### Handoff requirements
Each new chat must inherit:
- project summary
- active objective summary
- completed objective summary
- blocked items
- failure memory summary
- current budgets / limits
- current repo constraints
- next intended action

---

## Retry / repair policy

### Retry limit
- same-class retry limit: **2**

### Retry sequence
When failure occurs:
1. retry #1
2. retry #2
3. invoke failure analysis in browser-UI ChatGPT
4. choose one of:
   - replan
   - split
   - repair
   - restart
5. verify result
6. continue or escalate

### Why this order
Fixed rigid fallback order is less accurate than:
- retry twice
- then run explicit failure analysis
- then choose recovery class

---

## Recovery-first chaining policy

Failure signs are not immediate stop signals.

They are inputs to a recovery decision pipeline:

1. detect failure sign
2. classify failure
3. check recoverability
4. attempt bounded recovery
5. verify
6. renew continuation if justified
7. escalate only if needed

---

## Success-proof continuation policy

### Continuation threshold
Use browser-UI ChatGPT scoring with:

- **continuation threshold: 90**

### Suggested score bands
- 90-100: continue
- 75-89: repair / verify / limited retry
- 50-74: restart / replan / split
- 0-49: escalate / stop

### Important rule
Scoring is not used alone.

Use:
1. minimum hard gates
2. then ChatGPT scoring/judgment

---

## Hard-gate policy

The system should automate as much as possible.

However, keep a minimal hard-gate layer for:
- explicit manual-only states
- forbidden/destructive policy states
- missing critical truth
- missing auth/secrets for required operation
- explicit unsafe external boundary posture

Everything else should be pushed as far as possible toward automated ChatGPT judgment.

---

## External operation policy

### Definition
External operations are actions that modify state outside plain local code editing.

Examples:
- PR merge
- branch cleanup / deletion
- issue / PR comments
- review requests
- CI reruns
- release operations
- approval notifications
- browser-UI ChatGPT interaction steps
- external API operations

### Policy
External operations should be automated whenever possible.

Only minimum hard gates should block them.

If hard gates pass, browser-UI ChatGPT may judge whether the external operation should proceed.

---

## High-risk action policy

### Policy
High-risk actions should be automated as far as possible.

Use:
- minimal hard-gate rejection layer
- then browser-UI ChatGPT final judgment

### High-risk examples
- merge
- branch deletion
- restart after repeated failures
- external execution
- actions affecting multiple objectives
- actions following repeated suppression signals

---

## ChatGPT scoring policy

Browser-UI ChatGPT should evaluate:
- current state summary
- latest diff summary
- changed files summary
- quality posture
- lifecycle posture
- failure memory summary
- objective status
- external boundary posture
- escalation posture

The model returns:
- success score
- confidence score
- decision
- reason
- main risks
- continue / retry / repair / restart / escalate recommendation

---

## Structured output policy

All browser-UI ChatGPT operational calls must return fixed JSON.

### Base schema
```json
{
  "status": "ok",
  "task_type": "planner|review|repair|scoring|prompt_generator|test_spec",
  "objective_id": "string",
  "step_id": "string",
  "success_score": 0,
  "confidence_score": 0,
  "decision": "continue|retry|replan|split|repair|restart|escalate|stop",
  "decision_reason": "short string",
  "risk_level": "low|medium|high|critical",
  "risks": [],
  "proofs": [],
  "required_actions": [],
  "blocked_by": [],
  "suggested_next_prompt": "string",
  "summary": "short summary",
  "token_list": []
}
```

### Task-specific extensions

#### planner
- roadmap_items
- slice_plan
- priorities

#### repair
- failure_class
- repair_strategy
- retry_allowed

#### scoring
- continuation_recommended
- proof_loss
- recovery_candidate

#### prompt_generator
- prompt_body
- preferred_files
- out_of_scope

#### test_spec
- test_targets
- edge_cases
- scenario_list

---

## Playwright selector strategy

### Meaning
Playwright selector implementation details are the strategy for reliably locating:
- chat input box
- send button
- new chat button
- model selector
- assistant response body
- conversation-ready state
- error / loading / retry states

### Selector design rule
Never rely on one selector only.

Use:
1. primary selector
2. secondary selector
3. fallback selector

### Recommended priority
1. stable `data-testid` / `aria-label`
2. role + visible text
3. DOM-structure fallback
4. page-text nearest-candidate fallback

### Required UI targets
- chat input element
- send trigger
- latest assistant response container
- new chat trigger
- message-ready detection
- loading detection
- retryable UI failure detection
- logout/login interruption detection

---

## UI failure handling

Browser-UI instability is acceptable if bounded recovery exists.

### Recovery order
1. same-chat retry
2. resend same prompt
3. page reload
4. new chat + handoff summary
5. pause / escalate only if still unresolved

### Login interruptions
If login state is lost:
- detect it
- pause active step
- recover login state
- resume from preserved state if safe

---

## Input payload policy

Accuracy is preferred over aggressive token reduction.

### Default input style
Use:
- fixed summary-first schema
- diff summary
- state summary
- constraints summary
- failure memory summary
- only add larger full-context blocks when needed

### Default always-send items
- project brief summary
- active objective summary
- current constraints summary
- current state summary
- latest diff summary
- failure memory summary
- budget / escalation / boundary summary
- requested task type
- required JSON output schema

### Conditional items
Add only when needed:
- full roadmap
- full changed file bodies
- full failure history
- full test context

---

## Codex token policy

Codex usage should be minimized by:
- storing stable rules/spec text in repo-side `.md` files
- sending Codex only bounded task-specific prompts
- avoiding large strategic descriptions in Codex prompts
- keeping test generation outside Codex whenever possible

---

## Test generation policy

### Browser-UI ChatGPT
Use for:
- test spec
- edge cases
- risk-focused scenarios

### Local LLM / Python
Use for:
- test skeletons
- fixture expansion
- repetitive boilerplate
- simple permutations

### Codex
Use mainly for:
- implementation code
- only narrowly-scoped test edits when strictly necessary

---

## Current intended direction
This repository should evolve from:
- bounded implementation orchestration

toward:
- browser-UI ChatGPT guided planning
- browser-UI ChatGPT guided repair
- recover-first chaining
- success-proven rolling autonomy
- long-running but non-blind autonomous development

with:
- retry limit = 2
- continuation threshold = 90
- chat rotation = 80 turns
- fixed JSON structured output
- external/high-risk action automation by default, with only minimal hard gates

## PR114: Autonomous Safety Layer

- Adds execution_permission gating
- Adds manual_override / safe_stop classification
- Metadata-only (no execution)
- Blocks unsafe or insufficient states before execution bridge

Key fields:
- project_browser_autonomous_safety_switch_status
- execution_permission
- safe_stop_status
- manual_override_status

