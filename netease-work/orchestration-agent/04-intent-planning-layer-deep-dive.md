---
tags: [netease, orchestration-agent, intent, planning, agentic-loop, task-toolkit]
aliases: [Orchestration Agent 意图与规划层深度分析]
---

# 意图与规划层深度分析

## Layer Judgment

本项目整体上通过 Workflow 承载任务生命周期，通过主编排 Agent 动态调用专业 Agent 完成用户目标。

本篇深入意图与规划层：它负责回答“用户到底要完成什么、需要哪些能力、应该拆成哪些步骤、哪些步骤可以并行、结果不符合预期时如何调整”。

一个重要判断是：当前项目没有独立的传统意图分类器或 Planner 服务。意图理解、Agent 选择和计划生成主要由 `LoopOrchestrationAgent` 通过 Prompt 和工具调用完成；代码侧负责提供候选信息、校验计划、解析 Agent、保存状态和限制非法状态。

## 先用一条完整流程理解这一层

直白地说，这一层把用户的一句话变成一份“可以交给执行层逐步完成的任务计划”。

```text
用户输入
  -> 解析 TaskContext
  -> 注入用户、项目、附件、知识库和可用 Agent
  -> 主 Agent 理解目标和任务对象
  -> 为每个子任务列出能力匹配的候选 Agent
  -> task_update_plan_tool 提交完整计划
  -> 服务端校验步骤、依赖、Agent 和状态
  -> 主 Agent 调 task_execute_tool 执行某个步骤
  -> 读取结果摘要或详细结果
  -> 根据结果继续、重试、跳过或改写计划
  -> 所有必要步骤完成后汇总回答
```

这层不直接完成专业任务，也不负责远程 HTTP。它提供的是“决策中间层”：

```text
自然语言目标
  -> 结构化任务意图
  -> 候选 Agent + 执行计划
  -> 可执行步骤和结果引用
```

## Core Idea

核心机制是：

> 用稳定的编排规则约束主 Agent，用运行时 Agent 快照提供可选能力，用 TaskToolkit 把 LLM 的规划动作转换成经过校验的计划状态。

它解决两个问题：

1. 用户只描述目标，没有直接提供执行步骤和 Agent 分配；
2. 任务执行过程中结果可能改变后续决策，计划不能只在开始时生成一次。

为什么采用这个抽象：

- 意图识别和任务拆解天然需要语言理解，适合由 LLM 处理；
- Agent 可用性、状态转换和结果引用必须可控，适合由代码处理；
- 将两者分开后，模型可以灵活规划，但不能任意绕过计划和执行契约。

## Mechanism Priority Map

### Primary mechanisms

#### 1. Prompt 驱动的任务理解与规划

- 优先级：primary
- 作用：把用户目标解释成任务对象、子任务、验收标准和执行顺序。
- 核心实现：稳定 `_INSTRUCTIONS_BASE` + 动态用户上下文 + Agent 快照。
- 关键文件：`src/agents/loop_orchestration_agent.py`、`src/workflow/prompts/orchestration.py`。

#### 2. 计划工具作为决策边界

- 优先级：primary
- 作用：把 LLM 生成的计划变成结构化、可持久化、可通知前端的状态。
- 核心实现：`task_update_plan_tool`、`task_execute_tool` 和计划状态机。
- 关键文件：`src/tools/task_tools.py`。

#### 3. Agent 候选与权限解析

- 优先级：primary
- 作用：让模型提供能力候选，服务端根据当前用户和项目范围选出实际 Agent。
- 核心实现：`candidate_agent_ids` + scope 优先级解析。
- 关键文件：`src/workflow/agent_filter.py`、`src/tools/task_tools.py`、`src/schema/agent_info.py`。

### Secondary mechanisms

#### 4. 计划执行结果反馈

- 优先级：secondary
- 作用：把子任务结果摘要、失败、超时和取消重新提供给主 Agent。
- 关键文件：`task_get_plan_tool`、`task_get_result_tool`、`task_execute_tool`。

#### 5. 计划重放和上下文压缩恢复

- 优先级：secondary
- 作用：在多轮对话或上下文压缩后恢复计划视图和执行状态。
- 关键文件：`TaskToolkit.build_replay_plan_updated_event`、Agno `CompressionManager`。

#### 6. 同 Agent 连续步骤约束

- 优先级：secondary
- 作用：避免把同一个 Agent 能连续完成的工作拆成多个无意义调用。
- 关键文件：`TaskToolkit._validate_same_agent_chains`。

### Supporting mechanisms

- XML 形式的 Agent 列表渲染；
- 用户历史纠错记忆；
- 附件和知识库提示；
- 工具调用次数上限和结果长度限制；
- 主 Agent HITL 工具；
- Prompt caching 稳定性设计。

## Layer Problem

这一层承受的主要压力是：

| 压力 | 具体问题 |
|---|---|
| 意图不完整 | 用户说目标，不说步骤、执行者和验收方式 |
| 能力匹配 | 多个 Agent 能力重叠，需要选出合适执行者 |
| 动态性 | 前序结果可能改变后续任务 |
| 权限 | 模型不能调用当前用户不可见的 Agent |
| 上下文成本 | 计划和子任务结果会持续增加 prompt 长度 |
| 状态一致性 | 模型输出的计划必须与已完成步骤相容 |
| 可解释性 | 前端需要看到计划、步骤和状态变化 |
| 可靠性 | 失败、超时和取消不能被误判为成功 |

## Core Abstractions

### `LoopOrchestrationAgent`

- 表示：面向用户目标的主编排 Agent。
- 拥有：语言理解、规划判断、工具选择、结果汇总。
- 不拥有：Agent 注册权限的最终判定、远程执行细节、专业任务结果。
- 相邻抽象：`TaskToolkit`、`TaskContext`、`AgentInfo`。
- 代码：`src/agents/loop_orchestration_agent.py:260`。

### 稳定编排指令

- 表示：不会随每轮 Agent 列表变化的系统规则。
- 内容：何时委派、如何拆分、候选 Agent 规则、计划规则、失败处理和最终回答规则。
- 作用：提供行为边界和决策规范。
- 代码：`_INSTRUCTIONS_BASE`、`_build_instructions`。

### 动态运行上下文

- 表示：当前请求的用户、项目、资源和 Agent 快照。
- 内容：`TaskContext`、`_session_agents`、`_session_extra_data`、`_user_memories`。
- 作用：让同一个稳定 Agent 根据当前请求做不同决策。
- 代码：`LoopOrchestrationAgent.arun`、`build_orchestration_prompt_for_agent`。

### `TaskPlanStepInput`

- 表示：LLM 提交给计划工具的单个计划步骤。
- 核心字段：`step_id`、`description`、`candidate_agent_ids`、`status`、`depends_on`。
- 不包含：最终 `agent_id` 和执行指令 `instruction`。
- 原因：候选 Agent 由服务端解析，执行指令在实际执行时根据上下文动态生成。

### `TaskPlanStep`

- 表示：服务端保存的计划步骤。
- 在输入步骤基础上增加最终解析出的 `agent_id`。
- 这是“模型计划”到“服务端执行计划”的转换结果。

### `task_toolkit_state`

- 表示：计划和结果的持久化运行态。
- 主要内容：`plan_id`、`plan_goal`、`plan_steps`、步骤结果和结果引用。
- 作用：支持工具间共享、上下文压缩后恢复、多轮计划重放。

## Main Flow

### 1. 解析用户任务

`LoopOrchestrationAgent._parse_task_context` 将输入统一为 `TaskContext`：

```text
str / dict / BaseModel / TaskContext
  -> TaskContext
  -> trace_id / request_id / session_id / user_id / inputs / constraints
```

用户原始输入最终通过 `build_orchestration_prompt_for_agent` 放入 `<user_input>`。历史对话由 Agno 的 `add_history_to_context` 机制提供，不在动态 prompt 中重复拼接。

### 2. 注入决策上下文

主 Agent 获得三类信息：

```text
稳定规则：system instructions
当前 Agent 能力：additional_input 中的 <available_agents>
当前任务上下文：prompt 中的 userinfo、extra_info、user_input
```

可用 Agent 列表按当前 session 的 `_session_agents` 构造，并在每轮重新注入，避免 Agent 上下线或权限变化后继续使用旧快照。

### 3. 生成计划

主 Agent 按规则：

1. 识别用户真正的任务对象；
2. 为每个子任务列出所有能力匹配的候选 Agent；
3. 将无依赖步骤放在同一轮调用中，以便并行；
4. 为有依赖的步骤写入 `depends_on`；
5. 先调用 `task_update_plan_tool`，再调用 `task_execute_tool`。

计划是完整快照，而不是 patch。后续调整时需要带回已完成步骤，避免前端和服务端丢失计划全貌。

### 4. 服务端校验和解析计划

```text
LLM steps
  -> Pydantic 字段校验
  -> step_id 去重
  -> candidate Agent 可用性检查
  -> scope 优先级解析
  -> depends_on 引用检查
  -> 同 Agent 连续步骤检查
  -> 状态迁移检查
  -> 写入 task_toolkit_state
  -> PlanUpdatedEvent
```

服务端把 `candidate_agent_ids` 解析为最终 `agent_id`：

```text
用户专属 > 项目专属 > public
```

注意：这是权限/作用域优先级，不是语义能力评分。候选列表本身由模型根据描述排序，服务端只在候选中选择当前作用域更高的 Agent。

### 5. 执行和反馈

主 Agent 调用 `task_execute_tool`：

```text
step_id + instruction
  -> 找到已解析 agent_id
  -> 执行本地/远程 Agent
  -> 得到 NodeResult
  -> 写 succeeded/failed/timeout/cancelled
  -> 保存 result_ref + summary
  -> 返回状态摘要给主 Agent
```

如果摘要不足，主 Agent 调用 `task_get_result_tool` 按步骤读取受限长度的详细结果。

### 6. 动态调整计划

结果回到主 Agent 后，主 Agent 可以：

- 继续执行下一个 pending 步骤；
- 将 failed 步骤改为 retry；
- 将 timeout 步骤跳过并插入替代步骤；
- 更新后续步骤依赖；
- 补充新的查询步骤；
- 发现没有必要的步骤后标记 skipped；
- 所有必要步骤完成后停止调用工具并汇总回答。

## Runtime Channel Map

| 信息 | 来源 | 通道 | 模型/运行时生效位置 | 保护机制 | 可能丢失/失真 |
|---|---|---|---|---|---|
| 用户目标 | HTTP/会话输入 | `TaskContext -> prompt` | 模型可见 `<user_input>` | 输入模型校验、guardrail | 非文本输入需转为 URI/元信息 |
| 历史对话 | Agno session | history context | 模型可见历史消息 | `add_history_to_context`、历史轮数限制 | 压缩、轮数限制或 session 读取失败 |
| Agent 能力 | AgentStore/session | `_session_agents -> additional_input` | 模型可见 `<available_agents>` | 可见性、ENABLED 过滤 | XML 描述不完整、列表变化 |
| 用户资源 | Workflow extra data | `_session_extra_data -> prompt hint` | 模型可见 `<extra_info>` | 只渲染名称/提示，不直接暴露内容 | 附件内容不在该层读取 |
| 用户纠错记忆 | session/user memory | prompt XML | 模型可见参考信息 | 明确当前事实优先 | 记忆错误会影响选择 |
| 计划 | LLM tool call | `task_toolkit_state` | 工具和前端事件可见 | schema、状态机、完整快照 | 上下文压缩后需重放/读取 |
| 子任务结果 | 执行层 | result record + summary | 主 Agent 按摘要或工具读取 | 字符上限、result_ref | 摘要截断损失语义 |
| 规划规则 | 稳定 instructions | system prompt | 模型决策边界 | 固定 prompt、工具契约 | 模型仍可能误解规则 |

### 重要区别：模型可见 vs 运行时有效

Agent 列表进入 prompt 后只是“模型可见”，真正能否执行还要经过：

```text
candidate_agent_ids
  -> session_state 白名单
  -> scope 解析
  -> task_execute_tool 再次读取 AgentInfo
  -> 执行层调用
```

因此模型看到某个 Agent，不代表它一定能成功执行；运行时白名单才是实际权限边界。

## Mechanism Interrogation

### 1. Prompt 编译：稳定规则 + 动态上下文

**问题压力：** Agent 需要当前 Agent 列表和用户资源，但这些内容变化频繁，全部放入稳定 system prompt 会降低缓存稳定性并造成上下文波动。

**核心思想：** 把不变的编排规范留在 system instructions，把本轮变化的信息放入动态 prompt 和独立 `additional_input`。

**触发：** 每轮 `LoopOrchestrationAgent.arun`。

**决策标准：** 信息是否稳定、是否属于当前请求上下文、是否需要模型直接看到。

**第一性目标 vs 实现代理：**

- 第一性目标：让模型获得完成当前任务所需的完整且可信上下文；
- 实现代理：把 Agent 列表独立成 system message，用 XML 和名称提示表达能力。

**状态变化：** 设置 `self.additional_input`，构造 prompt，Agno 再合并历史消息。

**可见输出：** 模型看到稳定规则、用户输入、用户资源和 Agent 快照；对外 SSE 会清除 `additional_input`，避免内部信息泄露。

**不变量：** 当前 Agent 列表不能被旧会话快照静默替代；内部 system message 不得回传给用户。

**关键代码：** `LoopOrchestrationAgent.arun`、`build_orchestration_prompt_for_agent`、`_remove_internal_event_context`。

**批判：** XML 和独立消息改善了边界与缓存，但不等于模型真正理解 Agent 能力；描述质量仍是选择质量的主要瓶颈。

### 2. 候选 Agent 解析

**问题压力：** 模型知道能力匹配关系，但最终 Agent 选择必须受用户/项目/public 可见范围约束。

**核心思想：** 模型提交候选列表，服务端按作用域优先级解析最终 Agent。

**触发：** `task_update_plan_tool` 校验计划时。

**决策标准：** 候选是否在 `_session_agents`，以及 Agent 的用户/项目/public scope。

**第一性目标 vs 实现代理：**

- 第一性目标：在满足能力的前提下选出最适合当前用户的执行者；
- 实现代理：按 scope 优先级选择候选列表中第一个最高作用域 Agent。

**状态变化：** `TaskPlanStepInput` 转为带 `agent_id` 的 `TaskPlanStep`，写入 `plan_steps`。

**可见输出：** PlanUpdatedEvent 包含最终计划和执行步骤状态。

**不变量：** 不执行模型编造、当前用户不可见或已下线的 Agent。

**关键代码：** `TaskToolkit._resolve_agent_from_candidates`、`_validate_plan_steps`、`filter_agents_by_visibility`。

**批判：** 该机制解决权限和可用性，不解决候选 Agent 的语义排序质量；如果模型遗漏了真正适合的候选，服务端不会自动全局搜索替代者。

### 3. 计划完整快照与状态校验

**问题压力：** 多轮 loop 中计划会变化，模型可能只提交局部修改、重置已完成步骤或制造非法依赖。

**核心思想：** 每次提交完整计划快照，由服务端验证结构和状态迁移。

**触发：** 创建计划或调整计划时调用 `task_update_plan_tool`。

**决策标准：** `step_id` 唯一性、候选可用性、依赖引用、同 Agent 连续链、当前状态和目标状态。

**状态变化：** 更新 `task_toolkit_state.plan_steps/plan_goal`，并 yield `PlanUpdatedEvent`。

**可见输出：** 前端获得完整计划；主 Agent 获得最新状态摘要。

**不变量：** succeeded/cancelled 不被重置；timeout 不被直接 retry；计划依赖引用已存在。

**关键代码：** `TaskPlanStepInput`、`_validate_plan_steps`、`_validate_status_transitions`、`task_update_plan_tool`。

**批判：** 完整快照易于重放和展示，但每次计划调整 token 成本较高；校验的是结构合法，不等于计划逻辑正确。

### 4. 结果摘要和按需读取

**问题压力：** 每个子任务的完整结果持续塞回主 Agent 会造成上下文和 token 成本膨胀。

**核心思想：** 默认返回短摘要和引用，需要时通过工具读取指定步骤的详细结果。

**触发：** `task_execute_tool` 完成子任务；主 Agent 判断摘要不足时调用 `task_get_result_tool`。

**决策标准：** 字符上限和主 Agent 的信息需求，而不是语义重要性评分。

**状态变化：** 保存 result record、summary、result_ref 和原始结果；按需读取时不修改计划状态。

**可见输出：** 默认摘要进入下一轮模型上下文，详细结果仅在显式工具调用后进入。

**不变量：** 主 Agent 上下文不会因单个子任务结果无限增长。

**关键代码：** `_MAX_RESULT_CHARS`、`_store_step_result`、`task_get_result_tool`。

**批判：** 它优化了长度代理指标，不保证摘要保留真正关键事实；结构化 JSON 被字符截断时尤其危险。

## Algorithms

### Intent-to-plan compilation

- Problem：自然语言目标缺少执行结构。
- Main idea：由主 Agent 依据稳定规则和动态 Agent 上下文生成 goal、steps、candidates、dependencies。
- Priority：primary
- Trigger：用户任务需要委派时。
- Decision criteria：任务对象、能力匹配、依赖关系、是否可并行、是否需要 HITL。
- Input：TaskContext、历史、Agent XML、extra_info、user memories。
- Output：TaskPlanStepInput 完整快照。
- Visible output：模型 tool call、PlanUpdatedEvent、前端计划。
- State written：`task_toolkit_state.plan_goal/plan_steps`。
- Invariant：执行前必须有合法计划。
- Failure：任务对象误判、步骤过度拆分、遗漏依赖、候选 Agent 选错。
- Key files/functions：`loop_orchestration_agent.py`、`task_update_plan_tool`。

### Scope-priority candidate resolution

- Problem：候选 Agent 可能同时属于 public、项目或用户范围。
- Main idea：从候选列表中选择当前用户作用域最高的 Agent。
- Priority：primary
- Trigger：计划校验阶段。
- Decision criteria：用户专属 > 项目专属 > public。
- Input：candidate_agent_ids、`_session_agents`、project、user_email。
- Output：最终 `agent_id`。
- Visible output：服务端保存的计划和 PlanUpdatedEvent。
- State written：每个 step 的 `agent_id`。
- Invariant：不可调用不可见或不存在的 Agent。
- Failure：候选遗漏、scope 数据过期、Agent 描述和实际能力不一致。
- Key files/functions：`_resolve_agent_from_candidates`、`filter_agents_by_visibility`。

### Plan state transition validation

- Problem：LLM 可能重置终态或提交不一致计划。
- Main idea：对完整快照与当前计划做状态迁移校验。
- Priority：primary
- Trigger：`task_update_plan_tool` 每次提交。
- Decision criteria：current status、incoming status、step 是否新建、依赖是否存在。
- Input：当前 `plan_steps`、新 steps。
- Output：接受并写入，或参数校验失败。
- Visible output：PlanUpdatedEvent 或 `[参数校验失败]`。
- State written：合法时更新 toolkit state，非法时不更新。
- Invariant：succeeded/cancelled 不可重置，timeout 不直接 retry。
- Failure：合法结构但语义错误、计划全量传输成本高。
- Key files/functions：`_validate_status_transitions`、`task_update_plan_tool`。

### Result compaction and retrieval

- Problem：结果过长导致 loop 上下文膨胀。
- Main idea：短摘要默认进入上下文，详细结果按 step_id 按需读取。
- Priority：secondary
- Trigger：子任务完成或模型显式读取。
- Decision criteria：字符数上限和显式读取请求。
- Input：NodeResult、原始结果、max_chars。
- Output：summary、result_ref 或受限 detail。
- Visible output：下一轮模型上下文中的摘要/详情。
- State written：`step_results`。
- Invariant：上下文增长受控。
- Failure：截断损失关键事实、result_ref 状态与 session 不一致。
- Key files/functions：`_store_step_result`、`task_get_result_tool`。

## 一个关键边界：`depends_on` 不是完整 DAG 调度器

计划模型支持 `depends_on`，Prompt 也要求模型为有依赖的步骤填写它。但从当前 `TaskToolkit` 的校验和执行路径看，主要保证是：

- 依赖 ID 必须存在；
- 模型应该遵守依赖关系；
- 主 Agent 根据结果决定何时调用下一步。

当前执行工具的核心校验是步骤状态 `pending/retry`、Agent 存在和 instruction 非空，并没有看到一个独立调度器根据 `depends_on` 自动阻塞或释放节点。因此它更准确地说是：

> LLM 驱动的计划依赖约束，而不是代码驱动的严格 DAG 执行引擎。

这带来灵活性，但也意味着依赖正确性部分依赖模型行为和 Prompt 约束。

## System Design

## Invariants

- 主 Agent 需要委派时必须先创建计划；
- 每个计划步骤必须有唯一 `step_id`；
- 每个步骤必须提供能力匹配的候选 Agent；
- 最终执行 Agent 必须来自当前 session 白名单；
- succeeded/cancelled 不可被计划工具重置；
- timeout 不能直接变成 retry；
- 执行终态由 `task_execute_tool` 写入，而不是由模型伪造；
- 计划结构变化使用完整计划工具，单纯状态变化使用单步状态工具；
- 子任务详细结果默认不重复注入主 Agent 上下文。

## Boundaries

意图与规划层负责：

- 识别用户任务对象和目标；
- 判断是否需要委派；
- 选择能力候选；
- 生成步骤、依赖和验收要求；
- 根据执行结果调整计划。

它不负责：

- Agent 的最终权限认证；
- 子任务内部业务逻辑；
- 远程 HTTP 重试和取消；
- 结果事实正确性的最终证明；
- 严格的 DAG 调度和资源配额调度。

## Tradeoffs

### 为什么让模型提供候选列表，而不是直接传 `agent_id`

模型负责表达能力匹配，服务端负责按用户/项目/public scope 解析最终 Agent。这样能避免模型绕过可见性规则，也允许同一任务存在多个候选执行者。

代价是模型候选排序仍然影响选择；服务端没有执行复杂的语义能力匹配算法。

### 为什么计划管理和执行分成两个工具

计划调整、状态读取和实际执行是不同动作。拆开后可以只调整计划而不执行，也可以在上下文压缩后读取计划，而不用重新提交执行。

代价是模型需要遵守更多工具契约，工具调用轮次可能增加。

### 为什么使用完整计划快照

完整快照便于前端展示、session 恢复和状态校验，也避免服务端猜测 patch 语义。

代价是每次调整都需要重复传递已完成步骤，增加 token 和模型输出负担。

### 为什么不把规划做成独立 Planner 服务

当前任务需要根据实时结果动态调整，Agentic Loop 可以让规划和执行交替发生，不需要在执行前一次性决定全部路径。

代价是运行路径不完全可预测，计划质量、停止条件和调用成本依赖模型。

## Code Implementation Map

### 主 Agent 行为规则

- 文件：`src/agents/loop_orchestration_agent.py`
- 重点：`_INSTRUCTIONS_BASE`、`_build_instructions`、`LoopOrchestrationAgent.arun`。
- 先读：Agent 选择规则、计划规则、失败规则、并行指导。
- 暂时跳过：模型 provider 细节和普通工具实现。

### Prompt 构造

- 文件：`src/agents/loop_orchestration_agent.py`、`src/workflow/prompts/orchestration.py`
- 重点：`build_orchestration_prompt_for_agent`、`build_available_agents_message`、`_render_extra_info_xml`。
- 先读：稳定 instructions 与动态上下文的分工。

### Agent 可见性

- 文件：`src/workflow/agent_filter.py`
- 重点：`filter_agents_by_visibility`、`extract_project_name`、`extract_user_identifier`。
- 先读：过滤条件、排序和同 ID 覆盖规则。

### 计划工具

- 文件：`src/tools/task_tools.py`
- 重点：`TaskPlanStepInput`、`_validate_plan_steps`、`_validate_status_transitions`、`task_update_plan_tool`。
- 先读：输入模型、服务端解析和状态约束。

### 结果反馈

- 文件：`src/tools/task_tools.py`
- 重点：`task_execute_tool`、`task_get_plan_tool`、`task_get_result_tool`、`_store_step_result`。
- 先读：结果如何从执行层回到主 Agent，以及摘要边界。

## Failure and Cost Model

### 常见失败

- 用户目标被错误理解；
- Agent description 不准确导致候选错误；
- 候选列表没有包含真正可用 Agent；
- 计划依赖写错或模型提前执行依赖步骤；
- 计划工具提交状态非法；
- 子任务失败后模型没有安排补救；
- 结果摘要截断关键事实；
- 上下文压缩后模型忘记计划，需要调用恢复工具；
- 工具调用达到 `tool_call_limit=100` 后仍未完成。

### 降级行为

- 没有合适 Agent 时主 Agent 可以直接回答或请求用户补充；
- Agent 不可用时计划校验失败，不进入执行；
- failed 可以 retry 或 skipped；
- timeout 只能 skipped 或更换步骤；
- 详细结果不足时按 step_id 读取；
- 计划在新一轮开始时通过 `task_toolkit_state` 重放给前端。

### 成本

- 每轮 LLM 规划、工具调用和结果观察都会产生 token 和延迟；
- 完整计划快照会重复传输已完成步骤；
- Agent XML 列表随 Agent 数量增长，增加 prompt 输入；
- 结果摘要降低成本，但可能增加额外的 `task_get_result_tool` 调用；
- Agent 描述、Prompt 规则和状态契约需要持续维护；
- Agentic Loop 难以像固定 DAG 一样准确预估最坏执行成本。

## Evolution

### 当前稳定设计

- 稳定编排规则与动态 Agent 列表分离；
- 模型提交候选 Agent，服务端解析最终 Agent；
- 计划、执行、读取结果拆为不同工具；
- 执行终态由代码管理；
- 结果摘要和详细结果按需读取。

### 当前过渡或薄弱部分

- `depends_on` 当前主要是模型遵守的计划语义，不是严格调度约束；
- Agent 选择主要依赖候选列表和 scope 优先级，没有独立能力评分/健康评分；
- 计划完整快照会产生重复 token；
- 结果摘要使用字符截断，不理解 JSON 或领域结构；
- 主 Agent 可能因为上下文压缩、错误结果或模型误判而重复规划。

### 演进方向

#### 1. 意图结构化与规划分层

先将用户目标转换为结构化意图对象，再由 Planner 生成计划：

```text
用户输入
  -> Intent {object, goal, constraints, missing_inputs}
  -> Candidate capabilities
  -> Plan {steps, dependencies, acceptance criteria}
```

这样可以把“用户到底要什么”和“如何执行”分开评估，减少计划直接承担意图理解错误。

#### 2. 引入代码驱动的依赖调度

如果业务需要严格 DAG 语义，应由调度器根据 `depends_on` 判断节点是否 ready，而不是只依赖 LLM：

```text
depends_on
  -> dependency status check
  -> ready queue
  -> execute
  -> unlock downstream steps
```

Agentic Loop 仍可负责动态增删计划，但执行门控由代码保证。

#### 3. Agent 能力和健康度评分

在 scope 过滤之外增加：能力标签、输入输出 schema、在线状态、历史成功率、延迟、成本和负载等评分维度。

当前 scope 优先级解决的是“谁有资格”，未来评分解决的是“谁更适合”。

#### 4. 结构化结果摘要

根据结果 schema 生成摘要，而不是简单按字符截断：

```text
完整结果
  -> schema-aware summary
  -> key facts / evidence / warnings / references
  -> 主 Agent 上下文
```

#### 5. 计划验证与评测

增加对计划质量的离线评测：任务覆盖率、Agent 选择准确率、依赖正确率、重复调用率、平均工具轮次、token 成本和最终完成率。

## Synthesis

意图与规划层的本质是：**把自然语言目标转换成受约束的协作计划，并让执行结果反过来改变计划。**

它让上层用户可以只描述目标，让执行层只接受明确步骤，让权限和状态约束不完全依赖模型记忆。

当前最大代价是：规划质量和执行顺序仍有一部分依赖 LLM，`depends_on` 还不是严格调度器，Agent 能力选择也主要依赖描述和候选排序。

下一步适合深入：`TaskToolkit` 的计划状态机与 `depends_on` 执行语义，或者主 Agent 的 Prompt/上下文工程。

