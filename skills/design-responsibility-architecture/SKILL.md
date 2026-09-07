---
name: design-responsibility-architecture
description: Design a responsibility-oriented architecture from an approved capability contract. Use when Codex needs to assign durable facts, decision rights, irreversible effects, integration boundaries, and architecture invariants to clear owners before decomposing a capability into development tasks.
---

# Design Responsibility Architecture

Turn semantic commitments into explicit ownership. Do not start from existing folders, classes, or preferred patterns.

## Build the responsibility ledger

For each capability commitment, enumerate:

- durable and runtime facts that must be trusted;
- decisions that accept, reject, complete, or reinterpret those facts;
- irreversible effects and their required ordering;
- external boundaries and unknown outcomes;
- consumers that observe committed facts.

Assign each fact's business interpretation and write authority to one owner. A fact may have many readers but must not have competing writers.

## Define boundaries and hand-offs

For every proposed component, state its purpose, owned facts/effects, input assumptions, guarantees, non-responsibilities, and outgoing hand-offs. Every returned decision, event, or field must name a consumer and required consumer action.

Define architecture invariants only when they constrain multiple work items: unique decision ownership, single-write rules, effect ordering, isolation, and committed-fact projection.

## Review the allocation

Reject a design when a fact has no owner, two components can decide the same terminal result, a component promises an outcome outside its control, or a hand-off requires private mutable state. Keep implementation detail out; produce a responsibility matrix and resolved architecture decisions.

## Gate the next phase

Permit task decomposition only after every semantic commitment has an owner or an explicitly deferred boundary.
