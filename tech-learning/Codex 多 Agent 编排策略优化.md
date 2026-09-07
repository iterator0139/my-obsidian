---
title: Codex 多 Agent 编排策略优化
tags:
  - Codex
  - Agent
  - 多 Agent
  - 编排
  - 系统设计
source: /home/chenhong24/projects/codex
updated: 2026-08-11
---

# Codex 多 Agent 编排策略优化

> 本文基于 Codex 当前仓库代码与相关实现整理，重点说明 Codex 在多 Agent 场景下如何处理并发、上下文、资源、成本、隔离与恢复。

## 1. 总览

Codex 的多 Agent 编排并不是简单地“启动更多 Agent”，而是围绕以下问题构建了一套运行时机制：

- 什么时候应该并行执行任务；
- 并行度应该限制在什么范围；
- 子 Agent 需要继承多少上下文；
- 不活跃 Agent 是否继续驻留内存；
- Agent 之间如何通信、暂停和恢复；
- 如何控制 token 和执行成本；
- 如何避免工作目录、环境变量和凭据互相污染。

整体上，它更接近一个轻量级的 Agent 运行时和调度系统。

## 2. 共享并发容量

Codex 使用 session 级的共享执行容量控制，而不是让每个 Agent 独立创建无限并发任务。

### 主要行为

- 父 Agent、子 Agent 和嵌套子 Agent 共享执行容量；
- 启动新 Agent 前先检查当前可用容量；
- 达到上限时返回容量不足结果，而不是无限 spawn 或无限排队；
- 通过共享容量池避免嵌套编排造成并发爆炸。

这种设计可以保证单个 Agent 的局部决策不会突破整个 session 的资源边界。

相关实现：

- `codex-rs/core/src/agent/control.rs`
- `codex-rs/core/src/agent/control/execution.rs`

## 3. Agent 驻留管理与 LRU 驱逐

逻辑上的 Agent 数量可以很多，但所有 Agent 的运行时状态不可能一直驻留内存。因此 Codex 将 Agent 的逻辑生命周期与运行时驻留生命周期分离。

### 驻留策略

- 活跃 Agent 优先保留；
- 长时间不活跃的 Agent 可以被卸载；
- 容量不足时按 LRU 思路驱逐较少使用的 Agent；
- 主线程或受保护线程不会被随意驱逐；
- 驱逐前先保存 rollout 状态；
- 后续需要执行时再重新 materialize。

这使系统可以支持更多逻辑 Agent，同时把内存占用控制在可预测范围内。

相关实现：

- `codex-rs/core/src/agent/control/residency.rs`

## 4. Fork 时的上下文继承策略

子 Agent 不一定要复制父 Agent 的全部历史。`spawn_agent` 支持按任务选择上下文继承范围。

| 策略    | 适用场景         | 特点                |
| ----- | ------------ | ----------------- |
| 完整历史  | 子任务强依赖主任务背景  | 信息完整，但上下文成本较高     |
| 最近若干轮 | 只需要近期执行状态    | 在连续性与成本之间折中       |
| 不继承历史 | 独立搜索、测试或局部调查 | 上下文最干净，token 成本最低 |

这避免了“所有子 Agent 都携带完整会话历史”的粗粒度做法，降低了 token 消耗和上下文噪声。

相关实现：

- `codex-rs/core/src/tools/handlers/multi_agents_v2/`

## 5. 异步消息式编排

多 Agent 工具不仅支持创建 Agent，还支持后续的点对点通信和生命周期控制：

- `spawn_agent`：创建子 Agent；
- `send_message`：发送消息；
- `followup_task`：追加后续任务；
- `wait`：等待任务完成；
- `interrupt_agent`：中断 Agent；
- `list_agents`：查看 Agent 状态。

因此编排模型不局限于：

```text
spawn -> 阻塞等待 -> 收集结果
```

也可以采用：

```text
并行启动多个独立任务
主 Agent 继续处理自己的工作
子 Agent 完成后异步汇报
必要时追加 follow-up 或 interrupt
```

这种方式减少了主 Agent 被最慢子任务完全阻塞的情况，适合代码扫描、测试执行、资料收集和多模块调查等任务。

## 6. 环境与凭据隔离

多 Agent 共享部分工作区时，需要避免隐式继承过多权限和进程状态。Codex 对执行环境做了更细粒度的管理。

### 隔离维度

- 通过 `TurnEnvironmentSelection` 管理 cwd 和 workspace roots；
- 子 Agent 显式继承父 Agent 的环境选择；
- 对敏感环境变量进行过滤；
- 不将 federation 身份相关环境变量随意传给子进程；
- command/process 执行侧继续执行路径和环境边界控制。

这样可以降低以下风险：

- 子 Agent 在错误目录中修改文件；
- 子 Agent 无意中继承父进程的身份信息；
- 多个 Agent 之间通过环境变量产生隐式耦合；
- 一个任务的执行策略泄漏到另一个任务。

相关实现：

- `codex-rs/core/src/environment_selection.rs`
- app-server 中的 command/process 执行逻辑

## 7. Rollout Budget 与加权成本

Codex 的预算管理不只统计输出 token，而是采用加权成本模型：

```text
weighted_tokens =
    output_tokens × sampling_token_weight
  + non_cached_input_tokens × prefill_token_weight
```

### 预算机制包括

- 输入和输出分别计权；
- 区分缓存输入与非缓存输入；
- 支持多个剩余预算阈值；
- 在接近阈值时分阶段提醒；
- 按 thread 记录提醒投递，避免重复提醒。

这使编排器可以更准确地评估：

> 启动一个额外 Agent 带来的收益，是否值得它产生的 token、延迟和资源成本。

相关实现：

- `codex-rs/core/src/rollout_budget.rs`

## 8. 驱逐后的状态恢复

Agent 被驱逐并不意味着任务状态丢失。重新加载时，Codex 会恢复关键 rollout 和执行配置，包括：

- 会话或 rollout 状态；
- 环境选择；
- 执行策略；
- 与当前任务相关的运行时配置。

其中环境选择恢复尤其重要。否则 Agent 虽然重新启动，但可能在错误的 cwd、错误的 workspace 或错误的执行策略下继续工作，造成隐蔽的数据和行为错误。

## 9. 近期优化方向

从近期实现和提交可以看到，优化重点主要集中在以下方面：

| 方向 | 目标 |
| --- | --- |
| 环境恢复 | Agent 驱逐后重载时保持原有环境语义 |
| 作用域明确 | 区分全局环境配置与 turn 级环境配置 |
| 隔离强化 | 限制子进程环境变量继承，减少身份泄漏 |
| 持久化区分 | 明确 turn-start 与普通线程的持久化边界 |
| 上下文传递 | 将 session 信息传递给 shell 等执行路径 |
| 并发控制 | 验证嵌套 spawn 仍遵守共享容量限制 |

对应的验证测试包括：

- `codex-rs/core/tests/suite/agent_execution.rs`
- `v2_nested_spawn_checks_shared_active_execution_capacity`

## 10. 与“从多个 Agent 中选择合适子 Agent”场景的差异

你描述的场景，核心不是“如何运行多个 Agent”，而是：

> 面对一个任务和一组候选 Agent，如何判断应该选择谁、为什么选择，以及如何让选择经验持续变好。

这与 Codex 当前多 Agent 能力存在明显的关注点差异。

### 10.1 Codex 已经覆盖的部分

Codex 对以下问题有比较成熟的支持：

- 是否应该委派子任务；
- 子任务是否属于关键路径；
- 子任务是否足够具体、边界清晰、自包含；
- 是否与主 Agent 的工作重复；
- 多个子任务是否可以并行；
- 子 Agent 使用什么模型和 reasoning effort；
- 子 Agent 需要继承多少上下文；
- 子 Agent 如何汇报、追加任务或被中断。

尤其是 `spawn_agent` 的工具描述中，已经包含了一套轻量级规划规则：先形成高层计划，区分关键路径和 sidecar 任务；只有适合并行的、边界清晰的任务才委派；不要把主 Agent 下一步马上依赖的阻塞任务交给子 Agent；编辑任务需要划分不重叠的写入范围。

相关实现：

- `codex-rs/core/src/tools/handlers/multi_agents_spec.rs`
- `codex-rs/core/src/tools/handlers/multi_agents_common.rs`
- `codex-rs/core/src/config/mod.rs`

### 10.2 Codex 与你的场景之间的 Gap

| 能力       | Codex 当前侧重                             | 你的场景需要                                  |
| -------- | -------------------------------------- | --------------------------------------- |
| Agent 选择 | 暴露可选模型、角色描述和 reasoning effort，主要由主模型判断 | 基于任务语义，从多个专业 Agent 中检索、排序并选择            |
| 任务规划     | 判断是否委派、是否并行、如何拆分子任务                    | 先把任务表示成结构化需求，再匹配 Agent 能力组合             |
| 语义空间对齐   | 依赖 prompt、工具描述和当前上下文对齐                 | 建立任务空间、Agent 能力空间、产出空间之间的显式映射           |
| 经验沉淀     | 主要保留 rollout、线程状态和运行配置                 | 沉淀“什么任务在什么条件下选了什么 Agent，结果如何”           |
| 选择反馈     | 预算、执行状态和结果可见，但不是专门的选择学习闭环              | 记录成功率、返工率、成本、时延、用户评价并更新选择策略             |
| Agent 组合 | 主 Agent 通过工具动态 spawn，偏即时决策             | 可能需要 planner、router、worker、critic 等角色协同 |
| 评估方式     | 更关注任务是否执行完成、资源是否可控                     | 还要评估“选得是否合适”和“是否比其他候选更合适”               |

因此，Codex 更像是一个 **delegation runtime**：负责把已经做出的委派决策可靠地执行起来；你的系统还需要一个 **agent routing / planning layer**：负责理解任务、检索候选、选择 Agent、组合 Agent，并从结果中学习。

## 11. 可以从 Codex 吸取的经验

### 11.1 先区分“选择问题”和“执行问题”

建议把系统拆成两层：

```text
Planning / Routing Layer
  任务理解 -> 任务分解 -> 候选召回 -> Agent 选择 -> 形成执行计划

Execution Layer
  spawn -> 并行执行 -> 消息协作 -> 结果汇总 -> 失败恢复
```

不要让执行器同时承担所有选择逻辑。Codex 的经验表明，并发限制、上下文 fork、消息通信、等待和恢复等机制应该由运行时负责，而不应该全部依赖模型临场发挥。

### 11.2 Agent 描述不能只有角色名

Codex 的模型 picker 会向模型暴露模型描述、支持的 reasoning effort 和 service tier。这个思路可以扩展成更完整的 Agent Card：

```yaml
agent_id: financial-risk-reviewer
capabilities:
  - financial_statement_analysis
  - risk_identification
  - evidence_based_review
input_contract:
  required:
    - company_name
    - financial_statements
  optional:
    - industry_context
output_contract:
  type: risk_report
  required_fields:
    - finding
    - evidence
    - severity
    - confidence
constraints:
  max_context_tokens: 60000
  supports_parallel: true
  writes_files: false
cost:
  estimated_input_tokens: 8000
  estimated_output_tokens: 3000
quality:
  domains:
    finance: 0.91
    general_reasoning: 0.72
```

关键不是“这个 Agent 是什么角色”，而是明确：

- 它擅长什么；
- 它不擅长什么；
- 需要什么输入；
- 能产出什么；
- 产出是否可被下游 Agent 消费；
- 成本、时延和可靠性如何。

### 11.3 语义对齐应落到“任务契约”

仅靠自然语言描述容易出现三个问题：

1. 任务描述和 Agent 描述使用不同词汇；
2. 选择了领域相关但输入不兼容的 Agent；
3. Agent 的输出无法直接被下游步骤使用。

可以将任务统一表示为：

```text
Task = {
  goal,
  domain,
  operations,
  input_schema,
  output_schema,
  constraints,
  quality_bar,
  latency_budget,
  cost_budget,
  parallelism,
  dependencies
}
```

然后分别计算：

```text
task_embedding
capability_embedding
contract_compatibility
historical_success_prior
cost_latency_penalty
```

最终的 Agent 选择分数可以是：

```text
score(agent, task) =
    semantic_fit
  + contract_fit
  + historical_success
  + availability
  - cost_penalty
  - latency_penalty
  - risk_penalty
```

这里的重点是：向量相似度只解决“语义上像不像”，不能单独决定“是否适合执行”。输入输出契约、历史效果和资源约束必须参与排序。

### 11.4 采用“召回 + 重排”，不要一开始就让模型遍历所有 Agent

当候选 Agent 数量变多时，可以参考 Codex 对工具的 deferred loading / tool search 思路：

1. 使用标签、向量、领域和输入输出契约做候选召回；
2. 只把 Top-K 候选的完整描述交给 planner；
3. 由 planner 进行重排和组合；
4. 选择后再加载完整工具和上下文。

这样既降低上下文成本，也避免模型在大量近似 Agent 中产生选择噪声。

### 11.5 把“是否委派”作为独立决策

Codex 的一个重要经验是：任务需要深度、研究或详细分析，并不自动意味着应该 spawn 子 Agent。可以将决策拆成两步：

```text
Step 1: 这个任务是否值得委派？
Step 2: 如果值得，哪个 Agent 最合适？
```

第一步考虑：

- 是否存在真正独立的子任务；
- 是否可以与主线并行；
- 是否会阻塞主线下一步；
- 委派成本是否低于本地完成成本。

第二步才考虑候选 Agent 的专业能力和历史表现。

### 11.6 经验沉淀要记录“决策轨迹”，不只是最终答案

建议每次编排都记录一条 routing trace：

```json
{
  "task_type": "quarterly_financial_analysis",
  "task_features": {
    "domain": "finance",
    "needs_web": true,
    "needs_file_output": true,
    "latency_budget_ms": 120000
  },
  "candidates": [
    {"agent_id": "finance-researcher", "score": 0.87},
    {"agent_id": "general-researcher", "score": 0.74}
  ],
  "selected": ["finance-researcher", "spreadsheet-builder"],
  "plan": "research -> build -> critic",
  "result": {
    "success": true,
    "quality": 0.91,
    "latency_ms": 88400,
    "cost": 1.32,
    "rework_count": 1
  },
  "feedback": {
    "user_rating": 5,
    "critic_findings": 2
  }
}
```

沉淀的不是“某个 Agent 很好”，而是条件化经验：

> 对于什么类型的任务，在什么约束下，选择什么 Agent 组合，产生了什么结果。

这类经验才能反过来优化未来的召回、排序和规划。

### 11.7 使用分层经验，而不是把所有历史直接塞回 prompt

经验可以分成三层：

1. **事实层**：Agent 的能力、输入输出 schema、成本和限制；
2. **案例层**：具体任务的选择、执行和结果；
3. **策略层**：从多个案例归纳出的路由规则。

例如：

```text
事实：spreadsheet-builder 能生成 xlsx，但不能做外部检索。
案例：涉及财务数据和 xlsx 交付时，finance-researcher -> spreadsheet-builder 成功率较高。
策略：当任务同时需要外部数据和 xlsx 交付时，优先采用 research -> build 两阶段计划。
```

Planner 只需要检索与当前任务相关的经验，而不是加载整个历史库。

## 12. 推荐的目标架构

针对“从多个 Agent 中选择合适子 Agent”的场景，可以考虑以下架构：

```text
用户任务
   |
   v
Task Understanding
   | 结构化任务契约、目标、约束、质量标准
   v
Task Decomposition
   | 生成有依赖关系的子任务 DAG
   v
Candidate Retrieval
   | 召回具备相关能力和契约兼容性的 Agent
   v
Agent Ranking
   | 语义匹配 + 历史效果 + 成本 + 时延 + 风险
   v
Plan Construction
   | 选择 Agent、安排顺序、并行度和上下文传递
   v
Codex-style Execution Runtime
   | spawn / message / wait / interrupt / budget / recovery
   v
Evaluation & Learning
   | 质量、返工、成本、时延、用户反馈、选择结果
   |
   +--> 更新 Agent Profile
   +--> 更新 Routing Experience
   +--> 更新 Planner Policy
```

其中 Codex 最适合作为下游的 Execution Runtime 参考，而不是完整的 Agent Selection 学习系统。

## 13. 结论

你的判断是对的：如果关注的是“从多个 Agent 中选出最合适的子 Agent”，前一版文档主要讲了 Codex 的运行时编排能力，没有充分覆盖规划、语义对齐和经验沉淀，因此存在明显的层次 Gap。

更准确的判断是：

- **Codex 已经解决得较好**：委派规则、任务边界、并行执行、上下文继承、通信、预算、隔离和恢复；
- **Codex 没有明显解决或不是主要目标**：面向大量异构 Agent 的语义检索、能力匹配、动态路由、选择反馈学习和规划经验库；
- **你可以直接吸收的经验**：规划与执行分层、先判断是否值得委派、任务契约化、子任务边界化、召回与重排、并行度控制、上下文按需继承、记录完整决策轨迹。

一句话总结：

> Codex 更像“把委派决策执行好”，你的系统还需要“把委派决策做得越来越好”。

## 14. 设计原则总结

Codex 当前的多 Agent 编排可以总结为七条原则：

1. **共享容量，而不是无限并发**：所有 Agent 受 session 级资源边界约束。
2. **逻辑数量与驻留数量解耦**：不活跃 Agent 可以卸载，需要时恢复。
3. **上下文按任务继承**：独立任务不必携带完整历史。
4. **优先异步协作**：主 Agent 不必同步等待每个子任务。
5. **环境和凭据最小继承**：减少 Agent 间的隐式权限扩散。
6. **预算纳入调度决策**：不仅控制能否执行，也控制是否值得执行。
7. **状态恢复保持语义一致**：驱逐和重载不应改变任务所在环境或执行策略。

因此，Codex 的策略优化重点不是单纯提高 Agent 数量，而是优化：

> 什么时候并行、并行多少、传递多少上下文、何时暂停或驱逐，以及如何在预算内可靠恢复执行。

## 15. 相关研究与开源项目调研

这一部分按与你的场景的相关度分层：**动态 Agent 选择与路由**、**规划与工作流生成**、**角色化多 Agent 协作**、**经验优化与评估**、**执行运行时**。

### 15.1 第一优先级：动态路由与异构 Agent 选择

#### Internet of Agents（IoA）

- 论文：[Internet of Agents: Weaving a Web of Intelligent Agents](https://arxiv.org/abs/2407.07061)
- 关键词：异构 Agent、Agent Integration Protocol、动态组队、对话流控制。

IoA 与你的场景最接近。它关注的不是一个固定框架里的几个 Agent，而是如何连接和协调不同来源、不同能力的 Agent。

可借鉴点：

- 为 Agent 定义统一的接入协议和能力描述；
- 运行时根据任务动态组成 Agent team；
- 将消息路由、对话流控制和 Agent 选择解耦；
- 把异构 Agent 看作可发现、可组合的服务，而不是写死在 workflow 中。

对你的启发是：先建设 **Agent Registry + Capability/Contract Schema + Router**，再建设复杂的协作执行器。

#### Semantic Kernel / Microsoft Agent Framework

- 项目：[Semantic Kernel](https://github.com/microsoft/semantic-kernel)
- 后续方向：[Microsoft Agent Framework](https://github.com/microsoft/agent-framework)

Semantic Kernel 的多 Agent 示例包含 triage agent，将请求转交给 billing 或 refund specialist。它适合参考：

- 专家 Agent 注册；
- triage / routing agent；
- 插件、MCP、OpenAPI 工具统一接入；
- Process Framework 中的结构化业务流程；
- memory、planning、observability 等通用能力。

它更偏企业工作流和显式路由，适合借鉴“路由器不是普通 worker”的架构分工。

#### AutoGen

- 项目：[Microsoft AutoGen](https://github.com/microsoft/autogen)
- 论文：[AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](https://arxiv.org/abs/2308.08155)

AutoGen 的核心抽象是可对话 Agent 和多 Agent conversation。它适合参考：

- Agent 之间通过消息协作；
- group chat、selector/group-chat manager 等编排模式；
- 人类、LLM、工具共同参与会话；
- AutoGen Bench 这类评估思路。

需要注意：仓库目前标注为 maintenance mode，新项目被引导到 Microsoft Agent Framework。因此建议把 AutoGen 当作通信和 group-chat 设计参考，而不是新系统的默认底座。

### 15.2 第二优先级：规划与动态工作流生成

#### AFlow

- 论文：[AFlow: Automating Agentic Workflow Generation](https://arxiv.org/abs/2410.10762)
- 项目：[AFlow GitHub](https://github.com/FoundationAgents/AFlow)

AFlow 的核心方向是自动生成 Agent workflow，而不是由工程师手写一条固定链路。与你的场景相关的地方在于：

- 把 workflow 视为可搜索、可优化的程序结构；
- 根据任务和评估结果调整 Agent 顺序、分支和协作方式；
- 通过 workflow-level evaluation 比较不同规划方案。

建议借鉴其思想：不要只学习“选哪个 Agent”，还要学习：

```text
选择哪些 Agent + 以什么顺序执行 + 哪些节点并行 + 何时引入 critic
```

#### ReAct

- 论文：[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- 项目：[ReAct GitHub](https://github.com/ysymyth/ReAct)

ReAct 不是多 Agent 路由系统，但它提供了一个重要的规划循环：

```text
Reason -> Act -> Observe -> Update Plan
```

你的 Router 不应只在任务开始时选择一次 Agent。更合理的是：

- 初始阶段选择候选 Agent；
- 观察中间产出；
- 根据缺口补充或替换 Agent；
- 发现任务结构变化时重新规划。

这适合构建“动态路由”而不是“一次性静态路由”。

#### LangGraph

- 项目：[LangGraph](https://github.com/langchain-ai/langgraph)

LangGraph 是低层、有状态的 Agent workflow runtime，重点包括：

- 图结构和条件分支；
- short-term / long-term state；
- durable execution；
- checkpointing；
- human-in-the-loop；
- 失败后从状态恢复。

它不替你解决 Agent 选择算法，但很适合承载你自己的：

```text
Task Parser -> Candidate Router -> Planner -> Workers -> Evaluator
```

推荐把“选择策略”作为图中的显式节点，而不是隐藏在某个 prompt 里。

### 15.3 第三优先级：角色专业化与标准化协作

#### MetaGPT

- 项目：[MetaGPT](https://github.com/geekan/MetaGPT)
- 论文：[MetaGPT: Meta Programming for Multi-Agent Collaborative Framework](https://arxiv.org/abs/2308.00352)

MetaGPT 的核心思想是把 Agent team 设计成一个软件组织：product manager、architect、project manager、engineer 等角色通过 SOP 协作。

可借鉴点：

- 角色不是 prompt 标签，而是职责、输入、输出和交接协议；
- 通过 SOP 降低自由对话的不确定性；
- 中间产物作为 Agent 之间的接口；
- 复杂任务通过专业角色链路分解。

它的局限是角色和流程相对预定义，动态选择能力弱。因此适合借鉴 **Agent Profile、输出契约和交接协议**，不宜直接照搬固定软件公司组织结构。

#### ChatDev 2.0

- 项目：[ChatDev](https://github.com/OpenBMB/ChatDev)

ChatDev 从固定的 CEO、CTO、Programmer 等角色协作，发展到可配置 Agent、workflow、node 和 context flow。其 puppeteer 方向还探索了 central orchestrator 动态激活和排序 Agent。

可借鉴点：

- Agent 与 workflow 配置分离；
- context flow 显式描述上下文如何在节点之间传递；
- 中间 artifact 和日志可观察；
- central orchestrator 负责动态激活 Agent。

对于你的系统，尤其值得关注的是 **context flow**：语义对齐不仅是“任务和 Agent 匹配”，还包括“上游产出能否被下游消费”。

#### CrewAI

- 项目：[CrewAI](https://github.com/crewAIInc/crewAI)

CrewAI 把 Crews 和 Flows 分开：

- Crews：自主、角色化的 Agent 协作；
- Flows：有状态、事件驱动、可分支的 workflow。

可借鉴点：

- sequential / hierarchical process；
- `router`、`listen`、条件分支；
- Pydantic structured state；
- checkpointing、async execution、human review；
- Crew 嵌套进 Flow。

它适合做产品原型和工作流验证，但 Agent 选择本身更多是通过配置和 Flow 路由完成，尚不是完整的学习型 Agent router。

### 15.4 第四优先级：选择优化、结果重排与经验学习

#### RouteLLM

- 论文：[RouteLLM: Learning to Route LLMs with Preference Data](https://arxiv.org/abs/2406.18665)
- 项目：[RouteLLM](https://github.com/lm-sys/RouteLLM)

RouteLLM 主要解决的是“不同模型之间如何路由”，不是专业 Agent 选择，但方法可以直接迁移：

- 为请求抽取特征；
- 用历史偏好或质量标签训练 router；
- 在质量和成本之间做动态 trade-off；
- 比较强模型、弱模型和路由策略的 Pareto frontier。

迁移到你的场景，就是训练：

```text
task features -> agent/team selection
```

反馈信号可以包括：质量、用户评分、返工次数、成本、时延和安全风险。

#### FrugalGPT

- 论文：[FrugalGPT: How to Make Large Language Models Cheaper While Maintaining Quality](https://arxiv.org/abs/2305.05176)

FrugalGPT 的价值在于级联和预算意识：

- 先尝试低成本候选；
- 质量不够再升级；
- 根据任务难度选择模型组合；
- 在成本和质量之间动态平衡。

迁移到 Agent 场景，可以设计：

```text
cheap specialist -> evaluator -> stronger specialist if needed
```

这比所有任务一开始都启动最强、最贵的 Agent 更适合生产系统。

#### LLM-Blender

- 论文：[LLM-Blender: Ensembling Large Language Models with Pairwise Ranking and Generative Fusion](https://arxiv.org/abs/2306.02561)
- 项目：[LLM-Blender](https://github.com/yuchenlin/LLM-Blender)

LLM-Blender 重点是多个模型输出后的 pairwise ranking 和 fusion。对你的场景可迁移为：

- 让多个候选 Agent 分别给出方案；
- 用独立 evaluator 对候选进行两两比较；
- 选择或融合最好的 Agent 结果；
- 将比较结果作为后续 routing experience。

它适合解决“静态 profile 很像，难以提前判断谁更好”的问题。

### 15.5 第五优先级：评估、基准与运行时

#### AgentVerse

- 项目：[AgentVerse](https://github.com/OpenBMB/AgentVerse)
- 相关综述：[A Survey on Large Language Model based Autonomous Agents](https://arxiv.org/abs/2308.11432)

AgentVerse 更适合参考多 Agent 任务组织、角色协作和 benchmark 维度。它的启发是：Agent team 的效果不应只看最终答案，还应看：

- 任务完成率；
- 协作轮数；
- Agent 间通信成本；
- 任务分工是否合理；
- 是否出现重复劳动或冲突。

#### AgentBench / GAIA

- AgentBench：[论文](https://arxiv.org/abs/2308.03688)
- GAIA：[论文](https://arxiv.org/abs/2311.12983)

这些 benchmark 不直接提供路由器，但可以帮助你建立评估集。建议增加专门的 routing 指标：

| 指标                     | 含义                      |
| ---------------------- | ----------------------- |
| Selection Accuracy     | 选择的 Agent 是否属于专家标注的合理集合 |
| Best-Agent Regret      | 与事后最优 Agent 的质量差距       |
| Team Regret            | 选择的 Agent 组合与最优组合的差距    |
| Contract Compatibility | 输入输出契约是否匹配              |
| Rework Rate            | 因 Agent 选择不当导致的返工比例     |
| Routing Cost           | 路由阶段自身消耗的 token 和时间     |
| End-to-End Utility     | 质量、成本、时延的综合收益           |

## 16. 推荐的开源参考顺序

不要一次性研究所有项目，建议按以下顺序下钻：

### 第一阶段：先验证架构

1. **LangGraph**：理解如何把 Planner、Router、Worker、Evaluator 组织成有状态图；
2. **Semantic Kernel / Microsoft Agent Framework**：参考 triage router 和企业级 Agent 注册；
3. **CrewAI**：快速验证角色、Flow、结构化状态和分支编排。

### 第二阶段：研究动态选择

4. **IoA**：研究异构 Agent 的协议、发现和动态组队；
5. **RouteLLM**：借鉴基于历史反馈的路由训练；
6. **LLM-Blender**：借鉴候选结果排序和 pairwise evaluator。

### 第三阶段：研究规划与经验

7. **AFlow**：研究如何自动搜索和优化 Agent workflow；
8. **ReAct**：研究执行中基于观察结果重新规划；
9. **MetaGPT / ChatDev**：研究角色契约、SOP、中间 artifact 和 context flow。

### 第四阶段：补运行时和评估

10. **Codex**：并发、上下文 fork、预算、隔离、恢复；
11. **LangGraph**：checkpoint、durable execution 和人工介入；
12. **AgentBench / GAIA**：建立任务级评估和 routing benchmark。

## 17. 针对你的场景的最小可行方案

建议不要一开始训练复杂的端到端 Planner，而是先实现一个可解释的 Router：

```text
1. Task Parser
   将用户任务转换成结构化 Task Contract

2. Agent Registry
   保存 Agent Card、能力、输入输出契约、成本和历史表现

3. Candidate Retriever
   通过标签、向量、契约兼容性召回 Top-K

4. Rule + LLM Reranker
   先用硬约束过滤，再用 LLM 对候选排序

5. Plan Builder
   生成 Agent DAG，决定顺序、并行、上下文和验收方式

6. Runtime
   执行 spawn、message、wait、interrupt、budget 和 recovery

7. Evaluator
   评价最终质量、选择合理性、成本、时延和返工

8. Routing Memory
   记录候选、选择理由、执行结果和用户反馈
```

第一版可以使用显式打分：

```text
routing_score =
    0.30 * semantic_fit
  + 0.25 * contract_fit
  + 0.20 * historical_success
  + 0.10 * output_quality
  + 0.05 * availability
  - 0.05 * normalized_cost
  - 0.05 * normalized_latency
```

后续再用真实 routing trace 学习权重，或者训练 pairwise ranker。这样更容易解释、调试和做离线评估。

## 18. 调研结论

与你的场景最直接相关的研究和项目不是单一的“多 Agent 框架”，而是几类能力的组合：

- **IoA**：异构 Agent 的接入、发现和动态组队；
- **Semantic Kernel / Microsoft Agent Framework**：triage router、专家 Agent 和企业流程；
- **LangGraph**：有状态 Planner / Router / Worker / Evaluator 执行图；
- **AFlow**：动态 workflow 生成和 workflow-level 优化；
- **RouteLLM / FrugalGPT**：基于反馈的质量-成本路由；
- **LLM-Blender**：候选结果排序与融合；
- **MetaGPT / ChatDev / CrewAI**：角色契约、SOP、context flow 和结构化协作；
- **Codex**：并发、上下文、预算和恢复运行时；
- **AgentBench / GAIA**：建立任务级和路由级评估体系。

最值得形成你自己差异化能力的部分是：

> **Task Contract + Agent Card + Candidate Retrieval + Experience-aware Ranking + Dynamic Plan + Routing Evaluation**。

这比单纯做一个“能调用多个 Agent 的框架”更接近你真正要解决的问题。

## 15. 相关研究与开源项目调研

这一部分按与你的场景的相关度分层：**动态 Agent 选择与路由**、**规划与工作流生成**、**角色化协作**、**经验优化**以及**执行运行时**。

### 15.1 动态路由与异构 Agent 选择

#### Internet of Agents（IoA）

- 论文：[Internet of Agents: Weaving a Web of Intelligent Agents](https://arxiv.org/abs/2407.07061)

IoA 与你的场景最接近，关注不同来源、不同能力的异构 Agent 如何接入、发现、动态组队和控制对话流。

可借鉴：

- Agent Integration Protocol：为异构 Agent 定义统一接入协议；
- Agent capability/profile：让 Agent 可被发现和比较；
- Dynamic agent teaming：根据任务动态组成 Agent team；
- Conversation flow control：将消息路由与协作流程显式化。

核心启发是先建设 `Agent Registry + Capability Schema + Contract + Router`，再建设复杂的执行器。

#### Semantic Kernel / Microsoft Agent Framework

- 项目：[Semantic Kernel](https://github.com/microsoft/semantic-kernel)
- 后续方向：[Microsoft Agent Framework](https://github.com/microsoft/agent-framework)

Semantic Kernel 的多 Agent 示例包含 triage agent，将请求转发给 billing、refund 等 specialist agent。适合参考：

- 专家 Agent 注册；
- Triage / routing agent；
- 插件、MCP、OpenAPI 工具统一接入；
- Process Framework 中的结构化业务流程；
- planning、memory 和 observability 的组合。

它体现了一个重要分工：**Router 不是普通 Worker，Router 的职责是理解请求、判断意图和选择专家。**

#### AutoGen

- 项目：[AutoGen](https://github.com/microsoft/autogen)
- 论文：[AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](https://arxiv.org/abs/2308.08155)

AutoGen 的核心抽象是可对话 Agent 和多 Agent conversation，适合参考：

- Agent 之间通过消息协作；
- group chat 和 selector/group-chat manager；
- 人类、LLM 和工具共同参与；
- AutoGen Bench 等评估思路。

仓库目前处于 maintenance mode，新项目被引导到 Microsoft Agent Framework，因此更适合作为通信和 group-chat 的设计参考。

### 15.2 规划与动态工作流生成

#### AFlow

- 论文：[AFlow: Automating Agentic Workflow Generation](https://arxiv.org/abs/2410.10762)
- 项目：[AFlow GitHub](https://github.com/FoundationAgents/AFlow)

AFlow 关注自动生成和优化 Agent workflow，而不是只由工程师手写固定链路。对你的场景，重要的是：

```text
不仅选择哪个 Agent
还要优化 Agent 组合、执行顺序、并行关系、critic 位置和重试策略
```

这意味着 Planner 的优化目标应是整个 workflow，而不是单个 Agent 的分类准确率。

#### ReAct

- 论文：[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- 项目：[ReAct GitHub](https://github.com/ysymyth/ReAct)

ReAct 提供了 `Reason -> Act -> Observe -> Update Plan` 循环。它不是多 Agent Router，但适合借鉴动态重规划：

- 初始阶段选择候选 Agent；
- 观察中间产出；
- 根据能力缺口补充或替换 Agent；
- 发现任务结构变化时重新规划。

因此不要把 Agent 选择设计成一次性决策，而应允许执行中重路由。

#### LangGraph

- 项目：[LangGraph](https://github.com/langchain-ai/langgraph)

LangGraph 是低层、有状态的 Agent workflow runtime，提供 durable execution、checkpoint、memory、human-in-the-loop 和失败恢复等能力。

它不替你解决 Agent 选择算法，但适合承载如下显式图：

```text
Task Parser -> Candidate Router -> Planner -> Workers -> Evaluator -> Replanner
```

建议把 Router 和 Evaluator 作为图中的显式节点，不要把选择逻辑隐藏在 Worker prompt 中。

### 15.3 角色专业化与标准化协作

#### MetaGPT

- 项目：[MetaGPT](https://github.com/geekan/MetaGPT)
- 论文：[MetaGPT: Meta Programming for Multi-Agent Collaborative Framework](https://arxiv.org/abs/2308.00352)

MetaGPT 将 Agent team 设计成软件组织，通过 product manager、architect、project manager、engineer 等角色和 SOP 协作。

可借鉴：

- 角色职责不是简单 prompt 标签；
- 每个角色有明确输入、输出和交接协议；
- 中间产物是 Agent 之间的接口；
- 标准化 SOP 降低自由对话的不确定性。

局限是角色和流程相对预定义，动态选择能力较弱，因此应重点借鉴 Agent Profile、输出契约和交接协议，而不是照搬固定组织结构。

#### ChatDev 2.0

- 项目：[ChatDev](https://github.com/OpenBMB/ChatDev)

ChatDev 2.0 从固定角色协作发展到可配置 Agent、workflow、node 和 context flow；其 puppeteer 方向还探索了 central orchestrator 动态激活和排序 Agent。

对你的场景最有价值的是 **context flow**：语义对齐不仅是“任务和 Agent 匹配”，还包括“上游 Agent 的输出能否被下游 Agent 消费”。

#### CrewAI

- 项目：[CrewAI](https://github.com/crewAIInc/crewAI)

CrewAI 将 Crews 和 Flows 分开：Crews 负责自主、角色化协作；Flows 负责有状态、事件驱动和条件分支。

适合参考：

- sequential / hierarchical process；
- router、listen 和条件分支；
- Pydantic structured state；
- checkpoint、async execution 和 human review；
- Crew 嵌入 Flow 的混合模式。

### 15.4 选择优化、排序与经验学习

#### RouteLLM

- 论文：[RouteLLM: Learning to Route LLMs with Preference Data](https://arxiv.org/abs/2406.18665)
- 项目：[RouteLLM](https://github.com/lm-sys/RouteLLM)

RouteLLM 主要研究不同模型之间的请求路由，但方法可以直接迁移到 Agent 路由：

```text
task features -> agent/team selection
```

可借鉴：

- 用历史偏好或质量标签训练 router；
- 在质量和成本之间做动态 trade-off；
- 比较不同 router 的 Pareto frontier；
- 用真实任务反馈更新选择策略。

#### FrugalGPT

- 论文：[FrugalGPT](https://arxiv.org/abs/2305.05176)

FrugalGPT 的级联思路适合迁移到 Agent：

```text
cheap specialist -> evaluator -> stronger specialist if needed
```

先调用低成本 Agent，质量不足时再升级，比所有任务一开始都启动最贵的 Agent 更适合生产环境。

#### LLM-Blender

- 论文：[LLM-Blender](https://arxiv.org/abs/2306.02561)
- 项目：[LLM-Blender GitHub](https://github.com/yuchenlin/LLM-Blender)

LLM-Blender 通过 pairwise ranking 和 generative fusion 比较多个模型输出。迁移到 Agent 场景可以：

- 让多个候选 Agent 产生结果；
- 用独立 evaluator 做两两比较；
- 选择或融合最佳结果；
- 将比较结果沉淀为 routing experience。

### 15.5 执行运行时与评估

#### AgentVerse

- 项目：[AgentVerse](https://github.com/OpenBMB/AgentVerse)
- 综述：[A Survey on Large Language Model based Autonomous Agents](https://arxiv.org/abs/2308.11432)

AgentVerse 适合参考多 Agent 任务组织、角色协作和 benchmark 维度。评估不应只看最终答案，还应看：

- 任务完成率；
- 协作轮数；
- Agent 间通信成本；
- 分工是否合理；
- 是否出现重复劳动或冲突。

#### AgentBench / GAIA

- [AgentBench](https://arxiv.org/abs/2308.03688)
- [GAIA](https://arxiv.org/abs/2311.12983)

可以在通用 Agent benchmark 之上增加专门的 routing 指标：

| 指标 | 含义 |
| --- | --- |
| Selection Accuracy | 选择的 Agent 是否属于合理候选集合 |
| Best-Agent Regret | 与事后最优 Agent 的质量差距 |
| Team Regret | 与事后最优 Agent 组合的差距 |
| Contract Compatibility | 输入输出契约是否匹配 |
| Rework Rate | 因选择不当导致的返工比例 |
| Routing Cost | 路由阶段自身的 token 和时间成本 |
| End-to-End Utility | 质量、成本、时延的综合收益 |

## 16. 推荐研究顺序

### 第一阶段：验证系统架构

1. [LangGraph](https://github.com/langchain-ai/langgraph)：Planner / Router / Worker / Evaluator 的有状态执行图；
2. [Semantic Kernel](https://github.com/microsoft/semantic-kernel)：triage router 和 specialist Agent；
3. [CrewAI](https://github.com/crewAIInc/crewAI)：角色、Flow、结构化状态和分支编排。

### 第二阶段：研究动态选择

4. [Internet of Agents](https://arxiv.org/abs/2407.07061)：异构 Agent 的协议、发现和动态组队；
5. [RouteLLM](https://arxiv.org/abs/2406.18665)：基于历史反馈的路由训练；
6. [LLM-Blender](https://arxiv.org/abs/2306.02561)：候选结果排序与融合。

### 第三阶段：研究规划和经验

7. [AFlow](https://arxiv.org/abs/2410.10762)：动态 workflow 生成和 workflow-level 优化；
8. [ReAct](https://arxiv.org/abs/2210.03629)：执行中的观察和重新规划；
9. [MetaGPT](https://github.com/geekan/MetaGPT)：角色契约和 SOP；
10. [ChatDev](https://github.com/OpenBMB/ChatDev)：context flow 和 central orchestrator。

### 第四阶段：补执行和评估

11. Codex 当前的多 Agent runtime：并发、上下文、预算和恢复；
12. [AutoGen](https://github.com/microsoft/autogen)：消息协作和 group chat；
13. [AgentVerse](https://github.com/OpenBMB/AgentVerse)：多 Agent benchmark；
14. AgentBench / GAIA：建立任务级和路由级评估。

## 17. 针对当前场景的最小可行方案

不建议一开始训练复杂的端到端 Planner。第一版可以先实现一个可解释的 Router：

```text
Task Parser
  -> 将用户任务转换成结构化 Task Contract

Agent Registry
  -> 保存 Agent Card、能力、输入输出契约、成本和历史表现

Candidate Retriever
  -> 通过标签、向量、契约兼容性召回 Top-K

Rule + LLM Reranker
  -> 先做硬约束过滤，再用 LLM 对候选排序

Plan Builder
  -> 生成 Agent DAG，决定顺序、并行、上下文和验收方式

Runtime
  -> 执行 spawn、message、wait、interrupt、budget 和 recovery

Evaluator
  -> 评价最终质量、选择合理性、成本、时延和返工

Routing Memory
  -> 记录候选、选择理由、执行结果和用户反馈
```

第一版可使用显式打分：

```text
routing_score =
    0.30 * semantic_fit
  + 0.25 * contract_fit
  + 0.20 * historical_success
  + 0.10 * output_quality
  + 0.05 * availability
  - 0.05 * normalized_cost
  - 0.05 * normalized_latency
```

后续再使用真实 routing trace 学习权重，或者训练 pairwise ranker。这样更容易解释、调试和做离线评估。

## 18. 调研结论

与你的场景最相关的不是单一的“多 Agent 框架”，而是几类能力的组合：

- **IoA**：异构 Agent 接入、发现和组队；
- **Semantic Kernel / Microsoft Agent Framework**：triage router、专家 Agent 和企业流程；
- **RouteLLM / FrugalGPT**：质量、成本和历史反馈驱动的路由；
- **AFlow**：Workflow 级规划和优化；
- **LLM-Blender**：候选结果排序与融合；
- **MetaGPT / ChatDev / CrewAI**：角色契约、SOP、Context Flow；
- **LangGraph**：有状态执行和重规划；
- **Codex**：并发、上下文、预算、隔离和恢复；
- **AgentBench / GAIA**：建立任务级和路由级评估体系。

最值得形成差异化能力的部分是：

> **Task Contract + Agent Card + Candidate Retrieval + Experience-aware Ranking + Dynamic Plan + Routing Evaluation**。

这比单纯做一个“能调用多个 Agent 的框架”更接近当前问题的核心。

## 19. 从“Agent Router”走向真正的智能化

当前方案已经覆盖了任务结构化、候选召回、Agent 排序和执行反馈，但如果目标是持续推进智能化，还需要从“静态匹配”走向“学习如何组织 Agent”。

### 19.1 从选择一个 Agent 升级到学习如何组队

基础路由是：

```text
一个任务 -> 选择一个 Agent
```

更有价值的目标是：

```text
一个任务 -> 选择一组 Agent + 分配角色 + 决定顺序 + 决定交接方式
```

例如研究任务可以动态形成：

```text
Researcher -> Evidence Verifier -> Synthesizer -> Critic
```

但这不应该是固定流水线。系统需要学习：

- 哪些任务只需要一个 Agent；
- 哪些任务需要两个 Agent 交叉验证；
- 哪些任务适合 `research -> write`；
- 哪些任务适合 `parallel research -> merge`；
- 哪些任务必须先补充信息；
- 哪些任务启用 Critic 的收益低于它的成本。

这类问题本质上是 **Team Formation / Workflow Search**，可参考 [AFlow](https://arxiv.org/abs/2410.10762)、[Internet of Agents](https://arxiv.org/abs/2407.07061) 和 [MetaGPT](https://github.com/geekan/MetaGPT)。

### 19.2 从文本相似度升级到可执行能力空间

Embedding 只能回答“任务和 Agent 描述是否相似”，不能回答“Agent 是否真的适合执行”。建议把 Agent 能力拆成四个空间：

```text
Capability Space  -> 它会做什么
Input Space       -> 它需要什么输入
Output Space      -> 它能产出什么
Constraint Space  -> 它在什么条件下工作
```

任务也映射到相同空间：

```text
fit =
  capability_fit
  * input_compatibility
  * output_compatibility
  * constraint_satisfaction
```

因此，Agent Profile 不应只有角色名，而应包含工具、输入输出 schema、限制条件、成本、时延和真实表现。

### 19.3 从经验记录升级到决策经验学习

普通 memory 往往只是保存历史对话。你的系统需要保存 **Routing Memory** 和 **Planning Memory**：

```text
任务是什么
候选 Agent 有哪些
为什么选 A 没选 B
生成了什么计划
哪个节点失败
失败是选择、规划、交接还是执行问题
如果重来应该如何选择
```

建议为每次编排记录 routing trace：

```json
{
  "task_type": "financial_research",
  "candidate_agents": [
    {"id": "general-researcher", "predicted_score": 0.72},
    {"id": "finance-researcher", "predicted_score": 0.88}
  ],
  "selected_team": ["finance-researcher", "evidence-verifier"],
  "plan": "research -> verify -> synthesize",
  "result": {
    "quality": 0.91,
    "latency_ms": 88400,
    "cost": 1.32,
    "rework_count": 1
  },
  "diagnosis": {
    "selection_quality": 0.94,
    "planning_quality": 0.86,
    "execution_quality": 0.89
  }
}
```

必须区分：

- Agent Selection Quality；
- Planner Quality；
- Execution Quality。

否则系统只能知道“结果失败”，却不知道应该更换 Agent、修改拆解方式，还是修复上下文交接。

### 19.4 从成功率升级到失败归因

建议把失败归因结构化，而不是只记录 `success = false`：

```text
Failure Diagnosis:
- task_understanding_error
- wrong_agent_selection
- missing_capability
- bad_task_decomposition
- invalid_input_contract
- weak_context_handoff
- execution_failure
- evaluator_mistake
- budget_exceeded
```

例如输出没有引用，不一定意味着研究 Agent 不好，也可能是 output contract 没有要求 citation 字段。只有完成归因，经验才能作用于正确的策略层。

### 19.5 引入不确定性和探索策略

面对新任务时，不能只看平均成功率。路由器还应该维护：

```text
expected_quality
uncertainty
cost
latency
risk
```

不同任务需要不同策略：

- 高风险任务：选择质量下界最高的 Agent；
- 探索性任务：允许尝试高不确定性 Agent；
- 成本敏感任务：选择质量 / 成本比最高的 Agent；
- 未知任务：先做小规模 probe 或多候选短评估。

后续可以研究 Bayesian optimization、contextual bandit、Thompson Sampling 和 Pareto optimization。早期不必直接训练复杂模型，但应先记录不确定性，避免把未知能力误当成稳定能力。

### 19.6 从固定 Agent Card 升级到动态能力发现

Agent 的能力不应完全依赖人工填写。可以从真实执行中自动更新 Profile：

```text
初始 Profile
  -> 观察真实输入、工具调用、产出和失败
  -> 推断新的能力或限制
  -> 更新 Profile
  -> 影响后续路由
```

例如系统可以逐渐发现某个通用研究 Agent：

```yaml
learned_profile:
  strong_domains:
    legal: 0.89
    policy: 0.84
  weak_domains:
    finance_calculation: 0.56
    spreadsheet_output: 0.48
  strong_output_modes:
    citation_markdown: 0.91
```

可参考 [Reflexion](https://arxiv.org/abs/2303.11366) 的语言反馈和 episodic memory，以及 [Voyager](https://arxiv.org/abs/2305.16291) 的可复用技能库思想。

### 19.7 把经验升级为可组合的 Planning Skill

经验不应永远停留在自然语言总结，可以在反复验证后提炼成可执行策略：

```yaml
skill_id: evidence_based_research
trigger:
  - needs_external_sources
  - requires_citations
plan:
  - research
  - verify
  - synthesize
constraints:
  verifier_must_be_independent: true
success_rate: 0.87
```

这样系统就从 `experience memory` 升级为 `retrievable planning skill`，Planner 可以检索和组合这些技能，而不是每次从零生成计划。

### 19.8 让 Planner 预测信息价值

更智能的 Planner 不应一开始就决定全部步骤，而应判断下一步最值得获取的信息：

```text
预期减少的不确定性 > 获取信息的成本
```

可选动作包括：

- 向用户询问一个澄清问题；
- 调用便宜的 Task Classifier；
- 检索 Agent Registry；
- 让候选 Agent 做小型 probe；
- 直接执行；
- 启动多个候选做短评估。

这相当于把 Planner 从固定流程生成器提升为 Information-Gathering Planner。

### 19.9 从单一总分升级到 Pareto 路由

不要把质量、成本和时延过早压成一个总分。可以先保留 Pareto 前沿：

```text
Agent A -> 最高质量
Agent B -> 最低成本
Agent C -> 最低延迟
Agent D -> 质量与成本最佳平衡
```

再由任务约束决定选择：

- 低延迟场景过滤超出 deadline 的 Agent；
- 高可靠场景选择质量下界最高的 Agent；
- 探索场景保留高不确定性候选；
- 低成本场景优先 utility / cost。

这种方式比固定权重更容易解释，也更适合不同业务场景。

## 20. 三个真正值得投入的方向

### 20.1 Experience-aware Planner

```text
当前任务
  -> 召回相似历史任务
  -> 查看过去的 Agent 选择和结果
  -> 生成计划
  -> 执行
  -> 诊断差异
  -> 更新经验
```

目标是让 Planner 不再每次从零开始。

### 20.2 Self-improving Router

```text
候选召回
  -> Router 选择
  -> 真实执行
  -> 质量评估
  -> 反事实分析
  -> 更新 Router
```

早期可以使用规则 + LLM reranker，后续再训练 pairwise ranker、contextual bandit 或 cost-aware policy。

### 20.3 Workflow / Team Search

把 Agent 组合视为搜索空间：

```text
A
A -> B
A -> C
A || B -> C
A -> Critic -> B
A -> B -> Critic -> Repair
```

通过离线 benchmark 比较这些组合，学习哪些任务适合单 Agent、并行、验证、重试或动态替换。

## 21. 技术演进路线

### Phase 1：可解释路由

```text
Task Contract
Agent Card
Candidate Retrieval
Hard Constraint Filter
LLM Reranker
Routing Trace
```

目标：能够回答“为什么选择这个 Agent”。

### Phase 2：经验增强

```text
Similar Task Retrieval
Routing Memory
Failure Diagnosis
Agent Profile Update
Planning Skill Extraction
```

目标：系统能够利用历史经验，而不是每次从零开始。

### Phase 3：动态重规划

```text
Intermediate Evaluation
Uncertainty Estimation
Agent Replacement
Budget-aware Escalation
Replanning
```

目标：执行中发现 Agent 不适合时能够自我修正。

### Phase 4：策略学习

```text
Pairwise Ranking
Contextual Bandit
Workflow Search
Counterfactual Evaluation
Offline Policy Evaluation
```

目标：Router 和 Planner 本身可以通过真实数据持续变好。

## 22. 最终定位

真正值得做的不是一个“可以调用很多 Agent 的平台”，而是：

> 一个能够学习“什么任务应该如何组织 Agent”的系统。

可以将产品定位为：

> **面向异构 Agent 的经验驱动规划与动态组队系统**
>
> **Experience-Driven Agent Team Formation and Planning**

基础设施层包括 Agent Registry、Invocation、Message Passing 和 Workflow Runtime；智能化核心包括 Task Understanding、Capability Grounding、Team Formation、Planning、Uncertainty、Credit Assignment、Experience Reuse 和 Policy Improvement。

## 相关代码索引

- `codex-rs/core/src/agent/control.rs`
- `codex-rs/core/src/agent/control/execution.rs`
- `codex-rs/core/src/agent/control/residency.rs`
- `codex-rs/core/src/tools/handlers/multi_agents_v2/`
- `codex-rs/core/src/environment_selection.rs`
- `codex-rs/core/src/rollout_budget.rs`
- `codex-rs/core/tests/suite/agent_execution.rs`
