# Validation-plan templates

## Requirement or capability plan

```markdown
# <Capability> validation plan

> Level: requirement/capability
> Status: planned | ready for verification | accepted at requirement level | blocked
> Authoritative sources: <links>

## Scope and non-goals

## Behavioral acceptance contract

| ID | Preconditions / trigger | Required observable behavior | Invariants and fault semantics | Owner(s) |
| --- | --- | --- | --- | --- |

## Evidence allocation

| Contract ID | Work-item evidence | Integration or E2E evidence | What this evidence does not prove | Status |
| --- | --- | --- | --- | --- |

## Cross-boundary scenarios

## Acceptance decision

State the observed evidence, environment, remaining risk, and the bounded conclusion.
```

## Work-item or module plan

```markdown
# <Work item> behavioral verification plan

> Level: work item/module
> Status: planned | ready for verification | verified at work-item level | blocked
> Source capability/requirement: <links and IDs>
> Responsibility boundary: <one paragraph>

## Local behavioral contract

| ID | Preconditions / trigger | Required observable behavior | Invariants and fault semantics | Explicit non-goals |
| --- | --- | --- | --- | --- |

## Integration contract

| Direction | Assumption or guarantee | Consumer / provider | Evidence |
| --- | --- | --- | --- |

## Verification strategy

| Contract ID | Proposed evidence | Controlled conditions | Pass condition | Limit of proof |
| --- | --- | --- | --- | --- |

## Evidence record and gaps

Record commands, test environment, result, and unproven claims. Do not treat planned tests as evidence.

## Handoff decision

State whether the work item is safe for its named dependents. List requirement-level scenarios still requiring integration verification.
```
