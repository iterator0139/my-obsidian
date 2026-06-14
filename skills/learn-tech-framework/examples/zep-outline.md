# Worked Example: Learning Zep

This example shows how `learn-tech-framework` was applied to Zep. Full output: `local/zep-from-zero-to-one.md`.

## Phase 1 Recon findings

| Finding | Evidence |
|---------|----------|
| Product = Context Engineering platform | README |
| Repo = examples + integrations, not core server | README "work in progress" |
| Engine = Graphiti (OSS) | README, graphiti repo |
| CE deprecated | legacy/, blog post |
| SDK = zep-cloud (PyPI) | README, examples import zep_cloud |
| Core API = add_messages → get_user_context | examples/python/agent-memory-full-example |

## Macro answers (compressed)

**本质对象**：Agent 上下文/记忆控制面，不是 LLM 也不是 Agent 框架。

**最小特征**：Add context → Graph RAG → Retrieve & assemble。

**核心矛盾**：Agent 需要全面、时效、关系感知的上下文，但窗口和工程精力有限。

**产品 vs repo  gap**：核心服务在 Cloud；repo 是示例和工具。

## Mechanisms identified (7)

1. Episode → Graph extraction
2. Bi-temporal facts
3. Incremental graph construction
4. Hybrid retrieval + rerank
5. Context assembly (templates, user summary)
6. Ontology + custom instructions
7. User Graph + Document Graph

Each documented with 是什么 / 解决的问题 / 解决方式 / 引入成本.

## Boundaries clarified (user FAQ)

| Misconception | Correction |
|---------------|------------|
| 只有知识图谱 | 支持对话、JSON、文档 chunk；统一进图谱 |
| 无文件上下文 | 有，但需 chunk → episode，非文件系统 |
| 无经验/技能记忆 | 无 procedural memory 一等公民 |
| 无本地版 | CE 废弃；Graphiti 可自建引擎 |
| 引擎不开源 | Graphiti 开源；Zep 产品层闭源 |

## Learning path produced

1. agent-memory-full-example (Streamlit)
2. zep-graph-visualization
3. context-templates / user-summary-instructions
4. integrations/python/*
5. zep-eval-harness
6. Graphiti repo

## Obsidian export

Compact version: `frameworks/zep/from-zero-to-one-obsidian.md` in vault `my-obsidian` — 822→687 lines, empty lines 236→122.

Full docs in vault:

- [[frameworks/zep/from-zero-to-one]]
- [[frameworks/zep/from-zero-to-one-obsidian]]
