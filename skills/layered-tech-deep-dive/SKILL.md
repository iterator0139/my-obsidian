---
name: layered-tech-deep-dive
description: >-
  Deeply learn one selected layer of a technical framework after macro understanding.
  Use when the user asks to 深入某一层, 下钻, 核心算法机制, 系统设计, 代码实现,
  架构师视角, or wants to move from framework-level understanding into a specific
  subsystem/layer. Works as a downstream companion to learn-tech-framework.
tags: [skill, agent, framework-learning, deep-dive]
vault: my-obsidian
source_of_truth: skills/layered-tech-deep-dive
---

# Layered Tech Deep Dive

> Canonical location: Obsidian vault `skills/layered-tech-deep-dive/`.  
> Sync to agents: `bash skills/sync-to-agents.sh`

## Goal

Help the user deeply understand **one selected layer** of a framework, after macro understanding is already established.

This skill answers:

- What problem does this layer solve inside the larger system?
- What is the layer's core idea / main mechanism in one or two sentences?
- Which mechanisms are primary vs supporting?
- What are its core abstractions?
- What is the main runtime/data flow?
- What are the key algorithms/mechanisms?
- What system design choices, invariants, costs, and failure modes shape it?
- Where is the implementation in code?
- How does this layer connect back to the whole framework?

## Relationship With `learn-tech-framework`

Use `learn-tech-framework` first when the user needs macro understanding of a framework.

Use this skill after one of these happens:

- the macro doc has identified a layer worth drilling into
- the user says they mainly care about one subsystem/layer
- the user asks for 核心算法机制 / 系统设计 / 代码实现 of a layer
- the user says API/product overview is not important and wants mechanisms

Pipeline:

```text
learn-tech-framework
  -> macro judgment
  -> main abstractions
  -> layer map
  -> candidate deep-dive layers

layered-tech-deep-dive
  -> selected layer
  -> layer abstractions
  -> layer flow
  -> algorithms
  -> system design
  -> code implementation
  -> invariants / failure modes / costs
  -> back to whole-system meaning
```

## Required Input

Before writing, establish these fields from the user's request and available context:

```text
Framework:
Selected layer:
Whole-system judgment:
Layer position in the system:
User focus: algorithms / system design / code implementation / all
Output target: chat / project-local doc / Obsidian doc
```

If any field is missing, infer conservatively from prior context. Ask only when the missing decision changes the output substantially.

## Workflow

```text
- [ ] Phase 1: Anchor — restate whole-system judgment and selected layer
- [ ] Phase 2: Core idea — state the layer's main idea before mechanisms
- [ ] Phase 3: Mechanism priority map — distinguish primary, secondary, and supporting mechanisms
- [ ] Phase 4: Layer problem — explain what system pressure this layer handles
- [ ] Phase 5: Layer abstractions — identify core objects and boundaries
- [ ] Phase 6: Layer main flow and runtime channel map — trace data/state through the layer and where it becomes effective
- [ ] Phase 7: Mechanism interrogation — identify triggers, decision criteria, visible outputs, and invariants
- [ ] Phase 8: Algorithm mechanisms — decision logic, ranking, compaction, scheduling, caching, etc.
- [ ] Phase 9: System design — invariants, constraints, tradeoffs, trust boundaries
- [ ] Phase 10: Code implementation — concrete files/functions/data structures
- [ ] Phase 11: Failure and cost model — degradation, fallbacks, performance, operational cost
- [ ] Phase 12: Evolution — legacy/new paths, deprecated fields, likely direction
- [ ] Phase 13: Synthesis — how this layer serves the whole framework
- [ ] Phase 14: Write doc
```

### Phase 1: Anchor

Start by connecting this layer back to the whole system.

Template:

```text
In {framework}, the whole-system idea is {judgment}.
The selected layer is {layer}. It matters because {why it carries system complexity}.
```

Do not restart a full framework overview.

### Phase 2: Core Idea

Before any file list, pseudocode, or implementation detail, state the layer's main idea.

Template:

```text
The core idea of this layer is: ...
It solves ... by ...
The key mechanism is ...
```

This section must answer:

- What is the real problem?
- What mechanism solves it?
- Why is this the right abstraction?
- What would break without this layer?

Do not describe all mechanisms equally. Make a judgment.

### Phase 3: Mechanism Priority Map

Rank mechanisms by importance before explaining them.

Use three levels:

```text
Primary mechanisms:
  - mechanisms that define the layer's purpose

Secondary mechanisms:
  - mechanisms that make the primary path usable or scalable

Supporting mechanisms:
  - governance, compatibility, fallback, optimization, or ergonomics
```

For each mechanism, include:

```text
Mechanism:
Priority: primary / secondary / supporting
Why it matters:
Main idea:
Key source files:
```

If everything appears equally important, stop and re-evaluate. A good deep dive has a center of gravity.

### Phase 4: Layer Problem

Explain the pressure this layer exists to handle:

- context budget
- state consistency
- concurrency
- retrieval quality
- latency/cost
- safety/trust
- compatibility/provider differences
- product vs repo boundary

### Phase 5: Layer Abstractions

List only the abstractions that carry the layer's design.

For each abstraction:

```text
Name:
Represents:
Owns:
Does not own:
Adjacent abstractions:
Key files:
```

Avoid directory tours. Every abstraction must explain a boundary.

### Phase 6: Layer Main Flow

Write the main flow before algorithms.

Good flow shape:

```text
input/event
  -> state object
  -> transformation
  -> persistence/cache/index
  -> runtime-visible output
  -> feedback/writeback
```

Also produce a runtime channel map before explaining individual modules:

```text
source / information type
  -> channel
  -> transformed representation
  -> runtime-visible or runtime-effective position
  -> protection / eviction / invalidation
  -> failure mode
```

This is mandatory when a layer manages context, state, IO, requests, caches, events, tools, plugins, files, memory, or permissions.

Do not assume a named module is the only path. The same information type may enter through multiple channels, and each channel may have different durability, visibility, and protection rules.

For agent systems, explicitly identify:

- model-visible context
- hidden runtime state
- persisted state
- retrieved state
- generated/derived state

For each important information type, answer:

```text
Information type:
Named module(s):
Actual runtime channel(s):
Where it is attached or consumed:
How long it remains effective:
What protects it:
What can silently drop, stale, summarize, evict, or hide it:
```

### Phase 7: Mechanism Interrogation

Before writing algorithm details, interrogate each important mechanism with these questions. Do not skip this phase.

Use the general mechanism lens:

```text
problem pressure
  -> core idea
  -> trigger
  -> decision criteria
  -> state transition
  -> visible result
  -> invariant
  -> cost/failure mode
  -> code evidence
```

```text
Trigger:
  When does this mechanism run?
  Does it happen every request/turn, only on state changes, only on threshold crossing, or only on explicit user/tool action?

Decision criteria:
  What does it use to choose?
  Examples: token budget, message boundary, timestamp, ranking score, open/closed state, tags, provider capability, approval state.

First-principles target:
  If you designed this mechanism from the problem itself, what should the ideal decision rule optimize?
  Does the implementation optimize that target directly, or only a cheaper proxy?

Visible output:
  What becomes model-visible after this mechanism runs?
  What remains persisted but hidden?
  What is request-scoped vs persisted?
  If the same information can become visible through multiple channels, list all channels and their different guarantees.

State transition:
  What state is read?
  What state is written?
  Does it update a pointer/list/index/cache/message buffer?

Invariant:
  What bad state does this prevent?
  Examples: context overflow, stale prompt, broken tool-call structure, orphan tool result, hidden file content leak, unbounded memory growth.

Source evidence:
  Which function proves the trigger?
  Which function proves the decision criteria?
  Which function proves the visible output?

Critical evaluation:
  What problem does this design actually solve well?
  What important problem does it not solve?
  What tradeoff or approximation does it make?
  Where can it fail even when the code behaves as intended?
```

If the answer only describes code steps but not trigger/criteria/visible output/invariant, the mechanism is not understood yet.

Common decision criteria to look for:

- Budget: tokens, memory, time, concurrency, quota, context window
- Boundary: message boundary, transaction boundary, file boundary, permission boundary, API/protocol boundary
- Ranking: score, distance, timestamp, priority, rank, recency
- State: open/closed, dirty/clean, pending/done, active/inactive, cached/uncached
- Threshold: buffer size, timeout, retry count, trigger threshold, batch size
- Capability: provider support, backend support, model capability, feature flags
- Strategy: LRU, fallback, hybrid ranking, checkpointing, batching, deduplication

Always distinguish the real design target from the proxy implemented in code. A mechanism may optimize a measurable proxy such as length, recency, count, timestamp, score, or threshold while only indirectly serving the deeper goal such as relevance, correctness, freshness, safety, latency, or cost control.

Common visible-output distinctions:

- persisted but not runtime-visible
- runtime-visible but not persisted
- request-scoped injection
- model-visible prompt/context
- user-visible response
- derived index/cache
- pointer/list update such as message IDs, cursor, offset, checkpoint pointer

Pay special attention to mechanisms that sound obvious:

- A name may hide a different core mechanism than it suggests.
- A mechanism may solve resource control without solving semantic quality.
- A mechanism may preserve local correctness while creating global blind spots.
- A mechanism may be a cheap approximation of a more expensive ideal design.
- A mechanism may only work because another layer supplies missing guarantees.
- A named module may describe only one projection; trace all channels through which the same information becomes runtime-visible or effective.

### Phase 8: Algorithm Mechanisms

For each algorithm, use this template:

```markdown
### [Algorithm Name]

Problem:
Main idea:
Priority: primary / secondary / supporting
Trigger:
Decision criteria:
Input:
Output:
Visible output:
State written:
Mechanism summary:
Key implementation path:
Invariant protected:
Failure mode:
Key files/functions:
```

Examples of algorithm mechanisms:

- context compaction cutoff selection
- semantic search ranking
- cache eviction / LRU
- prompt compilation
- tree/path rendering
- checkpoint/undo history
- routing/fallback
- batching/chunking
- concurrency control

Avoid overusing pseudocode. Use pseudocode only when it clarifies a decision rule. Prefer explaining:

```text
problem -> main idea -> trigger -> decision criteria -> visible output -> code evidence -> invariant/tradeoff
```

Do not use pseudocode as the first explanation. First state the mechanism's main idea and why the decision rule exists.

### Phase 9: System Design

Answer:

- Why is the layer separated this way?
- What invariants must always hold?
- What crosses the layer boundary?
- What is intentionally not solved here?
- What would break if this layer were removed?

Required subsections:

```markdown
## Invariants
## Boundaries
## Tradeoffs
```

### Phase 10: Code Implementation

Tie mechanism to code.

For each important implementation path:

```text
File:
Function/class:
Role:
Important data fields:
What to read first:
What to ignore initially:
```

Prefer concrete code paths over broad package lists.

### Phase 11: Failure and Cost Model

Always include:

- normal failure modes
- fallback behavior
- degradation path
- performance cost
- storage/network/token cost
- cognitive/maintenance cost

### Phase 12: Evolution

Look for:

- deprecated fields
- V1/V2/V3 parallel paths
- TODO comments
- compatibility shims
- product vs repo drift
- legacy names or migrated concepts

Explain which parts are stable design and which parts are transitional.

### Phase 13: Synthesis

End by returning to the whole-system idea:

```text
This layer matters because...
It lets the framework...
Its main cost is...
The next layer to study should be...
```

## Output Targets

Project-local default:

```text
local/{framework-slug}-{layer-slug}-deep-dive.md
```

Obsidian default:

```text
frameworks/{framework-slug}/{layer-slug}-deep-dive.md
```

When the user asks for algorithms specifically:

```text
local/{framework-slug}-{layer-slug}-algorithms.md
```

## Quality Checklist

- [ ] Starts from the selected layer, not a full framework intro
- [ ] States the layer's core idea / main mechanism before details
- [ ] Ranks mechanisms into primary, secondary, and supporting
- [ ] States what problem the layer solves
- [ ] Identifies layer abstractions and boundaries
- [ ] Describes the main flow before algorithms
- [ ] Includes a runtime channel map showing source -> channel -> runtime-visible/effective position -> protection/failure mode
- [ ] Checks whether the same information/state type enters through multiple channels with different guarantees
- [ ] For each primary mechanism, identifies trigger, decision criteria, visible output, state writes, and invariant
- [ ] For each primary mechanism, separates the first-principles design target from the concrete proxy implemented in code
- [ ] Provides critical evaluation: what the design solves well, what it does not solve, and where it can fail even when implemented correctly
- [ ] Includes algorithm mechanisms with inputs/outputs/decision rules
- [ ] Does not flatten all mechanisms into an equal-weight list
- [ ] Avoids excessive pseudocode when a concept explanation is better
- [ ] Explains mechanisms with a transferable problem -> idea -> criteria -> state -> invariant shape, not a one-off incident recap
- [ ] Includes system design invariants and tradeoffs
- [ ] Maps mechanisms to concrete files/functions
- [ ] Includes failure modes and cost model
- [ ] Separates stable design from legacy/transitional code
- [ ] Ends by connecting the layer back to the whole system

## Anti-patterns

- Repeating the macro framework overview
- Directory tour without interpretation
- Jumping into code before abstractions and flow
- Flattening all mechanisms as equally important
- Explaining by module names only, without tracing where information/state actually becomes visible or effective
- Treating one named module as the whole story when the same information can enter through tool results, cache, messages, prompt, event bus, storage, or request-scoped injection
- Starting with pseudocode before explaining the main idea
- Explaining function steps without trigger/decision criteria/visible output
- Saying something is "rebuilt", "summarized", "searched", or "opened" without proving when and by what criteria
- Writing a post-hoc bug/incident reflection instead of a reusable method for understanding the mechanism
- Treating the implemented design as automatically optimal instead of evaluating it against the underlying problem
- Calling every function an algorithm
- Listing implementation details without invariants
- Explaining algorithms without failure modes
- Treating API endpoints as the core unless the selected layer is API/protocol

## Minimal Chat Output

When answering in chat only, use this compact shape:

```markdown
## Layer Judgment
...

## Core Idea
...

## Mechanism Priority Map
...

## Core Abstractions
...

## Main Flow
...

## Algorithms
...

## System Design
...

## Code Map
...

## Costs / Failure Modes
...
```

