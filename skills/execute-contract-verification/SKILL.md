---
name: execute-contract-verification
description: Execute and report evidence for an approved behavior-first validation plan. Use when Codex needs to verify a completed work item, module, integration, or capability against its stated contract; add missing tests within scope; run checks; inspect concurrency or ownership mechanisms; and record a bounded verified, failed, or blocked conclusion without overstating proof.
---

# Execute Contract Verification

Verify the contract, not merely the implementation's happy path.

## Require inputs

Read the approved task or capability contract and its validation plan before testing. Identify every claim, its promised evidence, its scope, and what a passing result cannot prove.

## Collect evidence

Inspect code for ownership, state/effect ordering, and concurrency claims that tests cannot fully observe. Add focused tests only when required evidence is absent and the change stays within the approved task boundary. Run the defined checks in the project environment and preserve exact commands and results.

For each claim, record one of: verified, failed, insufficient evidence, or blocked. A passing test proves only its observed condition; do not infer an end-to-end conclusion from work-item tests.

## Conclude at the correct level

Mark a work item `verified at work-item level` only when all local commitments have sufficient evidence. Mark a capability accepted only after its integration and end-to-end commitments have evidence. On failure, report the violated contract and counterexample; do not weaken the contract or broaden the implementation without approval.

## Update evidence

Update the validation artifact with the result, environment, residual boundaries, and rerun commands. Do not alter semantic or architecture contracts merely to match current code.
