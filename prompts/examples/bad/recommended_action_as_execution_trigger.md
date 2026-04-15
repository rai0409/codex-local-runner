# Bad Example: Treat recommended_action as execution trigger

## Pattern
Interpret recommended_action as permission to execute retry / rollback / merge.

## Why this is bad
- recommended_action is advisory/review-layer information
- execution still requires explicit operator decision or future bounded runtime contract
- this collapses read-only visibility into control behavior

## Red flags
- “retry” automatically schedules retry
- “rollback” directly calls executor from inspect layer
- advisory is used as authorization

## Corrective action
- keep recommended_action display-only
- separate inspect from operator decision
- require explicit local human decision for execution paths