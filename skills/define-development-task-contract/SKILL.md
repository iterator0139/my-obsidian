---
name: define-development-task-contract
description: Split a requirement spec, with or without a technical architecture design, into ordered
  development tasks. Use when Codex needs to turn an approved requirement, design document, or change
  proposal into T01/T02-style work items that state what each task delivers, what it must not break,
  and the order and dependencies for implementation.
---

# Development Task Breakdown

Turn a requirement spec, and the architecture design when one exists, into an ordered list of development
tasks. Each task is a delivery slice the developer can finish on its own: one responsibility, a clear
input, and one conclusion that shows it is done.

The task list says **what** each task delivers. **How** to build it belongs to the code-level design, so
leave module boundaries, data structures, call sequences, algorithms, and test fixtures to
`code-implementation-spec` unless a shared compatibility boundary already fixes them.

## Read the source material

Read the requirement spec first, then the architecture design if the user has one, then the current code
and tests for the parts that will change. If a spec and a design disagree, say which one you followed.

Work from whichever document you have. With only a requirement spec, split by behavior and capability.
With an architecture design, split along the boundaries it already drew, and keep its decisions instead
of inventing your own.

## Find the slices

Walk the source material from trigger to final outcome and mark the places where a piece of behavior can
be built, run, and checked on its own. Typical cuts:

- one capability or state transition, with the data it reads and writes;
- one interface between two systems or modules, including the contract both sides code against;
- one integration point, such as a route, consumer, or adapter that connects a finished piece to the rest;
- groundwork that other tasks cannot start without, kept as small as it can be.

Split by responsibility rather than by file or layer. A task may touch several files when they serve one
responsibility, and two tasks may touch the same file when they own different behavior.

## Describe each task

For every task, state:

- its id and name, in the T01/T02 style;
- **What it delivers**: the behavior this task adds or fixes, in one or two sentences, plus the
  requirement section or design decision it implements.
- **Done when**: the observable result that shows the task works. This is also the parent-level
  acceptance point, so a reviewer can check it without reading the implementation.
- **Must not break**: any behavior, interface, or data contract this task could damage while it works.
- **Depends on**: the tasks that must land first, and the input each one hands over.
- **Leaves to others**: decisions this task does not make, and the task that owns each one.

Keep those five fields short. Long-form reasoning belongs in the design document or in the task's own
implementation spec, not in the breakdown. Add **Files touched** when the user asks for it, or when two
tasks in the same area would otherwise collide.

## Order the tasks

Default to the order that lets each task run: groundwork, then the capabilities they enable, then the
wiring, then the end-to-end path.

Check the order before you hand it over:

- every task lists the tasks it depends on, and the dependency points one way;
- no task needs a change in another task that nobody declared;
- each task can be finished and checked while the tasks after it are still unbuilt;
- no task exists only to serve a later task, unless the later task is named with it;
- a task that two tasks both need comes first, and the shared piece is named.

Two tasks may build in parallel when their dependencies are already done and neither writes what the
other owns. Say so in the list.

When one dependency can be read two ways and the order changes the design, ask the user instead of
guessing. For a small change with an obvious order, the list is enough; do not invent phases.

## Write the output

Give the sequence first, then the task detail:

1. A one-paragraph summary of the change and how it splits.
2. A task list in dependency order: id, name, depends on, parallel with.
3. Per-task detail using the five fields above.
4. The unresolved decisions, each with the smallest choice or document needed from the user.

Then hand each task to `code-implementation-spec` for its code-level design.

## Why the fields stop at "what"

Agile practice splits a story's statement from its acceptance criteria so the team can re-plan the
implementation without rewriting the requirement (INVEST: independent, negotiable, valuable, estimable,
small, testable). Spec-driven toolchains draw the same line: GitHub spec-kit keeps the plan and research
documents separate from the task list, OpenSpec calls `tasks.md` an implementation checklist while
`design.md` holds the approach, and Anthropic's Claude Code guidance keeps implementation detail out of
the requirement description. A task that also dictates structure cannot be re-planned when the first
approach fails, and its reader cannot tell which half is the contract.
