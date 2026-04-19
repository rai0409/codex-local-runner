# Merge Readiness Checklist

## Preconditions
- [ ] Task goal is satisfied
- [ ] Review score supports merge
- [ ] No unresolved critical blocker remains

## Repository alignment
- [ ] Change matches current repository maturity
- [ ] Change strengthens deterministic review-control plane
- [ ] Change does not prematurely move toward autonomy

## Semantic safety
- [ ] No source-of-truth ambiguity
- [ ] No hidden execution semantics
- [ ] No runtime / visibility boundary collapse
- [ ] No silent operator-gate change

## Compatibility safety
- [ ] Backward compatibility preserved where required
- [ ] Old payload behavior remains conservative
- [ ] Missing fields handled safely

## Diff safety
- [ ] Changed files are expected
- [ ] Diff remains narrow
- [ ] No unrelated cleanup mixed into merge

## Validation safety
- [ ] Compile commands passed
- [ ] Unit tests passed
- [ ] Relevant compatibility tests passed
- [ ] Validation commands are recorded

## Documentation / traceability
- [ ] Implementation map recorded
- [ ] Commands run recorded
- [ ] Test results recorded
- [ ] PR body accurately reflects actual change

## Final merge gate
Merge only when all boxes above are satisfied.
If any semantic safety box is unchecked, do not merge.
If reset is safer than patching, do not merge.