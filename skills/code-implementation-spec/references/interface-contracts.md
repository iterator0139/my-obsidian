# Interface collaboration contracts

Use this reference whenever a design introduces or changes a public method, result object, result field, exception, event, callback, or configuration value that affects another module.

## Design in this order

1. Name the capability. State the problem it solves, the state/effects it owns, when it is invoked, when it is complete, and what it does not do.
2. Name the operation that realizes the capability. Do not start with an enum, result object, or method signature.
3. Name the collaboration decision. State the question the operation answers for another component.
4. Name the producer and consumer. Do not describe a value without identifying who must react to it.
5. Specify the required action for every meaningful value, including rejection and no-op values.
6. Specify call order, ownership, and whether the consumer may retry, wait, emit an event, or terminate.
7. Only then define enum members, dataclass fields, signatures, or schemas.

## Capability description

Write one short paragraph per non-trivial capability before tables or declarations:

```text
Capability: [what the module enables]
Problem: [why a caller needs it]
Effect: [state changes, resource actions, or durable fact it completes]
Invocation: [when and by whom]
Boundary: [what remains the caller's or another module's responsibility]
```

## Required table

| Interface element | Producer | Consumer | Question answered | Required consumer action |
| --- | --- | --- | --- | --- |
| `StartDecision` | lifecycle controller | task runner | May the Flow start? | Start only on `STARTED`; otherwise do not allocate execution resources. |
| `cleanup_errors` | cancellation coordinator | finalizer | Is local cleanup confirmed? | Log/escalate and retain an intermediate state when non-empty. |

Use one row per meaningful result, event, or field; group only values that have identical consumers and actions.

## Minimal caller protocol

For a non-trivial interface, add pseudocode that demonstrates the correct order and decision handling:

```python
result = await producer.begin_operation()
if result.decision is Decision.ACCEPTED:
    if result.errors:
        record_errors(result.errors)
        return
    await producer.finish_operation()
```

The example is illustrative, not a required API pattern. The purpose is to expose missing ownership, impossible call order, and values no consumer actually uses.

## Review questions

- Could a reviewer explain every public field without reading its implementation?
- Could a reviewer explain what every public method accomplishes before seeing its signature?
- Is every enum member or error outcome consumed by a named caller?
- Would two callers make the same next-step decision from the documentation?
- Is the transition from one method to the next explicit, especially across async boundaries?
- Can an unused field or result type be removed because no consumer action needs it?
