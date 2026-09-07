---
name: define-capability-contract
description: Define the semantic contract for a user- or system-visible software capability. Use when Codex needs to turn a framed requirement into observable behavior, state rules, system-level safety invariants, failure semantics, non-goals, and acceptance boundaries before choosing an architecture or splitting development tasks.
---

# Define Capability Contract

Define what must be true for the capability, independent of code structure and implementation mechanism.

## Require inputs

Use an approved change frame. Read authoritative product, architecture, and compatibility constraints. Stop when a policy choice is unresolved; do not choose it from baseline code.

## Derive semantic commitments

Describe only observable behavior:

- triggers, preconditions, and outcomes;
- business states and legal transitions;
- system-level safety rules: what must never happen;
- failure, cancellation, and unknown-outcome semantics;
- non-goals and explicitly deferred behavior;
- user- or system-level acceptance boundary.

Keep implementation owners, classes, protocols, queues, locks, and test fixtures out of this contract.

## Exhaust the possibility space, not just the nominal path

Do not start from the happy path and append exceptions. Before writing commitments, identify the dimensions that define the full situation space and treat every cell as first-class:

- who may observe or act;
- what inputs may arrive and in what validity/duplication state;
- when they may arrive relative to each transition;
- what may fail, restart, repeat, reorder, or remain unknown.

A commitment is complete only when behavior is defined for valid, invalid, duplicate, stale, missing, delayed, concurrent, and post-failure cases. An omitted cell is unspecified behavior, not "not applicable".

## Separate concerns with different lifetimes and authorities

Do not derive one concept from another by proximity. At minimum keep these pairs distinct:

- durable fact vs transient authority;
- identity of an entity vs its current holder or location;
- observed or reported state vs authoritative state;
- policy choice vs derivable fact.

Examples of the failure pattern: "it can be found again" is mistaken for "it can be acted on without its current holder"; "it was reported" is mistaken for "it was committed".

## Model accepted-but-unconfirmed outcomes

Whenever a transition records intent before its effect is confirmed, explicitly state how retry, reordering, loss, or restart resolves that window: idempotent continuation, terminal convergence, or unrecoverable. Never assume retry is safe.

## Surface policy choices as open questions

When a commitment depends on a choice rather than a fact, list the choice before finalizing the contract. Do not silently adopt the current behavior and do not wait to be corrected.

## Test candidate invariants

For each candidate invariant, state the violation scenario and unacceptable consequence. Keep it only when it is stable across valid architectures and materially protects capability correctness. Classify liveness claims separately; do not present eventual completion as a safety invariant without its environmental assumptions.

## Gate the next phase

Require every semantic commitment to be atomic and falsifiable. Produce unresolved policy questions rather than hidden assumptions. Hand approved commitments to responsibility architecture design.
