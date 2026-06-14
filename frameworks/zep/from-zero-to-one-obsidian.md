---
tags: [framework, zep, agent-memory, context-engineering]
aliases: [从0到1认识Zep, Zep 紧凑版]
project: zep
canonical: my-obsidian/frameworks/zep/from-zero-to-one-obsidian.md
---

> [!note] Obsidian 紧凑版
> 由 `zep-from-zero-to-one.md` 生成：减少空行、移除 `---` 分隔线、标签改为四级标题。阅读内容与原版一致。

# 从 0 到 1 认识 Zep

> 本文档基于 Zep 官方 README、本仓库代码结构，以及 Context Engineering / Agent Memory 的工程视角整理而成。
> 目标：在动手写代码之前，建立对 Zep 的宏观认知框架。

## 目录
1. [Zep 是什么](#1-zep-是什么)
2. [为什么会出现](#2-为什么会出现)
3. [核心作用与能力边界](#3-核心作用与能力边界)
4. [核心概念与数据模型](#4-核心概念与数据模型)
5. [工作原理：三步闭环](#5-工作原理三步闭环)
6. [典型 Agent 接入模式](#6-典型-agent-接入模式)
7. [技术栈与生态](#7-技术栈与生态)
8. [本仓库结构导读](#8-本仓库结构导读)
9. [代价、风险与选型考量](#9-代价风险与选型考量)
10. [与其他方案的对比](#10-与其他方案的对比)
11. [在 Agent 架构中的位置](#11-在-agent-架构中的位置)
12. [从 0 到 1 学习路径](#12-从-0-到-1-学习路径)
13. [核心机制特性：问题、方式与成本](#13-核心机制特性问题方式与成本)
14. [关键链接](#14-关键链接)

## 1. Zep 是什么
### 1.1 一句话定义
**Zep 是一个端到端的 Context Engineering（上下文工程）平台**，专门解决 AI Agent 在生产环境中「该记住什么、该检索什么、该组装成什么上下文」的问题。

### 1.2 本质对象
Zep 的本质对象 **不是 LLM，也不是 Agent 框架**，而是 **Agent 的上下文/记忆控制面**——介于业务数据与 LLM 之间的中间层。

```
业务数据（对话、文档、JSON、事件）
        ↓
    [ Zep 平台 ]
        ↓
  装配好的 Context Block
        ↓
   LLM / Agent 框架
```

### 1.3 最小不可再分的核心特征
Zep 的工作可以压缩为三个动作：

| 步骤 | 动作 | 含义 |
|------|------|------|
| 1 | **Add context** | 把对话、业务数据、文档、事件流持续写入 |
| 2 | **Graph RAG** | 自动抽取实体与关系，维护带时间属性的知识图谱 |
| 3 | **Retrieve & assemble** | 在亚 200ms 内返回预格式化、关系感知的 context block |

底层图谱引擎是开源项目 **[Graphiti](https://github.com/getzep/graphiti)**。Zep 在其之上提供托管服务、SDK 和工程化能力。

### 1.4 和相近事物的区别
| 方案 | 核心能力 | Zep 的差异 |
|------|----------|-----------|
| 向量 RAG | 语义相似度检索文档块 | 理解 **实体关系** 和 **事实如何随时间变化** |
| 对话历史 / 长上下文 | 把更多 token 塞进窗口 | **分层记忆 + 有预算的装配**，不是简单堆历史 |
| MemGPT 等 memory 框架 | 虚拟上下文 / 分层存储 | 更偏 **生产级托管服务 + 图谱化语义记忆** |
| LangChain Memory | 框架内嵌的记忆抽象 | Zep 是 **独立平台**，可跨框架复用 |

## 2. 为什么会出现
### 2.1 旧方式的问题
Agent 落地时，上下文管理是高频痛点：

- **窗口有限**：无法把所有历史、用户偏好、业务数据都塞进 prompt
- **检索粗糙**：纯向量检索只能找「相似文本」，不知道「谁和谁什么关系、事实何时失效」
- **工程负担重**：开发者自己拼 prompt、管 memory、做 chunk，成本高、难维护、难评测
- **生产要求严**：需要低延迟（<200ms）、可扩展、合规（SOC2 Type 2 / HIPAA）

### 2.2 核心矛盾
> Agent 需要 **全面、准确、时效、关系感知** 的上下文，
> 但 LLM 窗口和开发者精力都有限。

Zep 的定位：**把 context engineering 做成一个独立、可治理的平台层**，而不是让每个 Agent 项目自己造轮子。

### 2.3 行业背景
2025–2026 的 Agent 工程共识 increasingly 把 **memory、context engineering、evaluation** 视为生产级 Agent 的核心控制面，而非「prompt 写得好不好」这种表层问题。Zep 正是在这个方向上做的产品化尝试。

## 3. 核心作用与能力边界
### 3.1 核心作用
为 Agent 提供 **relationship-aware context assembly**（关系感知的上下文装配）。

### 3.2 次级作用
- **用户模型**：偏好、身份、历史交互
- **多数据源融合**：对话 + 结构化 JSON + 文档 + 应用事件
- **可定制 Ontology**：定义实体类型/schema，影响图谱抽取质量
- **Context Template**：控制 context block 的输出格式与字段

### 3.3 衍生能力
- **MCP Server**：让 Claude Desktop、Cline 等 MCP 客户端直接读 Zep 图谱
- **框架集成包**：AutoGen、CrewAI、LiveKit、ADK 等
- **Eval Harness**：端到端评测记忆检索与问答效果
- **Benchmark 论文**：LoCoMo、LongMemEval 等学术评测

### 3.4 适用场景
- 需要 **长期记忆** 的对话 Agent（客服、销售、个人助手）
- 需要融合 **对话 + 结构化业务数据 + 文档** 的场景
- 需要理解 **用户偏好变化、关系演化** 的个性化 Agent
- 对延迟敏感的生产环境

### 3.5 不适用 / 不解决
| 层 | 说明 |
|----|------|
| 规划层 | Zep 不做任务分解、DAG 规划 |
| 执行层 | Zep 不做工具调用、workflow runtime |
| 反思层 | Zep 不做 verifier、self-correction |
| 物理世界感知 | 需要你自己把线下事实数字化后写入 |
| 自托管核心引擎 | Community Edition 已废弃，核心在 Zep Cloud |

## 4. 核心概念与数据模型
### 4.1 概念层级
```
User（用户）
  ├── Thread（对话线程）
  │     └── Messages（消息）
  └── Graph（知识图谱）
        ├── Nodes（实体）
        ├── Edges（关系，带时间属性）
        └── Episodes（数据摄入事件）
```

### 4.2 关键概念说明
| 概念 | 含义 |
|------|------|
| **User** | 一个终端用户，拥有独立的记忆图谱 |
| **Thread** | 一次对话会话，消息按 thread 组织 |
| **Message** | 单条对话消息（user / assistant） |
| **Graph** | 从所有摄入数据自动构建的知识图谱 |
| **Node** | 图谱中的实体（User、Preference、Event、Location 等） |
| **Edge** | 实体之间的关系，带 `valid_at` / `invalid_at` 时间属性 |
| **Episode** | 一次数据摄入事件，可追溯「这条知识从哪来」 |
| **Ontology** | 实体类型定义，指导 LLM 如何分类和抽取 |
| **Context Block** | 检索后返回的、可直接塞进 prompt 的格式化文本 |

### 4.3 时间属性：Zep 的关键差异点
Graphiti / Zep 图谱中的每个 fact 都带有 **时间有效性**：

- `valid_at`：事实开始成立的时间
- `invalid_at`：事实失效的时间（若有）

这意味着 Agent 能区分：

- 「用户 **以前** 喜欢 A」
- 「用户 **现在** 改成了 B」

这是 temporal memory / graph memory 方向的核心价值，也是纯向量 RAG 难以做到的。

### 4.4 默认 Ontology 示例
本仓库 `ontology/default_ontology.py` 定义了默认实体类型，例如：

- `User` / `Assistant`：对话参与者
- `Preference`：用户偏好（高优先级抽取）
- `Event`：时间-bound 的活动
- `Location`：物理或虚拟地点
- `Organization` / `Document` / `Topic` 等

Ontology 的质量直接影响图谱抽取效果，是定制 Zep 时最重要的杠杆之一。

## 5. 工作原理：三步闭环
```
┌─────────────────────────────────────────────────────────┐
│                      Zep Cloud                          │
│                                                         │
│  ① Ingest          ② Graph RAG           ③ Retrieve   │
│  ─────────         ──────────            ──────────     │
│  对话消息      →   实体抽取          →   search_graph   │
│  JSON 数据         关系建模              get_user_context│
│  文档 chunk        时序标注              context template│
│  应用事件          异步构建图谱                          │
└─────────────────────────────────────────────────────────┘
         ↑                                        ↓
    你的应用写入                              Context Block
                                              塞进 LLM prompt
```

**要点**：

- 写入（Ingest）是 **异步** 的：消息提交后，图谱构建在后台进行
- 检索（Retrieve）是 **同步、低延迟** 的：面向 Agent 每轮对话的实时 context 需求
- 图谱构建逻辑对用户 **透明**：不需要自己管 embedding、chunk、图数据库

## 6. 典型 Agent 接入模式
几乎所有官方 example 都遵循同一个 **两步模式**：

```python
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message

zep = AsyncZep(api_key="...")

# Step 1: 写入 — 把用户消息加到 thread
await zep.thread.add_messages(
    thread_id=thread_id,
    messages=[Message(name="Alice", role="user", content="I prefer window seats")]
)

# Step 2: 读取 — 拿到装配好的 context block
result = await zep.thread.get_user_context(thread_id=thread_id, mode="basic")
context_block = result.context

# Step 3: 塞进 system prompt，调 LLM
system_prompt = f"You are a helpful assistant.\n\n{context_block}"
```

### 6.1 两种主要检索 API
| API | 用途 | 适合场景 |
|-----|------|----------|
| `thread.get_user_context()` | 高级封装，返回 ready-to-use context string | 大多数 Agent 场景，最简单 |
| `graph.search()` | 低级图搜索，可自定义 scope、filter、rerank | 需要精细控制检索逻辑 |

### 6.2 可选定制参数
- `mode="basic"` — 默认 context 模式
- `template_id="..."` — 使用预定义的 context template
- custom ontology — 传入自定义实体 schema
- custom instructions — 指导 LLM 如何抽取和总结

## 7. 技术栈与生态
### 7.1 产品形态
| 形态 | 状态 | 说明 |
|------|------|------|
| **Zep Cloud** | ✅ 当前主力 | 托管 SaaS，<200ms 延迟，SOC2/HIPAA |
| **Community Edition** | ❌ 已废弃 | 代码在 `legacy/`，不再维护 |
| **Graphiti** | ✅ 开源 | 时序知识图谱框架，Zep 的底层引擎 |

### 7.2 SDK
SDK 发布在包管理器，**不在本 repo**：

| 语言 | 安装 |
|------|------|
| Python | `pip install zep-cloud` |
| TypeScript/JS | `npm install @getzep/zep-cloud` |
| Go | `go get github.com/getzep/zep-go/v2` |

### 7.3 框架集成
`integrations/python/` 目录下的独立包：

| 包 | 框架 |
|----|------|
| `zep-autogen` | Microsoft AutoGen |
| `zep-crewai` | CrewAI |
| `zep-livekit` | LiveKit |
| `zep-adk` | Google ADK |

### 7.4 MCP Server
`mcp/zep-mcp-server/` — Go 实现的 MCP 服务，提供 13 个 **只读** 工具：

- `search_graph` — 图谱搜索
- `get_user_context` — 获取 context block
- `get_user_nodes` / `get_user_edges` — 图谱探索
- `get_episodes` — 数据摄入事件
- 等

适用于 Claude Desktop、Cline 等 MCP 客户端，让 AI 助手直接访问 Zep 记忆。

## 8. 本仓库结构导读
> **重要认知**：这个 repo 不是 Zep 核心引擎源码，而是 **示例、集成、工具** 的集合。

```
zep/
├── examples/               # 各语言/框架用法示例
│   ├── python/
│   │   ├── agent-memory-full-example/    ← 推荐第一个跑
│   │   ├── zep-quickstart-dashboard/
│   │   ├── context-templates-example/
│   │   ├── user-summary-instructions-example/
│   │   ├── chunking-example/
│   │   ├── openai-agents-sdk/
│   │   └── elevenlabs-zep-example/
│   ├── typescript/
│   │   ├── langgraph/
│   │   ├── zep-graph-visualization/      ← 看图谱长什么样
│   │   └── chunking-example/
│   └── go/
│       └── chunking-example/
│
├── integrations/           # Agent 框架集成包
│   └── python/
│       ├── zep_autogen/
│       ├── zep_crewai/
│       ├── zep_livekit/
│       └── zep_adk/
│
├── mcp/
│   └── zep-mcp-server/     # MCP 只读服务（Go）
│
├── ontology/
│   └── default_ontology.py ← 默认实体 schema
│
├── zep-eval-harness/       # 端到端评测框架
│   ├── zep_ingest_users.py
│   ├── zep_chunk_documents.py
│   ├── zep_ingest_documents.py
│   └── zep_evaluate.py
│
├── benchmarks/             # 学术 benchmark 代码
│   ├── locomo/
│   └── longmemeval/
│
└── legacy/                 # 已废弃的 Community Edition（Go）
```

## 9. 代价、风险与选型考量
### 9.1 成本维度
| 维度 | 内容 |
|------|------|
| **引入成本** | Zep Cloud 账号 + API Key；学习 User/Thread/Graph/Ontology 概念 |
| **落地成本** | 设计 ontology、custom instructions、context template；搭建 ingestion pipeline |
| **运行成本** | 按 Cloud 定价；异步图谱构建有 processing 延迟 |
| **演进成本** | CE 已废弃，长期依赖 Cloud；ontology 变更可能需要 re-ingest |

### 9.2 风险维度
| 风险 | 说明 |
|------|------|
| **依赖风险** | 强依赖 Zep Cloud，核心引擎不开源自托管 |
| **正确性风险** | 图谱抽取质量受 LLM + ontology 影响，需要 eval 验证 |
| **可控性风险** | 黑盒图谱构建，调试需借助 graph inspect 工具 |
| **扩展性风险** | 大规模 multi-tenant 场景需评估 Cloud 配额与成本 |
| **合规风险** | Cloud 提供 SOC2/HIPAA，但数据出境等问题需自行评估 |

### 9.3 选型建议
**选 Zep 如果**：
- 你需要 production-ready 的记忆层，不想自建图谱基础设施
- 你的 Agent 强依赖用户偏好、关系演化的长期记忆
- 你愿意接受 Cloud 依赖，换取低延迟和运维简化

**不选 Zep 如果**：
- 你必须完全自托管、数据不出境
- 你只需要简单的短期对话历史，不需要图谱
- 你的核心诉求是 Agent 规划/执行，而非记忆

## 10. 与其他方案的对比
| 维度 | 向量 RAG | 长上下文 | MemGPT | Zep |
|------|----------|----------|--------|-----|
| 关系理解 | ❌ | ❌ | 部分 | ✅ 图谱 |
| 时间演化 | ❌ | ❌ | 部分 | ✅ valid_at/invalid_at |
| 生产延迟 | 中 | 高（token 成本） | 自管 | ✅ <200ms |
| 接入复杂度 | 低 | 最低 | 中 | 低（SDK 3 行） |
| 自托管 | ✅ | N/A | ✅ | ❌（Cloud only） |
| 跨框架 | ✅ | ✅ | 部分 | ✅ |

## 11. 在 Agent 架构中的位置
结合 Agent 分层架构，Zep 明确落在 **「上下文/记忆控制面」**：

```
┌──────────────────────────────────────────────────────┐
│  感知层：用户 query、外部事件、多模态输入              │
├──────────────────────────────────────────────────────┤
│  ★ 上下文与记忆层 ← Zep 在这里 ★                      │
│    · episodic memory（对话事件）                      │
│    · semantic memory（稳定事实，带时间演化）           │
│    · context assembly（任务态上下文装配）              │
├──────────────────────────────────────────────────────┤
│  意图与规划层：intent completion、plan generation     │
├──────────────────────────────────────────────────────┤
│  执行与调度层：tool routing、workflow runtime          │
├──────────────────────────────────────────────────────┤
│  验证与反思层：verifier ensemble                      │
├──────────────────────────────────────────────────────┤
│  学习与演化层：skill library、trajectory mining       │
└──────────────────────────────────────────────────────┘
         ↑ 横切：权限 / 成本 / 安全 / 评测 控制面
```

Zep **解决**：记忆存储、关系建模、上下文检索与装配
Zep **不解决**：规划、工具调用、结果验证、技能沉淀

## 12. 从 0 到 1 学习路径
### Phase 0：建立认知（本文档）
- 理解 Zep 是什么、解决什么问题、边界在哪
- 知道本 repo 是 examples/integrations，核心在 Cloud

### Phase 1：跑通最小闭环
**目标**：亲眼看到「有 Zep / 无 Zep」的回答差异

```bash
cd examples/python/agent-memory-full-example
pip install -r requirements.txt
# 配置 .env: ZEP_API_KEY, OPENAI_API_KEY
streamlit run ui.py
```

可选：先跑 `pre-populate-memories/populate-memories.py` 预填充测试数据。

### Phase 2：理解图谱
**目标**：看到消息如何变成节点和边

```bash
cd examples/typescript/zep-graph-visualization
# 按 README 启动，可视化 User Graph
```

同时阅读 `ontology/default_ontology.py`，理解实体类型设计。

### Phase 3：定制能力
按优先级：

1. `context-templates-example` — 控制 context block 格式
2. `user-summary-instructions-example` — 定制用户摘要逻辑
3. `chunking-example` — 文档分块与 ingestion

### Phase 4：框架集成
根据你使用的 Agent 框架，阅读对应集成包：

```
integrations/python/zep_autogen/
integrations/python/zep_crewai/
...
```

### Phase 5：评测与治理
```bash
cd zep-eval-harness
uv sync
# 按 README 跑完整 pipeline：ingest → chunk → evaluate
```

理解如何量化 memory 检索质量，建立 baseline。

### Phase 6：深入 Graphiti
阅读 [Graphiti 仓库](https://github.com/getzep/graphiti)，理解底层时序知识图谱的设计原理。

## 13. 核心机制特性：问题、方式与成本
> 本章深入 Zep 的 **7 个核心机制**：每个机制解决什么问题、通过什么方式解决、引入什么成本。

Zep 的本质不是「又一个向量库」，而是把 **动态数据 → 时序图谱 → 有预算的上下文装配** 做成一条生产级 pipeline。

### 13.1 机制一：统一摄入 → Episode → 图谱抽取
#### 是什么
所有数据（对话、JSON、文档 chunk、文本）都先变成 **Episode**（原始摄入事件），再由 LLM 异步抽取 **Entity（节点）** 和 **Fact（边/关系）**。

```
对话 / JSON / 文档 chunk
        ↓
   Episode（溯源层，保留原文）
        ↓  LLM 抽取（异步）
   Entity + Fact（结构化层）
```

#### 解决的问题
- 多源数据分散：对话在 chat history、业务在 DB、文档在 RAG，Agent 看不到全貌
- 非结构化数据难以被 Agent 稳定消费

#### 解决方式
- 统一入口：`thread.add_messages()` / `graph.add(type=text|json|message)`
- 异构数据进同一套图谱，检索时一次装配

#### 引入成本
- 图谱构建是 **异步** 的：写入后不能立刻检索到完整抽取结果，需 poll / 等待
- 抽取依赖 LLM：ingestion 阶段有 token 成本与失败重试
- 抽取质量是黑盒：ontology / custom instructions 设计不好，图谱就歪

### 13.2 机制二：时序事实管理（Bi-temporal Facts）
#### 是什么
每条 Fact（关系边）带 **valid_at / invalid_at** 时间窗口。信息变化时，旧 fact **失效（invalidated）而非删除**，历史可追溯。

```
2024-01: "用户偏好窗口座位"  (valid: 2024-01 → 2024-06)
2024-07: "用户偏好过道座位"  (valid: 2024-07 → present)
```

#### 解决的问题
- 向量 RAG：旧信息和新信息 embedding 相似，容易召回过期事实
- 长上下文：堆历史无法表达「什么时候成立、何时失效」
- Agent 幻觉：把已改变的偏好/状态当成当前真相

#### 解决方式
- 检索默认偏向 **当前有效** 的 facts（invalid_at = present）
- Context block 显式标注时间范围，LLM 能区分「曾成立」vs「现已成立」

#### 引入成本
- 时间信息依赖抽取质量：对话里没明确时间，valid_at 可能不准
- 冲突消解逻辑在平台侧，调试需借助 graph inspect / dashboard
- 不能替代业务系统里的 authoritative state（Zep 是 memory，不是 source of truth）

### 13.3 机制三：增量图谱构建（Incremental Graph Construction）
#### 是什么
新 Episode 进来后立即增量更新图谱，**不需要**像 GraphRAG 那样定期 batch 重算整个社区摘要。

#### 解决的问题
- 传统 GraphRAG：batch 处理，数据一变就要重跑，延迟高
- 静态知识库：Agent 记忆跟不上实时交互和业务变更

#### 解决方式
- 流式摄入 + 增量 entity/relationship 更新
- 适合「用户聊着聊着偏好就变了」这类动态场景

#### 引入成本
- 增量更新带来 **最终一致性**：刚写入到可检索之间有延迟
- 长期运行图谱会膨胀，需关注 Cloud 配额与检索噪声
- 大规模 re-ingest（改 ontology）成本高

### 13.4 机制四：混合检索 + 重排序（Hybrid Retrieval）
#### 是什么
检索不走「query → embedding → top-k chunks」单一路径，而是多路并行：

| 检索通道 | 作用 |
|----------|------|
| 语义向量 | 语义相似 |
| BM25 关键词 | 精确词匹配 |
| 图遍历 | 沿关系扩展 |
| Cross-encoder rerank | 精排 top 结果 |

eval harness 中的典型调用：

```python
zep_client.graph.search(
    user_id=user_id,
    query=query,
    scope="edges",      # 或 nodes / episodes
    reranker="cross_encoder",
    limit=N,
)
```

还支持 `mmr_lambda`（多样性）、`center_node_uuid`（以某实体为中心）、`node_labels` / `edge_types` 过滤。

#### 解决的问题
- 纯向量：召回相似但无关的 chunk
- 纯关键词：语义泛化差
- GraphRAG 检索：query 时还要 LLM 摘要，延迟秒级

#### 解决方式
- 多 signal 融合 + rerank，query 阶段 **不依赖 LLM 生成**
- sub-200ms 的关键：检索路径预优化，而非现场 summarization

#### 引入成本
- 高级参数（scope、reranker、filter）需要理解图谱结构，不是真·三行代码
- `get_user_context()` 是高级封装，定制检索逻辑要用 `graph.search()`
- 召回质量仍依赖图谱抽取质量——garbage in, garbage out

### 13.5 机制五：多视图上下文装配（Context Assembly）
#### 是什么
不是返回一堆 raw chunks，而是按结构化模板装配 **Context Block**：

```
<USER_SUMMARY>        ← 用户高层摘要（User Summary Instructions 驱动）
<FACTS>               ← 关系型事实（带时间范围）
<ENTITIES>            ← 相关实体
<EPISODES>            ← 原始 episode 片段（可选）
[Document Graph]      ← 共享文档图谱的结果（可选）
```

#### 解决的问题
- Context engineering 难点不是 recall，而是 **装什么、顺序如何、粒度多细**
- 开发者手工拼 prompt 不可维护、不可复现
- Token 预算有限，不能把图谱全塞进去

#### 解决方式
- 平台侧预配置装配策略（Smart Context Assembly）
- Context Template 控制输出格式
- User Summary Instructions 保证关键字段（如预算、偏好）**始终出现**，不完全依赖语义检索

#### 引入成本
- 默认装配策略是平台 opinion，不完全透明
- 要最优效果需调：template、summary instructions、search scope/limit
- 装配结果需 eval harness 量化，否则只能凭感觉

### 13.6 机制六：Ontology + Custom Instructions（领域适配）
#### 是什么
- **Ontology**：Pydantic 定义实体/边类型（User、Preference、Event…），指导 LLM 如何分类抽取
- **Custom Instructions**：领域术语、业务约定（如「budget = 最高购房预算」）
- **User Summary Instructions**：定义用户摘要应始终回答哪些问题

#### 解决的问题
- 通用抽取在垂直领域分类混乱（「预算」被抽成 Topic 而非 Preference）
- Agent 每次交互都缺关键业务字段

#### 解决方式
- 注入领域先验，提高抽取精度
- User Summary 作为「始终在线的 semantic anchor」

#### 引入成本
- **落地成本最高的一环**：需要领域专家 + 迭代 eval
- Ontology 变更可能导致历史数据需 re-ingest
- 过度复杂的 ontology 反而增加抽取错误面

### 13.7 机制七：多图谱模型（User Graph + Document Graph）
#### 是什么
- **User Graph**：per-user，来自对话 + 个人业务数据
- **Document Graph**：共享参考文档（如产品手册、政策），独立 ingest

检索时可并行搜两个 graph，装配进同一 context block。

#### 解决的问题
- 用户个性化 vs 共享知识混在一起，检索噪声大
- 文档更新不应污染用户图谱

#### 解决方式
- 文档需自己 chunk + contextualize（仓库有 example，但不是自动的）
- 两套 graph 的 ontology/instructions 可能需分别配置

#### 引入成本
- 文档 ingestion pipeline 是你自己的工程（Zep 只负责 ingest 后的图谱化）
- 无 raw file 语义：文件必须 chunk → episode，不能像文件系统那样按路径读取

### 13.8 问题 → 机制 → 成本 总览
| 核心问题 | Zep 用什么机制解决 | 主要成本 |
|----------|-------------------|----------|
| Agent 上下文窗口不够 | Context Assembly，只装相关 facts/entities | 装配策略需调优；默认策略不完全透明 |
| 纯向量 RAG 召回相似但无关内容 | Hybrid retrieval + cross-encoder rerank | 需理解 scope/filter 参数 |
| 用户偏好/事实随时间变化 | Bi-temporal facts，失效而非删除 | 时间抽取不准；非 authoritative state |
| 多源数据孤岛 | 统一 Episode → Graph 管道 | 异步延迟；抽取质量依赖 ontology |
| GraphRAG 延迟高、需 batch | 增量图谱 + query 时无 LLM 摘要 | 图谱膨胀；长期运维依赖 Cloud |
| 手工拼 prompt 不可维护 | get_user_context + template | 定制需 eval；vendor 依赖 |
| 关键字段不能靠检索碰运气 | User Summary Instructions | 需领域设计 + 项目设置 |
| 文档 + 对话 + 业务数据融合 | 多类型 graph.add + 多 graph 检索 | 文档 pipeline 自建；无 raw file 语义 |
| 垂直领域抽取不准 | Ontology + Custom Instructions | **落地成本最高**；变更需 re-ingest |

### 13.9 Zep 不解决什么（产品边界）
| 问题 | 状态 |
|------|------|
| Procedural memory（技能库、成功路径模板） | ❌ 无专门机制，只能当 text/json 塞进去 |
| Raw 文件系统上下文 | ❌ 无，文件必须 chunk → episode |
| Agent 规划 / 工具调用 / 执行 | ❌ 不在 scope |
| 完全自托管 Zep 服务 | ❌ CE 已停，只剩 Graphiti 自建 |
| Source of truth / 强一致业务状态 | ❌ 是 memory layer，不是 DB 替代品 |

### 13.10 成本结构（按阶段）
```
引入成本
├── Zep Cloud 账号 + API Key
├── 理解 User/Thread/Graph/Episode/Ontology 概念
└── SDK 接入（简单，但用好不简单）

落地成本  ← 通常最大
├── Ontology 设计
├── Custom Instructions / User Summary Instructions
├── 文档 chunk + contextualization pipeline
└── Eval harness 建立 baseline

运行成本
├── Cloud 订阅费
├── Ingestion 阶段 LLM 调用（抽取，按量）
├── 异步 processing 等待时间
└── 图谱随用户/数据增长

演进成本
├── Ontology 变更 → 可能 re-ingest
├── 强依赖 Cloud，迁移到 Graphiti 自建工作量大
└── 需持续 eval，否则质量漂移不可见

机会成本
├── 自研 memory 栈 vs 买 Cloud 的权衡
└── 若需 procedural memory，还得在上层另建系统
```

### 13.11 本章小结
> **Zep 的核心机制**：把异构动态数据流式摄入为时序知识图谱，用混合检索在毫秒级找到「当前有效、关系相关」的事实，再按模板装配成 LLM-ready 的 context block。
>
> **核心价值**：解决 Agent 记忆层的 **时效性、关系性、多源融合、装配自动化** 四个问题。
>
> **核心代价**：Cloud 依赖、异步黑盒抽取、ontology 设计负担、以及 procedural/file 语义的缺失。

## 14. 关键链接
| 资源 | 链接 |
|------|------|
| Zep 官网 | https://www.getzep.com |
| 官方文档 | https://help.getzep.com |
| Zep Cloud 注册 | https://app.getzep.com |
| Graphiti（底层引擎） | https://github.com/getzep/graphiti |
| 本仓库 | https://github.com/getzep/zep |
| Discord 社区 | https://discord.gg/W8Kw6bsgXQ |
| SOTA Agent Memory 论文 | https://zep.link/sota-paper |
| 开源策略变更公告 | https://blog.getzep.com/announcing-a-new-direction-for-zeps-open-source-strategy/ |

## 附录：快速参考卡片
```
┌─────────────────────────────────────────────────┐
│  Zep 快速参考                                    │
├─────────────────────────────────────────────────┤
│  是什么    │ Agent 上下文工程平台（Cloud SaaS）  │
│  核心引擎  │ Graphiti（时序知识图谱，开源）       │
│  核心 API  │ add_messages → get_user_context     │
│  核心差异  │ 关系感知 + 时间感知 + <200ms         │
│  本 repo   │ examples + integrations + eval      │
│  不在 repo │ 核心服务端（在 Cloud）               │
│  SDK       │ zep-cloud / @getzep/zep-cloud       │
│  已废弃    │ Community Edition（legacy/）        │
└─────────────────────────────────────────────────┘
```

*Obsidian 紧凑版 | 2026-06-06 | 源文件：`zep-from-zero-to-one.md`*
