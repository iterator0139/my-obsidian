---
name: plan-behavioral-validation
description: Create or review behavior-first validation plans for a complete requirement, capability, milestone, module, or independently developed work item. Use when Codex needs to define what must be proven before implementation proceeds or a change is accepted; distinguish requirement-level acceptance from task-level verification; derive stable behavioral contracts before selecting tests; map local evidence to end-to-end evidence; or turn an implementation/design document into an actionable validation plan.
---

# Plan Behavioral Validation

Plan validation around observable behavioral contracts, not the current implementation or a preferred test framework. Treat tests, fakes, integration environments, and manual review as replaceable evidence for those contracts.

## Choose the validation level

Classify the requested artifact before writing it. Ask only if scope cannot be inferred safely.

| Level | Validate | Passing conclusion | Must not claim |
| --- | --- | --- | --- |
| Requirement / capability | User- or system-visible outcome across all participating components | The requested capability meets its acceptance contract in its intended boundary | That every implementation choice is correct or every internal component is exhaustively tested |
| Work item / module | A bounded responsibility allocated from a requirement | This unit can safely be integrated under its stated assumptions | That the overall requirement is delivered or usable end-to-end |

When a request contains both levels, write the requirement-level plan first, allocate each behavior to one or more work items, then write the selected work-item plan. Always retain a requirement-level integration row for behavior that only emerges when work items combine.

## Build the behavioral contract

Read the authoritative requirement, architecture decision, implementation specification, and baseline behavior in that order of authority. Do not infer a target behavior from existing code when current documentation specifies a deliberate change.

For every behavior, state only facts that can be externally or boundary-observably judged:

- responsibility and non-goals;
- trigger or precondition;
- required result, state transition, or externally visible effect;
- ordering and concurrency invariant, where applicable;
- fault and cancellation semantics;
- ownership and integration boundary.

Avoid making private mechanisms the contract. Prefer “no resource starts after cancellation is accepted” over “the registry boolean is false.” Name a mechanism only when it is an intentional public or integration contract.

Make each claim atomic and falsifiable. Split a sentence containing “and” when either half could fail independently.

## Select evidence after the contract

For each behavioral claim, select the cheapest evidence that can falsify it. A claim may need more than one evidence type.

| Behavior type | Prefer evidence such as |
| --- | --- |
| Pure mapping, validation, or state transition | Unit or property test |
| Concurrent ordering or race | Deterministic scheduler, barrier/event-controlled test, or model check |
| Component boundary | Contract test with a fake or test double that records the boundary interaction |
| Persistence, transport, framework behavior | Integration test against the actual adapter/framework version |
| User-visible multi-component outcome | End-to-end or acceptance scenario |
| Failure handling | Fault injection proving the stated postcondition |

Do not mistake a passing test for evidence of a broader claim than it observes. State the observed fact, test environment, and remaining unproven boundary.

## Produce the plan

Use the applicable template from [references/templates.md](references/templates.md). Keep two layers distinct:

1. **Behavioral acceptance** — stable statements of what must be true.
2. **Verification evidence** — current tests, environments, commands, results, and known gaps; these may change without changing the behavior.

For a work item, include source requirement IDs or links, inbound assumptions, outbound contract, and residual system behavior that it does not prove. For a requirement, include an evidence allocation matrix plus integration scenarios that cannot be proven by any isolated work item.

Use statuses precisely:

- **planned**: contract or evidence is not yet agreed;
- **ready for verification**: implementation is in scope and required evidence is defined;
- **verified at work-item level**: local contract has sufficient evidence;
- **accepted at requirement level**: end-to-end and integration claims have sufficient evidence;
- **blocked**: an authoritative contract, environment, or external dependency prevents evidence collection.

Never mark a requirement accepted merely because every work item is locally verified.

## Review checklist

Before finalizing, confirm:

- Every acceptance claim is behavioral, atomic, and falsifiable.
- Non-goals prevent accidental scope expansion.
- Every claim has an owner and at least one proposed evidence path.
- Work-item assumptions and handoff contracts are explicit.
- Requirement-level integration behavior remains present after task decomposition.
- Evidence records what it proves and what it does not prove.
- Passing criteria use the correct level of conclusion.
