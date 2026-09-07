---
name: define-development-task-contract
description: Define a bounded, independently implementable delivery contract for a development task derived from approved responsibility architecture. Use when Codex needs to prepare T01/T02-style work items, allocate a safe responsibility slice, state local guarantees and invariants, define hand-offs and non-goals, and prevent a task from silently redefining system architecture.
---

# Define Development Task Contract

Create the contract that a task must satisfy before code-level design. A task is a delivery slice, not necessarily a stable module or directory.

## Require inputs

Read the approved capability contract, responsibility architecture, relevant preceding task contracts, and baseline/current code. Stop if the task depends on an unassigned fact, decision, or policy.

## Define the delivery slice

State:

- parent commitments and architecture decisions this task realizes;
- exact responsibility and observable local guarantee added by the task;
- system and architecture invariants the task must preserve;
- local invariants only for facts/effects this task can enforce;
- input assumptions, outgoing hand-offs, and required downstream action;
- explicit non-goals reserved for later tasks;
- local completion criterion and parent-owned integration boundary.

For every local invariant, give its owner, enforcement checkpoint, violation consequence, and proof target. Do not elevate an implementation choice into an invariant.

## Check task independence

Reject or split a task when it has two unrelated completion boundaries, needs undeclared changes in another task, writes a fact owned elsewhere, or can pass only by implementing a stated non-goal. Permit vertical slices spanning files when they have one coherent responsibility and one local acceptance conclusion.

## Gate the next phase

Hand the approved task contract to `code-implementation-spec`. Do not list classes, signatures, algorithms, or test fixtures except where a public compatibility boundary already constrains them.
