---
name: learn-tech-framework
description: >-
  Learn a technical framework or platform from zero using a structured macro-to-mechanism
  workflow. Produces from-zero-to-one docs with problem/mechanism/cost analysis, repo
  orientation, learning paths, and optional Obsidian compact exports. Use when the user
  wants to understand a new framework, library, platform, or OSS project from scratch;
  asks for 从0到1认识 / 宏观了解 / 技术框架学习 / framework onboarding; or wants
  systematic tech evaluation before adoption.
tags: [skill, agent, framework-learning]
vault: my-obsidian
source_of_truth: skills/learn-tech-framework
---

# Learn Tech Framework (From Zero to One)

> Canonical location: Obsidian vault `skills/learn-tech-framework/`.  
> Sync to agents: `bash skills/sync-to-agents.sh`

## Goal

Help the user **understand a framework before coding**, not dump docs. Output should answer:

- What is it, really?
- What problem does it solve, and how?
- Where are the boundaries and costs?
- How does this repo/SDK map to the product?
- What is the learning path?

## When to Apply

Use this skill when the user:

- asks to learn / understand a framework, platform, SDK, or OSS project
- says 「从 0 到 1」「宏观了解」「帮我认识 X」
- wants adoption/evaluation research before building
- asks for a structured learning doc or knowledge base entry

Do **not** jump to implementation unless the user explicitly asks after macro understanding.

For **selected-layer deep dive** after macro understanding, use `layered-tech-deep-dive`.

## Workflow

```text
- [ ] Phase 1: Recon — gather primary sources
- [ ] Phase 2: Macro map — answer SOP questions
- [ ] Phase 3: Mechanism depth — problem → mechanism → cost
- [ ] Phase 4: Repo/SDK orientation
- [ ] Phase 5: Boundaries, comparison, risks
- [ ] Phase 6: Learning path
- [ ] Phase 7: Write doc(s) → frameworks/{slug}/
- [ ] Phase 8: Optional Obsidian compact export
- [ ] Phase 9: Deep-dive handoff — name candidate layers and call `layered-tech-deep-dive` when requested
```

### Phase 1: Recon (evidence first)

Read in parallel when possible:

1. Official README / docs landing page
2. Repo top-level structure
3. Package manifests (`pyproject.toml`, `package.json`, `go.mod`)
4. 1–2 canonical examples (quickstart / full-example)
5. Integrations, benchmarks, eval harness if present
6. Announcements about licensing, cloud vs self-hosted, deprecation

Record: **product vs repo gap**, **maintained vs legacy**, **primary API surface**.

### Phase 2: Macro map (SOP)

Answer using [[Ideas/怎么认识一个事物]] + [reference.md](reference.md) Sections 2–4 (评估/成本/风险维度).

Keep claims tied to evidence. Mark inference vs documented fact.

Before splitting by named modules, identify the framework's runtime channels:

```text
information / request / state source
  -> transport or storage channel
  -> transformation
  -> runtime-visible position
  -> protection / eviction / failure mode
```

This prevents module-name bias. The same kind of information may enter the runtime through multiple paths; conversely, a named module may only be one projection of a broader runtime flow.

### Phase 3: Mechanism depth

For each core mechanism (5–8), use micro-template in [reference.md](reference.md) Section 5.

Use code citations when repo evidence exists.

For every mechanism, ask both:

- What does this named module do?
- Through which runtime channel does its output actually become effective?

### Phase 4: Repo / SDK orientation

Mental map: repo vs packages, entry examples, integrations, eval tooling.

### Phase 5: Boundaries, comparison, risks

Include **「不解决什么」** table.

### Phase 6: Learning path

Phase 0–6 ordered by ROI; name concrete repo paths.

### Phase 6.5: Candidate deep-dive layers

Before writing the final doc, identify 3–7 layers/subsystems that are worth deeper study.

For each layer, record:

```text
Layer:
Why it matters:
Core question:
Primary abstractions:
Source entry points:
Best deep-dive angle: algorithms / system design / code implementation / all
```

Examples:

- memory layer
- agent loop
- tool execution layer
- provider adapter layer
- storage/indexing layer
- protocol/API layer
- scheduling/background jobs layer

If the user selects one layer, hand off to `layered-tech-deep-dive` instead of expanding the macro doc indefinitely.

### Phase 7: Write document(s)

**Default output (Obsidian vault):**

```text
frameworks/{framework-slug}/from-zero-to-one.md
frameworks/{framework-slug}/from-zero-to-one-obsidian.md  # optional compact
```

**Project-local fallback** (when learning inside a code repo):

```text
local/{framework-slug}-from-zero-to-one.md
```

Use [templates/from-zero-to-one.md](templates/from-zero-to-one.md). Chinese unless user requests English.

Update [[skills/Skills Index]] frameworks table when adding new output.

### Phase 8: Obsidian compact export

1. Remove `---` horizontal rules; use heading hierarchy
2. Convert standalone `**标签**` → `#### 标签`
3. Collapse consecutive blank lines to one
4. Remove trailing spaces
5. Add frontmatter: `tags`, `aliases`

Target: ~40–50% fewer empty lines.

### Phase 9: Deep-dive handoff

When the user asks to go deeper into one selected layer, use `layered-tech-deep-dive`.

Pass this context forward:

```text
Framework:
Selected layer:
Whole-system judgment:
Layer position in the system:
User focus:
Important source entry points:
Known unknowns / mechanism questions:
```

The deep-dive skill should then produce layer abstractions, layer flow, algorithm mechanisms, system design, code implementation, invariants, failure modes, costs, and evolution.

## Output Modes

| User request | Deliver |
|--------------|---------|
| 「先宏观了解」 | Chat summary + offer full doc |
| 「输出到文档」 | `frameworks/{slug}/from-zero-to-one.md` |
| 「深入机制」 | Expand mechanism chapter |
| 「深入某一层 / 核心算法 / 系统设计 / 代码实现」 | Use `layered-tech-deep-dive` |
| 「和 X 对比」 | Comparison table + selection guide |
| 「学习路径」 | Phase 0–6 with repo paths |
| Obsidian 版 | Compact export in same folder |

## Quality Checklist

- [ ] **本质对象** in one sentence
- [ ] **product vs repo** gap if any
- [ ] ≥3 mechanisms with problem/mechanism/cost
- [ ] Runtime channel map: source -> channel -> visible/effective position -> protection/failure mode
- [ ] 「不适用 / 不解决」 section
- [ ] Learning path with real example paths
- [ ] Candidate deep-dive layers with source entry points
- [ ] Costs: 引入/落地/运行/演进
- [ ] Facts vs inference separated

## Anti-patterns

- Directory tour without interpretation
- Copying marketing README unchecked
- Skipping boundaries
- Jumping to code before macro map
- Listing features instead of mechanisms
- Explaining named modules without tracing how information/state becomes runtime-visible or effective
- Expanding one layer endlessly inside the macro doc instead of handing off to `layered-tech-deep-dive`

## Additional Resources

- SOP + dimensions: [reference.md](reference.md)
- Template: [templates/from-zero-to-one.md](templates/from-zero-to-one.md)
- Example: [examples/zep-outline.md](examples/zep-outline.md)
- Deep dive companion: `skills/layered-tech-deep-dive/`
- Agent sync: [portability.md](portability.md)
- Index: [[skills/Skills Index]]
