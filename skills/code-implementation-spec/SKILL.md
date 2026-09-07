---
name: code-implementation-spec
description: Turn approved semantic, architecture, product, or refactoring designs into code-level implementation specifications. Use when entering formal development, detailing how a design maps to code, defining interfaces, algorithms, sequences, exceptions, state ownership, integration contracts, or test evidence; use for whole workflows and independently implementable submodules.
---

# Code Implementation Spec

Turn semantic intent into an executable and reviewable design. Do not impose one fixed document template: first identify the implementation capabilities affected by the change, then assemble only the relevant design views.

## Workflow

1. Read the authoritative semantic design, project constraints, and relevant baseline/current implementation. State the source of truth and any unverified assumptions.
2. Express the requested behavior as observable semantic commitments: what must happen, what must not happen, and who can observe the result.
3. Identify the implementation unit and its correctness boundary:
   - A whole flow owns behavior from external trigger to external outcome.
   - A submodule owns a local guarantee defined by its incoming and outgoing contracts.
4. Select the applicable capability lenses. Read [capability-lenses.md](references/capability-lenses.md) for the questions and required evidence for each lens.
5. Find the decision points: fact owners, state/effect commit points, external side effects, and conflict arbiters. Do not leave ownership implicit.
6. Design public capabilities before API shape. For each capability, explain the problem it solves, the state/effects it owns, when it is invoked, its completion boundary, and what it deliberately does not do. A reader must understand why every operation exists before seeing its name or return type.
7. Map each capability to its interface collaboration. For every public method, result type, field, exception, event, or callback, name its producer, consumer, question answered, and required consumer action. Read [interface-contracts.md](references/interface-contracts.md) whenever a change adds or changes a public interface.
8. Only then define signatures, data types, and fields. Show a minimal caller protocol or pseudocode for non-trivial interfaces; do not present declarations as self-explanatory.
9. Design the normal path at function/await/effect granularity. Specify inputs, outputs, ordering, preconditions, postconditions, and caller responsibilities.
10. Design the non-normal paths relevant to the selected lenses: invalid input, expected business rejection, dependency failure, timeout, concurrency, cancellation, duplicate delivery, and process interruption.
11. Produce an implementation specification using the relevant blueprint in [output-blueprints.md](references/output-blueprints.md). Map each semantic commitment to a code mechanism and a verification artifact.
12. Before coding, identify unresolved decisions. Do not silently turn them into implementation assumptions. During coding, keep the work within the declared boundary; update the specification if implementation disproves an assumption.

## Required quality bar

An implementation specification must let another developer answer all applicable questions without inferring policy from code:

- Which module owns each fact and is authorized to change it?
- What capability does each public operation provide, what state/effect does it complete, and what is outside its boundary?
- What exact interface, result, exception, or event tells a caller what to do next?
- What collaboration question does every public field or return value answer, who consumes it, and what must that consumer do for each value?
- In what order are persistence and irreversible external effects performed, and why?
- What happens at every meaningful `await`, retry, duplicate, failure, timeout, or crash window?
- Which guarantees are local, which belong to dependencies, and which require integration verification?
- What test or observable evidence proves every semantic commitment?

Use precise state tables, sequence diagrams, pseudocode, type signatures, and test matrices where they remove ambiguity. Omit irrelevant views for simple changes; do not add state machines, distributed-failure analysis, or abstractions without a matching risk.

For any non-trivial public interface, explain capability, intent, and caller protocol before showing declarations. A type signature specifies shape; it does not specify why the operation exists, what it completes, who owns the next action, or the required call order.

## Scope rules

For a whole-flow specification, trace behavior from entry through cross-module effects to the externally visible terminal result. Allocate ownership and hand-offs to the participating modules.

For a submodule specification, state the parent design, input assumptions, local guarantees, explicit non-responsibilities, dependency contracts, and integration hand-offs. Prove only its local guarantees with fakes; list end-to-end guarantees as integration evidence owned by the parent flow.

Never duplicate a parent design merely to make a submodule document look complete. Never let a submodule silently redefine a parent-level policy.

## Deliverable discipline

Prefer one independently reviewable implementation unit. Name exact code locations, but do not precommit to abstractions that lack a stated responsibility or caller. Keep design decisions, code changes, and tests traceable to the same semantic commitments.
