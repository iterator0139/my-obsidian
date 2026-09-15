---
name: write-precise-process-description
description: Verify a written description of a mechanism, process, or relationship before trusting it. Use whenever Codex writes prose that describes concurrency, timing, phasing, or the relationship between two or more components/steps/plans — e.g. explaining a race()/select loop, a wait window, a "does A happen before B" relationship, whether two plans/phases are separate or the same thing, or invoking a named correctness mechanism (CAS, lock, idempotency key, transaction) to justify a claim. Also use when reviewing existing docs for the same failure.
---

# Write Precise Process Description

## The underlying pattern

Every failure below comes from the same root habit: when asked to justify a
claim about structure ("A happens before B", "X guarantees Y"), the cheapest
available signal gets used as if it were the verification — the way a
sentence happens to read, or the fact that a mechanism's name has already
appeared nearby — instead of re-deriving the real structure or the
mechanism's exact definition and checking the claim against it. Both signals
are correlated with correctness often enough to feel safe, which is exactly
what makes them dangerous: they are right most of the time, so nothing
forces a check on the times they are not.

## The failure this guards against


When describing a mechanism in prose, the default written form is sequential:
"X happens, then Y happens, after that Z." This template is easy to produce
because it mirrors the order in which the writer types the sentences or the
lines of code — not necessarily the order in which the described things
actually happen. The result reads fluently and passes a "does this sentence
make sense" check, which creates false confidence that it is also correct.

Concretely, this produces four recurring misdescriptions:

- A **concurrent listen** (`race()`, `select`, `asyncio.wait(FIRST_COMPLETED)`,
  two signals being watched at once) gets narrated as "do A, then wait for B" —
  implying A must finish before B is even considered, when actually both are
  being watched from the same instant.
- A **bounded window that a process still lives inside** gets compressed into
  "the process exits immediately" — dropping the fact that it keeps running
  until some other condition (e.g., sibling completion) is met.
- Two **co-equal parts of one design** get written as "baseline, then an
  optional increment" or "phase one, phase two" — implying an optional or
  staged relationship that does not exist; both parts are load-bearing and
  required together.
- A **termination condition** gets written as "if the race result is B" (a
  passive description of one branch outcome) instead of stating the actual
  positive rule that gates returning/exiting — forcing the reader to reverse
  the mechanism to find the real rule.

The common root cause: the writer's output order (how the sentence or the
code was typed) gets silently treated as evidence of the real temporal or
structural order of the thing being described. Fluency is not a proof of
correctness — a well-formed sentence can still describe the wrong mechanism.

## What to do instead

### 1. Classify the relationship before choosing connective words

Before writing a sentence that relates two or more things, decide which of
these it actually is — do not default to the first one just because it is
easiest to phrase:

- **Strict sequence** — A must fully complete before B can begin.
- **Concurrent / simultaneous** — A and B are both active/watched from the
  same starting point; whichever resolves first determines what happens next.
- **Co-equal parts of one whole** — A and B are both required components of
  the same design; neither is optional or deferred relative to the other.
  ("baseline + optional increment" and "phase 1 / phase 2" are almost always
  a misdescription of this case.)
- **Conditional trigger** — B happens if and only if condition C holds; state
  C as a positive rule ("B happens when C"), not as one arm of a described
  race ("if the race result is C-not-D").

Only strict sequence licenses connectives like "then", "after that", "next",
"first ... then", or numbered phases. If the actual relationship is one of
the other three, use "at the same time", "while X is still pending", "both
are required parts of", or "returns only when C holds" instead.

### 2. Verify with an imagined diagram, not with fluency

After writing the sentence, do not check it by re-reading for fluency — a
fluent sentence about the wrong mechanism still reads fine. Instead ask:

> If a reader saw only this sentence, with no access to the code or prior
> context, what timeline or structure diagram would they draw in their head?
> Does that diagram match the real mechanism exactly — same start points,
> same branch conditions, same "when does this return" answer, down to the
> detail of whether two things are watched at once or one after another?

Any mismatch, however small ("sounds sequential but is actually concurrent"),
means the sentence must be rewritten from the relationship type identified in
step 1 — not patched with a different connective word.

### 3. Say the termination/return condition as a positive rule

For any loop, wait, or listen construct, state explicitly and separately:
"this returns/exits only when \<condition\>" — as its own sentence, before
or after describing the branches. Do not leave it to be inferred from "one of
the two race outcomes."

### 4. Say what happens immediately, in place, on the other branch

If a listen/race construct resumes in place on one signal, say that as an
explicit rule too ("upon receiving \<signal\>, execution resumes immediately,
in place, without waiting for \<the other condition\>") — do not let it be
implied only by a code branch.

### 5. Before citing a named correctness mechanism, write out its exact guarantee — not just its name

"CAS", "lock", "idempotency key", "transaction", "at-most-once" are not
interchangeable safety stickers. Each has a narrow, specific formal
guarantee, and a mechanism proven once for one property does not
automatically cover every other property that happens to be discussed near
it — especially once it has been established earlier in the same document
and starts feeling like ambient authority.

Before writing "X guarantees Y" for any named mechanism:

1. State X's guarantee in your own words, independent of the current
   sentence: what are the inputs, what is compared, what does success vs
   failure mean. For CAS specifically: "multiple concurrent writers race to
   change the same existing record from state A to state B; at most one
   write succeeds." That is all it guarantees — nothing about durability,
   nothing about delivery, nothing about whether anyone ever reads the
   result.
2. State the property Y you actually need for this sentence, in equally
   concrete terms — e.g. "no reader ever misses an already-recorded answer"
   is a *liveness/no-loss* property, not a *mutual-exclusion* property.
3. Check whether Y is literally implied by X's guarantee as stated in step 1.
   If it is a different property — no-loss vs. exactly-once vs. ordering vs.
   durability are common pairs that get conflated — X does not cover it, and
   citing X is borrowing its name without its substance. Find or state the
   mechanism that actually provides Y.

This check applies even when there is only one writer. A single first-time
insert into a not-yet-existing record is not a compare-and-swap at all — CAS
requires an existing value to compare against and a genuine race between
writers. Don't dress up an ordinary insert as "CAS in place" just because the
field will later participate in a real CAS.

## Worked example: sequencing (from a real correction)

Wrong: "The paused coroutine does not return immediately; instead, after
persisting the wait record and emitting the event, it awaits one more race
inside the existing concurrency window: whichever happens first, an answer
notification or all sibling units finishing."

Why it's wrong: "after ... it awaits" frames persistence-then-emit (real
sequence) and the race (concurrent listen) with the same connective, so the
reader draws "persist, THEN start listening" instead of "listening starts as
part of the same window, watching two signals at once."

Right: "After persisting the wait record and emitting the event, the
coroutine enters a listening state and watches two signals at the same time:
whether the answer mailbox has been notified, and whether the superstep has
no other units still running. It returns — and only returns — when the
second signal holds with no prior notification. If the first signal fires at
any point while still listening, it resumes execution in place immediately,
without waiting for the second."

## Worked example: mechanism-guarantee mismatch (from a real correction)

Wrong (two instances in the same document): (a) "The unit pauses → the wait
fact is immediately persisted (CAS in place, `state="open"`)" — describing a
first-time insert into a record that didn't exist yet as if it were a CAS.
(b) "If the answer arrives at the exact instant the window closes, CAS's
mutual exclusion guarantees it won't be missed" — using CAS (a
mutual-exclusion/at-most-once guarantee) to justify a no-loss/liveness
property it says nothing about.

Why it's wrong: (a) has exactly one writer creating a new record — there is
no existing value to compare against and no second writer to race against,
so "CAS" borrows a safety-sounding name for an operation with no race at all.
(b) conflates two independent axes: CAS's real guarantee is "at most one of
several concurrent writers changing the *same existing* record from
`"open"` to `"answered"` succeeds" (mutual exclusion / at-most-once-applied).
Whether an already-recorded answer is ever *read and consumed* (no-loss /
liveness) is a completely different property, provided (if at all) by
something else — e.g. a settlement pass that re-reads persisted state, or an
explicit re-check the listening coroutine does before it exits.

Right: (a) "The unit pauses → the wait fact is persisted for the first time
(`state="open"`). This is a single writer creating a new record; there is no
concurrent write here, so no compare-and-swap is involved — it just
establishes the value a later, real compare-and-swap will compare against."
(b) "If the notification is lost when the process crashes between the CAS
success and the mailbox delivery, that's fine *not because of CAS* but
because the answer is already durably persisted as `state="answered"` — the
settlement pass (or the listening coroutine's own pre-exit check) will read
and apply it independent of whether the notification ever arrived. CAS's own
job here is narrower: it only guarantees that if the same answer is
submitted twice, at most one submission actually triggers a resume."

## When reviewing someone else's (or your own past) description

Apply the same imagined-diagram check as a review step, not just before
writing. Docs that describe HITL waits, retry/timeout logic, cutover plans,
or multi-phase rollouts are the highest-risk targets — re-derive the
relationship type from the actual code or design, then check every
connective word against it. When a named correctness mechanism is cited,
also re-derive its exact guarantee independently and check it against the
property actually being claimed, per item 5 above — this failure mode is
common in the same kind of doc but is not caught by the diagram check alone,
since the sentence can be temporally accurate while still misattributing
which mechanism provides which property.
