# LoopOrchestrationAgent 设计说明

## 1. 定位

`LoopOrchestrationAgent` 是多智能体系统中的主编排 Agent，位于 `src/agents/loop_orchestration_agent.py`。

它不负责某一个具体业务领域，而是负责将用户的复杂目标转化为可执行的子任务，选择合适的子 Agent，观察执行结果并动态调整计划，最后汇总结果。

核心执行模式是 Agentic Loop：

```text
理解目标 → 制定计划 → 调用工具/子 Agent → 观察结果
                         ↑                 ↓
                         └── 动态调整计划 ←┘
```

典型调用链如下：

```text
用户请求
  ↓
OrchestrationWorkflow
  ↓
DigitalWorkerProxyAgent
  ↓
LoopOrchestrationAgent.arun()
  ↓
Agno Agentic Loop
  ↓
TaskToolkit
  ├── 更新计划
  ├── 执行子 Agent
  ├── 获取计划和结果
  └── 根据结果继续决策
```

## 2. 解决的问题

### 2.1 复杂目标的任务拆分

用户通常只描述最终目标，例如“查询需求、分析代码、执行测试并生成报告”。这类目标包含多个专业环节，不能依赖一个具体 Agent 一次完成。

主 Agent 负责识别所需能力，并将任务拆分给搜索、代码分析、测试或报告类 Agent。

### 2.2 任务依赖和并行

不同步骤可能存在依赖关系。例如：

```text
查询需求单 → 定位代码 → 执行测试 → 生成报告
```

计划步骤通过 `depends_on` 表达前置依赖。没有依赖的步骤可以在同一轮并行调用。

### 2.3 动态调整

执行结果可能改变原计划，例如：

- 子 Agent 返回信息不足，需要补充查询；
- 某个 Agent 执行失败，需要更换 Agent；
- 任务超时，需要跳过并创建替代步骤；
- 用户需要补充必要参数。

Agentic Loop 可以在每次工具调用后重新判断，而不是要求一开始就生成完整且不可变的流程。

### 2.4 长任务的暂停、恢复和多轮对话

实现支持多轮会话、人工介入（HITL）、checkpoint 恢复、计划状态持久化和 SSE 事件推送。

## 3. 类结构和初始化

类继承自 Agno 的 `Agent`：

```python
class LoopOrchestrationAgent(Agent):
```

构造函数主要完成以下工作：

1. 保存 `agent_store`，用于读取可用子 Agent；
2. 创建 `TaskToolkit`；
3. 配置数据库和多轮历史；
4. 配置上下文压缩；
5. 注册任务、HITL、工作区、沙箱、平台知识和设备管理工具；
6. 配置 checkpoint 和工具调用上限。

主要配置包括：

```python
add_history_to_context=True
num_history_runs=10
checkpoint="tool-batch"
tool_call_limit=100
compress_tool_results=True
```

Agent 级别没有启用自动重试（`retries=0`）。原因是 Agno 的 continue 重试可能复用并原地修改同一个 `RunOutput`，在 HITL 或工具恢复场景下容易造成工具消息和工具状态不一致。模型层的受控重试负责处理瞬态模型或网关错误。

## 4. Prompt 设计

Prompt 分为稳定层和运行时层。

### 4.1 稳定层

`_INSTRUCTIONS_BASE` 定义长期稳定的编排规则，包括：

- 主 Agent 的职责；
- 什么时候应该委派；
- 如何识别任务对象；
- 如何选择 Agent；
- 如何拆分和更新计划；
- 如何编写自包含的子 Agent 指令；
- 如何处理失败、超时和取消；
- 如何使用人工介入工具；
- 什么时候停止调用工具并输出最终答案。

`_build_instructions()` 只拼接这些稳定规则，不内联 Agent 列表。这样 Agent 列表变化不会导致 system prompt 频繁变化，有利于 Prompt/KV Cache 命中。

### 4.2 运行时 Agent 快照

每次 `arun()` 执行时，从 `session_state["_session_agents"]` 获取当前会话可见的 Agent，并通过 `additional_input` 注入一个独立的 system message：

```xml
<available_agents>
  <agent>
    <agent_id>search_agent</agent_id>
    <description>负责搜索需求和业务数据</description>
    <visible_scope>public</visible_scope>
  </agent>
</available_agents>
```

这样可以保证：

- 只使用本轮实际可见的 Agent；
- 支持 public、项目级和用户级 Agent；
- 会话中 Agent 上线或下线后可以使用最新快照；
- LLM 不能编造 Agent ID。

由于 `additional_input` 中包含内部 system message，事件向 SSE 输出前会由 `_remove_internal_event_context()` 清理，防止内部上下文暴露给前端。

## 5. `arun()` 执行流程

`arun()` 是该类的核心入口，主要流程如下：

### 5.1 解析任务上下文

`_parse_task_context()` 支持以下输入：

- `TaskContext` 实例；
- 其他 Pydantic 模型；
- `dict`；
- 普通字符串。

字符串会被包装成包含 `trace_id`、`request_id`、`session_id`、`user_id` 和文本输入的 `TaskContext`，使上层不同输入形式在工具层统一。

### 5.2 加载运行时 Skill

如果 session state 中存在 `_task_skill_dir`，则加载本地 Skill；如果配置了 sandbox，则通过 `SandboxSkillsLoader` 从 sandbox 加载 Skill。

### 5.3 注入运行态

将 `trace_id` 等信息写入 `session_state`，供 TaskToolkit 从 Agno 的 `RunContext` 中读取。同时注入当前 Agent 快照。

### 5.4 构建动态用户 Prompt

`build_orchestration_prompt_for_agent()` 负责拼接：

- 用户项目和邮箱；
- 用户原始请求；
- 用户历史纠错记忆；
- 附件和知识库等额外资源。

用户输入和外部资源会进行 XML 转义，避免特殊字符破坏 Prompt 结构。

### 5.5 进入 Agno Agentic Loop

最终调用 `super().arun()`。之后逐个转发事件，并在必要时重放历史计划、清理内部字段。

## 6. TaskToolkit 与计划执行

TaskToolkit 是主 Agent 和子 Agent 之间的执行边界，注册了以下工具：

|工具|作用|
|---|---|
|`task_update_plan_tool`|创建或调整完整执行计划|
|`task_update_step_status_tool`|更新已有步骤的可管理状态|
|`task_execute_tool`|执行计划中的一个子任务|
|`task_get_plan_tool`|读取当前计划|
|`task_get_result_tool`|按步骤读取详细结果|

### 6.1 先计划，后执行

系统指令要求主 Agent 先调用 `task_update_plan_tool`，再调用 `task_execute_tool`。计划步骤包含：

```python
{
    "step_id": "step_1",
    "description": "查询需求单内容",
    "candidate_agent_ids": ["search_agent"],
    "status": "pending",
    "depends_on": [],
}
```

LLM 只提交候选 Agent，最终 `agent_id` 由服务端根据可见范围和优先级解析：

```text
用户专属 Agent > 项目专属 Agent > public Agent
```

这将能力判断交给 LLM，将权限和最终选择交给服务端。

### 6.2 计划使用完整快照

`task_update_plan_tool` 每次接收完整步骤列表，而不是局部 patch。调整计划时需要同时保留已完成步骤，并同步修改下游步骤的 `depends_on`。

### 6.3 状态机

计划状态大致如下：

```text
pending / retry
       │
       └── task_execute_tool
             ├── succeeded
             ├── failed
             ├── timeout
             └── cancelled
```

失败任务可以改成 `retry` 或 `skipped`。超时任务不能直接重试，应跳过或创建替代步骤。`succeeded` 和 `cancelled` 不允许被重置。

### 6.4 子 Agent 指令

`task_execute_tool` 接收 `step_id` 和 `instruction`。指令必须自包含，明确：

- 用户目标；
- 当前步骤目标；
- 必要输入和背景；
- 约束；
- 期望输出；
- 验收标准。

子 Agent 看不到主会话的完整上下文，因此不能依赖主 Agent 未写入指令的隐式信息。

### 6.5 结果和事件

TaskToolkit 通过异步生成器产生事件，实时通知前端：

```text
PlanUpdatedEvent
PlanStepStartedEvent
PlanStepCompletedEvent
```

执行结果默认只返回摘要，详细结果通过 `task_get_result_tool` 按需读取，以控制后续上下文和 Token 成本。

远程子 Agent 执行完成时会提取真实的 remote run ID，用于事件关联和父子任务取消传播。

## 7. 计划重放

TaskToolkit 的计划状态保存在 session state 中。多轮会话的下一轮开始时，主 Agent 不一定会再次调用计划工具，但前端仍然需要显示上一轮计划。

因此 `arun()` 会在收到 `RunStarted` 后的起始窗口中调用：

```python
TaskToolkit.build_replay_plan_updated_event(...)
```

重新生成一个 `PlanUpdatedEvent`。该窗口只执行一次，避免和本轮新计划产生的真实事件重复。

## 8. HITL 与 checkpoint

### 8.1 HITL

人工介入使用 Agno 原生 paused run 机制。`_get_paused_run()` 从 `AgentSession.runs` 中倒序查找 `RunStatus.paused`，不需要额外维护自定义暂停标记。

### 8.2 Checkpoint Continue

`clone_for_checkpoint_continue()` 为某个 checkpoint 分支创建独立 Agent，并关闭历史自动拼接：

```python
clone.overwrite_db_session_state = True
clone.add_history_to_context = False
clone.num_history_runs = 0
```

`acontinue_from_checkpoint()` 基于已有 `RunOutput` 调用 Agno 的 `acontinue_run()`，从已有执行状态继续模型循环，同时重新注入当前可见 Agent 列表。

## 9. 上下文成本控制

实现包含多层 Token 控制：

1. 稳定 Prompt 与动态 Agent 列表分离，提升缓存命中；
2. 使用 `CompressionManager` 压缩工具结果；
3. 子任务默认只携带结果摘要，详细结果按需读取；
4. 只保留最近 10 轮会话历史；
5. 计划状态单独存储，不要求每轮都将完整结果放入上下文；
6. 不使用固定 `output_schema`，让最终答案保持自然语言灵活性。

## 10. 与 DAG 模式的区别

|维度|Loop 模式|DAG 模式|
|---|---|---|
|决策时机|边执行边决策|先生成完整 DAG|
|计划变化|执行中可动态调整|结构相对固定|
|适用任务|不确定、需要观察结果|依赖清晰、流程稳定|
|并行控制|LLM 根据依赖调用工具|Workflow/DAG 调度|
|失败处理|LLM 观察后重新规划|按工作流错误策略处理|
|主要角色|动态项目经理|流程执行引擎|

Loop 模式的灵活性更高，但可能产生更多 LLM 循环；DAG 模式的执行边界更确定，适合结构稳定的任务。

## 11. 设计边界总结

### LLM 负责

- 理解用户意图；
- 判断能力匹配；
- 拆解任务；
- 编写子任务指令；
- 观察结果并调整计划；
- 汇总最终答案。

### 服务端负责

- Agent 可见性和权限；
- Agent ID 校验；
- 计划状态机；
- 子 Agent 实际调用；
- 超时、取消和远程 run 管理；
- 事件推送；
- session 和 checkpoint 持久化。

这种边界将非确定性的认知决策交给 LLM，将权限、状态和执行可靠性留在服务端，形成可扩展的多智能体编排架构。

## 12. 扩展性与智能化演进方向

当前实现已经具备动态规划、子 Agent 调用、状态管理、远程执行和恢复能力。后续如果希望支撑更多 Agent、更复杂的任务和更高质量的自动决策，建议沿着“编排内核平台化、决策数据化、执行可靠化”的方向演进。

### 12.1 将编排策略从 Prompt 中逐步抽离

目前很多编排规则位于 `_INSTRUCTIONS_BASE`，例如：

- 什么时候应该委派；
- 如何拆分步骤；
- 如何处理失败和超时；
- 什么时候需要重新规划。

短期内 Prompt 迭代成本低，但随着规则增多，容易出现规则冲突、Prompt 过长和版本难以管理的问题。

可以将规则拆成版本化的策略模块：

```text
OrchestrationPolicy
  ├── AgentSelectionPolicy
  ├── PlanningPolicy
  ├── RetryPolicy
  ├── ParallelismPolicy
  ├── EscalationPolicy
  └── ResponsePolicy
```

Prompt 负责告诉模型“有哪些策略以及如何使用”，服务端负责执行可验证的约束。例如依赖检查、权限检查、超时不可重试、同一 Agent 连续步骤合并等，都应尽可能由策略引擎或工具层强制执行，而不是只依赖模型遵守 Prompt。

这样可以实现：

- 不同项目使用不同编排策略；
- 策略独立灰度和回滚；
- 通过配置切换不同模型和规划深度；
- 对策略版本进行效果对比。

### 12.2 建立标准化 Agent 能力目录

当前 Agent 主要通过 `agent_id`、`description` 和 `visible_scope` 参与选择。随着 Agent 数量增长，仅靠自然语言 description 可能导致能力重叠、选择不稳定和候选列表过长。

建议扩展 Agent 元数据：

```python
class AgentCapability(BaseModel):
    domain: str
    actions: list[str]
    input_schema: dict
    output_schema: dict
    required_resources: list[str]
    estimated_cost: float | None = None
    estimated_latency: float | None = None
    quality_score: float | None = None
```

Agent 选择可以变成多阶段流程：

```text
权限过滤
  → 能力匹配
  → 输入/输出兼容性检查
  → 成本和时延排序
  → 历史成功率排序
  → LLM 最终决策
```

其中权限过滤和输入校验必须由服务端完成，LLM 只在合法候选集合中做语义判断。

### 12.3 将计划模型升级为可验证的执行图

目前计划主要由 `step_id`、`description`、`candidate_agent_ids`、`status` 和 `depends_on` 构成。后续可以增加：

- 输入引用：引用某个前序步骤的结构化输出；
- 输出契约：规定步骤必须返回哪些字段；
- 资源需求：文件、知识库、设备、凭证等；
- 超时和取消策略；
- 幂等键；
- 补偿动作；
- 成功和失败判定条件。

例如：

```text
step_2
  input: ${step_1.result.issue_id}
  output_schema: TestCaseReport
  depends_on: [step_1]
  timeout: 10m
  retry_policy: retry_with_fallback_agent
```

这样计划不只是给 LLM 看的描述，也成为可由执行引擎验证的中间表示（IR）。未来可以支持：

- 计划静态检查；
- 自动发现可并行步骤；
- 结构化结果自动注入下游；
- 不同执行引擎复用同一计划；
- 计划持久化、回放和版本比较。

### 12.4 将 LLM 规划和确定性调度分层

建议形成两层架构：

```text
Planning Layer
  LLM 负责理解目标、生成和修订计划
          ↓
Execution Layer
  调度器负责依赖、并发、重试、超时、取消和资源锁
```

当前 Agentic Loop 中，LLM 既参与规划，也通过工具逐步驱动执行。任务规模增大后，可以让 LLM 只提交“计划变更”，由独立调度器决定哪些步骤现在可以运行。

这样可以降低以下风险：

- LLM 重复执行同一个步骤；
- LLM 忽略 `depends_on`；
- 并发调用过多导致资源争抢；
- 主 Agent 被大量执行事件占据上下文；
- 长时间任务阻塞主模型循环。

对于简单任务仍可以保留当前轻量模式；对于长任务则切换到调度器模式，形成分层执行策略。

### 12.5 引入事件溯源和统一运行状态

目前计划状态保存在 session state，前端通过计划事件和执行事件获得状态。后续可以将任务运行抽象为统一的 `RunGraph`：

```text
WorkflowRun
  └── OrchestrationRun
        ├── PlanVersion
        ├── StepRun
        ├── AgentRun
        └── RemoteRun
```

每次计划变化、步骤状态变化、远程 run 建立或取消，都记录为不可变事件。当前状态由事件投影得到。

收益包括：

- 运行过程可完整回放；
- SSE 断线后可从事件序号继续；
- 父子 run 关系更清晰；
- 取消、重试和恢复更容易审计；
- 可以重建前端计划视图；
- 可以基于历史运行数据做质量分析。

这也能进一步统一本地子 Agent、远程智能体和数字员工的运行模型。

### 12.6 构建上下文工程层

随着任务复杂度提升，不应把所有历史、工具结果和 Agent 描述都交给模型。可以增加独立的上下文编排层，负责按当前决策需要组装上下文：

```text
Context Builder
  ├── 用户目标摘要
  ├── 当前计划摘要
  ├── 可执行步骤
  ├── 相关前序结果
  ├── 失败原因
  ├── 必要历史对话
  └── 当前可用能力
```

建议采用“摘要 + 引用 + 按需读取”的模式：

- 默认只提供结果摘要；
- 大结果存储为 `result_ref`；
- 只有当前步骤依赖的结果才注入；
- 上下文压缩时保留结构化状态，不只保留自然语言摘要；
- 让模型能够通过工具主动恢复详细信息。

这样可以避免上下文长度随着子任务数量线性增长。

### 12.7 从规则重试发展为基于证据的自适应执行

当前失败处理主要依赖状态和 Prompt 规则。后续可以为每次失败记录结构化原因：

```text
FailureEvidence
  ├── error_type
  ├── failure_stage
  ├── missing_input
  ├── agent_id
  ├── elapsed_time
  ├── partial_output
  └── suggested_recovery
```

系统可以根据失败证据选择恢复动作：

```text
参数缺失       → 请求用户补充
权限不足       → 更换合法 Agent 或终止
数据为空       → 扩大查询条件或更换数据源
模型输出不合格 → 要求修正或更换 Agent
远程超时       → 创建替代步骤
```

长期可以基于历史成功率、成本和时延学习 Agent 选择策略，但必须保留权限和安全边界，不能让统计结果覆盖硬约束。

### 12.8 建立离线评估和回归测试体系

智能化迭代不能只依赖人工观察。建议建立任务数据集，覆盖：

- 单 Agent 简单委派；
- 多步骤依赖；
- 无依赖并行；
- 失败后的补救；
- 超时和取消；
- HITL 暂停恢复；
- Agent 可见性和候选选择；
- 远程 Agent 调用；
- 长结果和上下文压缩。

评估指标可以包括：

|指标|含义|
|---|---|
|任务完成率|是否完成用户目标|
|计划有效率|计划是否存在无效、重复或遗漏步骤|
|Agent 选择准确率|是否选择了能力匹配的 Agent|
|补救成功率|失败后能否恢复任务|
|结果引用正确率|是否使用了正确的前序结果|
|平均 Token 成本|单任务模型消耗|
|平均时延|从开始到最终回答的耗时|
|取消传播成功率|父任务取消后子任务是否都停止|

每次 Prompt、模型、策略或工具变更，都应在固定任务集上进行回归，避免局部优化破坏其他场景。

### 12.9 增强可观测性和决策审计

建议为每次编排记录统一 trace：

```text
trace_id
  ├── model_call
  ├── tool_call
  ├── plan_version
  ├── step_run
  ├── remote_run
  ├── token_usage
  └── final_quality
```

重点记录：

- 模型使用的 Prompt/策略版本；
- 候选 Agent 和最终 Agent；
- 每次计划变更前后的差异；
- 工具调用耗时和结果大小；
- 失败、重试、超时和取消原因；
- 子 Agent 的输入输出引用；
- 最终答案是否通过验收。

这样可以回答“为什么选择这个 Agent”“为什么重新规划”“成本主要花在哪里”等问题，为后续智能优化提供数据基础。

### 12.10 建议的演进优先级

推荐按以下顺序推进：

1. **短期：强化契约和观测**。补充计划输入输出契约、统一错误分类、记录完整 trace，并完善 Agent 能力元数据。
2. **中期：拆分规划和执行**。引入可验证的计划 IR 和确定性调度器，让 LLM 只负责计划和修订。
3. **中期：建设评估闭环**。建立离线任务集、线上指标和 Prompt/模型版本对比。
4. **长期：自适应编排**。基于历史成功率、成本、时延和失败证据优化 Agent 选择、并行度和恢复策略。

演进过程中应始终保留当前 Agentic Loop 作为轻量路径：简单任务直接由主 Agent 完成，结构化长任务再升级到计划调度器。这样可以在扩展能力的同时控制系统复杂度和单任务成本。