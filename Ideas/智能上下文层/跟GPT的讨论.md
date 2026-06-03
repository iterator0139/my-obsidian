# Context OS / 上下文构建系统设计笔记（草案）

## 一、问题本质：Agent 的核心不是推理，而是上下文构建

传统 Agent 范式：

```
Task → Retrieval (RAG) → Reasoning → Action
```

但在复杂任务（尤其代码系统）中，这个链路存在根本问题：

> Retrieval 并不等于 Context，Context 不是“相关信息集合”，而是“任务视角下的知识投影”。

因此更本质的表达是：

```
Knowledge → Projection(Task) → Context → Reasoning
```

---

## 二、核心抽象：Context = Knowledge 的任务投影

### 1. 定义

```
Context = Projection(Knowledge, Task)
```

含义：

- Knowledge：全量知识空间（代码、文档、历史、系统结构）
- Task：当前目标
- Context：为完成 Task 从 Knowledge 中“筛选 + 组织 + 压缩 + 结构化”的结果

---

### 2. 为什么需要 Projection

因为：

- Knowledge 是全量且无结构（或弱结构）
- Context 是局部且结构化的工作集合

例子：

知识：

```
BidService, BudgetService, ExperimentService, RankingService...
```

不同任务对应不同 Context：

- 新增策略 → Bid + Experiment + Config
- 超投排查 → Budget + Billing + Delivery
- 推荐优化 → Ranking + Recall + Feature

---

## 三、核心问题拆解

Context OS 本质要解决四个问题：

### 1. Information Need Discovery（需要什么知识）

```
Task → What do I need to know?
```

输出：

```
{  "needs": ["bidding", "experiment", "config"]}
```

---

### 2. Knowledge Retrieval（去哪里找）

```
Need → Knowledge Graph / Code Index
```

方式：

- 代码图谱（Function/Class/Module）
- 文档索引
- PR / 历史记录
- Runtime metrics

---

### 3. Context Assembly（如何组织）

```
Retrieved Knowledge → Working Context
```

结构化输出：

- Architecture Summary
- Relevant Services
- Key Code Paths
- Historical Changes
- Constraints

---

### 4. Context Gap Detection（缺什么）

```
Current Context → Missing Information
```

输出：

```
{  "missing": ["traffic split logic", "budget allocation rules"]}
```

触发新一轮 retrieval。

---

## 四、系统架构设计（Context OS）

### 总体架构

```
                    Task                      │                      ▼            ┌──────────────────┐            │ Need Discovery   │            └──────────────────┘                      │                      ▼            ┌──────────────────┐            │ Projection Engine│            └──────────────────┘                      │                      ▼            ┌──────────────────┐            │ Working Context  │            └──────────────────┘                      │                      ▼            ┌──────────────────┐            │ Reasoning Agent  │            └──────────────────┘                      │                      ▼            ┌──────────────────┐            │ Gap Detector     │            └──────────────────┘                      │          missing info? │                      ▼            ┌──────────────────┐            │ Knowledge Graph  │            │ Code / Docs / PR │            └──────────────────┘                      ▲                      └──── loop ────┘
```

---

## 五、系统分层设计

### Layer 1：Knowledge Space（知识空间）

内容：

- Code
- Architecture
- PRD
- Design Docs
- PR History
- Metrics / Logs

特点：

- 全量
- 非结构化 or 弱结构化
- 不直接用于推理

---

### Layer 2：Knowledge Graph（结构层）

作用：

- 建立实体关系
- 支撑 traversal retrieval

例：

```
BidService → BudgetService → Metrics → Experiment
```

---

### Layer 3：Projection Engine（核心）

输入：

```
Task + Knowledge Graph
```

输出：

```
Task → Required Context Plan
```

分三步：

#### 3.1 Need Discovery

预测需要哪些知识领域

#### 3.2 Retrieval Planning

决定查哪些模块 / 文件 / 记录

#### 3.3 Context Construction

输出结构化 Context

---

### Layer 4：Working Memory（工作记忆）

作用：

- 存储当前任务上下文
- 累积中间发现
- 支持持续推理

结构：

```
{  "architecture": "...",  "services": ["BidService"],  "findings": [],  "unknowns": []}
```

---

### Layer 5：Gap Detector（缺口检测）

作用：

- 判断 Context 是否充分
- 主动发现信息缺失
- 触发新一轮 retrieval

本质：

> Context completeness estimator

---

## 六、关键思想总结

### 1. Agent 最大问题不是推理，而是 Context 错误

```
错误来源：- ❌ reasoning failure- ✅ context projection failure（更常见）
```

---

### 2. Context ≠ Knowledge

```
Knowledge = 全量事实Context = 任务视角切片
```

---

### 3. Projection 是核心能力

```
Task → Knowledge Selection → Context
```

这是当前 RAG / Agent 系统缺失的关键层。

---

### 4. Context OS 是“工作记忆系统”，不是知识库

它的目标不是存知识，而是：

> 持续构建“完成当前任务所需的最小充分信息集合”

---

## 七、代码场景切入的原因（工程策略）

选择代码系统原因：

- 结构天然存在（Graph）
- 任务明确（Issue / PR）
- 可评测（SWE-bench）
- Context 影响结果极大

---

## 八、工程落地路线（建议）

### Phase 1：验证 Context 是否有效

- OpenHands / Aider
- - Code Graph
- - baseline对比

指标：

- Pass@1
- 修复率
- token usage

---

### Phase 2：实现 Projection Engine V1

模块：

- Need Discovery
- Graph Retrieval
- Context Builder

---

### Phase 3：引入 Gap Detection

实现：

- Context completeness check
- iterative retrieval loop

---

### Phase 4：构建 Projection Dataset

记录：

```
Task → Context Plan → Success/Fail
```

用于未来训练：

```
P(Context | Task)
```

---

## 九、最终抽象（最核心一句话）

> Agent 的本质不是“会思考的模型”，而是“能够为任务构建正确工作记忆的系统”。

---

如果你后续要继续推进，这份笔记下一步可以扩展成两块：

1. **工程设计稿（模块拆解 + 接口定义）**
2. **实验设计（SWE-bench + baseline + ablation）**

我也可以帮你把下一步直接拆成“可实现的MVP架构图 + repo结构”。