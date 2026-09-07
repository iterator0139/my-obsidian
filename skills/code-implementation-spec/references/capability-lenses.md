# Capability lenses

Select every lens materially affected by the change. A lens is a set of questions, not a mandatory document section.

## Domain model and rules

Use for new or changed concepts, invariants, validation, calculation, or policy.

- Define source data, derived data, validation boundaries, and invalid cases.
- State which rules are pure functions and which require I/O.
- Give examples and boundary cases that determine the algorithm.

Evidence: model/validation tests and rule tables.

## Lifecycle and state

Use when a persistent or runtime entity has meaningful transitions.

- Define all states, legal transitions, terminal-state protection, and the authorized writer.
- State persistence timing, timestamps, and what a rejected transition returns.
- Distinguish persistent facts from process-local coordination state.

Evidence: transition matrix and transition-race tests when applicable.

## Workflow and orchestration

Use when more than one step, module, branch, retry, or join creates behavior.

- Define trigger, inputs, completion/terminal outputs, hand-offs, and branch/join conditions.
- Give normal and important alternate sequences at call/effect granularity.
- State which layer orchestrates and which layers only execute a capability.

Evidence: sequence tests and end-to-end or integration scenarios.

## Concurrency and asynchronous resources

Use for multiple tasks, callbacks, streams, locks, cancellation, shared mutable state, or meaningful awaits.

- Identify shared facts, critical sections, lock scope, and every commit/race boundary.
- Define duplicate/reentrant behavior and resource ownership, registration, and cleanup.
- State whether a late result can commit after cancellation, timeout, or supersession.

Evidence: deterministic interleaving tests using barriers, fakes, or controlled events.

## Persistence and evolution

Use for data stores, snapshots, schema/model changes, or backward compatibility.

- Define read/write shape, source of truth, compatibility behavior, and migration/backfill policy.
- Specify write atomicity assumptions, rollback/compensation, and data retention where relevant.

Evidence: serialization, compatibility, and migration tests.

## External protocol and adaptation

Use for HTTP/RPC, framework boundaries, SDKs, queues, files, or remote workers.

- Map local contract to remote request/response/event shapes, authentication, timeout, and error normalization.
- Keep credentials out of persisted business facts.
- State the semantic meaning of remote acceptance, remote completion, unknown outcome, and transport failure.

Evidence: contract tests with protocol-shaped fakes; integration tests where required.

## Distributed reliability

Use for cross-process coordination, delivery, idempotency, leases, retries, or recovery.

- Define ownership/routing, idempotency keys, duplicate handling, ordering assumptions, and visibility guarantees.
- Enumerate effect-order crash windows. For each, state recovery behavior or explicitly declare it out of scope.

Evidence: duplicate-delivery and fault-injection scenarios.

## Public API and event contract

Use when callers, clients, or event consumers observe changed behavior.

- Define request/event schema, success and rejection outcomes, error mapping, compatibility, and ordering guarantees.
- Separate internal state from externally projected facts.

Evidence: contract tests and consumer-facing examples.

## Security, operations, and performance

Select each only when its constraints change or create material risk.

- Security: trust boundary, authorization, sensitive-data lifetime, audit needs.
- Operations: logs, metrics, correlation IDs, alerts, diagnosis of partial failure.
- Performance: hot path, complexity, limits, backpressure, concurrency and capacity assumptions.

Evidence: focused security, observability, or load checks proportionate to risk.
