# Output blueprints

Choose a blueprint based on the implementation unit. Add only the sections required by selected capability lenses.

## Whole-flow specification

1. Semantic commitments, scope, authority, and non-goals.
2. Entry, terminal observable outcomes, and compatibility constraints.
3. Participating modules, fact ownership, and hand-off contracts.
4. Normal-path sequence with state/effect ordering.
5. Alternate, failure, retry, timeout, and interruption paths selected by the lenses.
6. Interface collaboration: producer, consumer, decision/question, and required action for each non-trivial result/event/field; then signatures and data changes by code location.
7. Verification matrix: commitment → mechanism → unit/contract/integration evidence.

## Submodule specification

1. Parent design reference and module responsibility.
2. Input assumptions and required dependency contracts.
3. Local semantic guarantees and explicit non-responsibilities.
4. Public capabilities: for each non-trivial capability, state problem, effect, invocation, completion boundary, and non-responsibilities.
5. Interface collaboration contract: for each public method, result, field, exception, or event, state producer, consumer, question answered, and required next action.
6. Public facade: show the minimal caller protocol first, then signatures, return decisions, exceptions, and caller obligations.
7. Internal facts, algorithms, state/effect order, and concurrency/resource rules.
8. Output hand-offs and integration requirements for callers/downstream modules.
9. Exact code locations and local test matrix; separately list parent-owned integration evidence.

## Traceability matrix

Use one row per material semantic commitment.

| Semantic commitment | Code mechanism / owner | Failure or race rule | Evidence |
| --- | --- | --- | --- |
| Example: accepted cancellation cannot later become success | Controller transition gate | lifecycle lock rejects late success | deterministic race test |

## Decision record format

For a decision that materially changes behavior, record:

```text
Decision: [chosen behavior]
Context: [semantic commitment and constraints]
Mechanism: [owner, interface, ordering]
Alternatives rejected: [only meaningful alternatives]
Evidence: [tests or inspection points]
Open boundary: [explicitly deferred behavior, if any]
```
