# Bad Example: Add loose-file fallback outside ledger source of truth

## Pattern
Allow inspect or decision logic to derive authoritative state from files not recorded in ledger.

## Why this is bad
- source of truth becomes ambiguous
- debugging becomes harder
- old/new state divergence risk increases
- deterministic review plane weakens

## Red flags
- “if ledger path missing, search nearby files”
- “best effort payload discovery”
- multiple authority paths for machine_review

## Corrective action
- keep ledger-recorded paths authoritative
- allow only conservative null/default behavior when data is missing
- never promote fallback discovery into authority