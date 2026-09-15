---
name: analyze-change-context
description: Frame a proposed software change before semantic or architecture design. Use when Codex needs to establish the real problem, authoritative sources, baseline behavior, affected boundary, compatibility constraints, and unresolved questions for a new feature, refactor, incident fix, or migration.
---

# Analyze Change Context

Create a factual starting point. Do not design a solution or infer target behavior from existing code.

## Gather authoritative context

Read current requirement and decision documents first, then project constraints, then the relevant baseline implementation and tests. Record the source hierarchy and distinguish confirmed facts from observations and assumptions.

## Produce a change frame

State:

- the problem and affected user/system outcome;
- current baseline behavior and its concrete limitations;
- scope and compatibility constraints;
- affected external and internal boundaries;
- unknowns that prevent a semantic or architecture decision.

Use observed evidence for baseline claims. Do not write APIs, module boundaries, algorithms, or test fixtures.
