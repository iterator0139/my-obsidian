---
tags: [netease, orchestration-agent, execution-adapter, proxy, remote-agent, node-result]
aliases: [Orchestration Agent 执行适配层深度分析]
---

# 执行适配层深度分析

## Layer Judgment

本项目的整体目标是让主编排 Agent 能够协调多个专业数字员工，并将不同执行方式纳入统一的 Workflow、事件和状态体系。

本篇深入执行适配层：它位于计划/编排层和具体 Agent 执行实现之间，负责选择执行路径、准备上下文、适配协议、透传事件、归一化终态和向上层返回统一结果。

## 先用一条完整流程理解执行适配层

直白地说，执行适配层做的是：**把“执行这个步骤”翻译成具体的本地/远程调用，再把各种调用结果翻译回统一的步骤事件和结果对象。**

普通编排步骤的流程是：

```text
TaskToolkit.task_execute_tool
  -> 根据 step_id 找到 agent_id
  -> 构造 instruction 和 TaskContext
  -> DigitalWorker executor
  -> 解析 Agent endpoint 类型
  -> 构造 RemoteAgent / RemoteTeam / RemoteWorkflow
  -> 建立远程事件流
  -> 处理 run_id、HITL、取消、超时和 token metrics
  -> 得到 DigitalWorkerTerminalState
  -> 转换成 NodeResult
  -> task_execute_tool 写入 succeeded/failed/timeout/cancelled
  -> 主 Agent 继续规划
```

顶层 `loop_execute` 还有三条代理路径：

```text
checkpoint restore
  -> 克隆主 Agent
  -> 从 checkpoint 继续

normal orchestration
  -> DigitalWorkerProxyAgent
  -> LoopOrchestrationAgent.arun

direct digital worker
  -> DigitalWorkerProxyAgent
  -> execute_remote_agent_until_terminal
  -> 伪造一个单步骤计划
```

执行适配层的核心不是“统一所有 Agent 的内部实现”，而是统一它们对上层暴露的执行契约：

```text
不同执行方式
  -> 统一事件流
  -> 统一暂停/继续信号
  -> 统一终态
  -> 统一 NodeResult / RunOutput
```

## Core Idea

核心机制是：

> 用 Proxy 选择执行模式，用 executor/runtime 统一远程协议和事件流，用 `NodeResult` 与 `DigitalWorkerTerminalState` 把不同实现归一化。

它解决的真实问题是执行异构性：

- 主编排 Agent 是本地对象；
- 数字员工可能是远程 Agent、Team 或 Workflow；
- endpoint 可能明确或不明确类型；
- 执行可能正常完成、暂停、取消、超时或网络失败；
- 调用方需要继续使用统一的步骤状态和前端事件。

如果没有这一层，`TaskToolkit`、主 Workflow 和每条业务路径都要自己理解 RemoteAgent/Team/Workflow、HTTP timeout、HITL、取消和结果格式，最终会形成多套不一致的远程调用实现。

## Mechanism Priority Map

### Primary mechanisms

#### 1. Proxy 路由选择

- 优先级：primary
- 作用：在 checkpoint restore、normal loop、direct worker 三种执行方式中选择正确路径。
- 核心文件：`src/agents/digital_worker_proxy_agent.py`。

#### 2. 远程执行统一入口

- 优先级：primary
- 作用：统一 endpoint 解析、Remote runnable 构造、事件流、HITL、取消和终态。
- 核心文件：`src/digital_worker/executor.py`、`src/digital_worker/runtime.py`。

#### 3. 终态归一化

- 优先级：primary
- 作用：把 Agno `RunOutput` 或远程 `DigitalWorkerTerminalState` 转为 `NodeResult` 或代理 `RunOutput`。
- 核心文件：`src/tools/task_tools.py`、`src/agents/digital_worker_proxy_agent.py`、`src/schema/result.py`。

### Secondary mechanisms

#### 4. endpoint 类型解析和回退

- 优先级：secondary
- 作用：根据 `/agents/{id}`、`/teams/{id}`、`/workflows/{id}` 选择远程类型；类型未知时按候选尝试。
- 核心文件：`src/digital_worker/resolver.py`、`src/digital_worker/executor.py`。

#### 5. 事件和计划事件适配

- 优先级：secondary
- 作用：把执行层事件转换为 Workflow/前端可理解的 PlanStep、PlanExecutorNode 和状态事件。
- 核心文件：`DigitalWorkerProxyAgent._adapt_plan_events`、`workflow/loop_plan_event_adapter.py`。

#### 6. checkpoint 恢复适配

- 优先级：secondary
- 作用：将持久化 checkpoint 转成新的主 Agent 继续运行上下文。
- 核心文件：`src/utils/workflow_checkpoint.py`、`DigitalWorkerProxyAgent._arun_stream`。

### Supporting mechanisms

- 分阶段 HTTP timeout；
- JWT `auth_token` 注入；
- graceful shutdown 远程任务登记；
- token metrics 透传；
- endpoint 错误消息归一化；
- remote run_id 改写与父子 run 登记；
- direct 路径的合成单步骤计划。

## Layer Problem

执行适配层承受的主要压力是：

| 压力 | 具体问题 |
|---|---|
| 协议异构 | Agent、Team、Workflow 的 endpoint 和事件名不同 |
| 部署异构 | 主 Agent 本地运行，数字员工远程运行 |
| 生命周期异构 | 远程可能 paused、continue、cancel、timeout |
| 结果异构 | `RunOutput`、事件 content、结构化 payload、错误字段格式不同 |
| 事件一致性 | 上层希望看到统一的 step started/completed 和 plan node 事件 |
| 取消传播 | 父 Workflow、proxy run、远程 run 使用不同 run_id |
| 超时语义 | HTTP read timeout、业务 timeout、Agno 没有 timeout status |
| 兼容演进 | endpoint 类型可能缺失，旧 snapshot 可能缺少定位字段 |

## Core Abstractions

### `DigitalWorkerProxyAgent`

- 表示：Workflow 中承载执行的代理 Agent。
- 拥有：运行模式选择、主 Agent/直连 Agent 调用、计划事件适配。
- 不拥有：远程 endpoint 解析的全部细节、远程 HTTP 事件循环的底层实现。
- 相邻抽象：`LoopOrchestrationAgent`、`digital_worker.executor`、Workflow Step。
- 代码：`src/agents/digital_worker_proxy_agent.py:65`。

### `digital_worker.executor`

- 表示：远程数字员工执行的高层统一 API。
- 拥有：候选目标、远程 runnable 构造、远程首次执行和 continue 的入口。
- 不拥有：业务层如何把终态展示给用户。
- 相邻抽象：`digital_worker.runtime`、`AgentInfo`、Proxy/TaskToolkit。
- 代码：`src/digital_worker/executor.py`。

### `digital_worker.runtime`

- 表示：远程 runnable 的事件级运行时。
- 拥有：事件读取、run_id 提取、取消检查、HITL 等待、终态产生、metrics 收集。
- 不拥有：主 Agent 如何规划，也不决定最终计划步骤状态。
- 相邻抽象：Agno RemoteAgent/Team/Workflow、Redis HITL、cancel registry。

### `AgnoRemoteTarget`

- 表示：远程目标类型、base URL 和 remote id。
- 作用：把不稳定的 endpoint 字符串转换为明确的构造参数。
- 代码：`src/digital_worker/resolver.py`、`src/engine/agent_adapter.py`。

### `DigitalWorkerTerminalState`

- 表示：一次远程执行链路的最终状态。
- 状态：`completed`、`error`、`cancelled`、`timeout`。
- 附带：最后事件、累计内容、remote_run_id、延迟、错误和 metrics。
- 作用：隔离远程 runtime 与业务调用方。

### `NodeResult`

- 表示：计划步骤统一业务结果。
- 状态：`SUCCESS`、`FAILED`、`TIMEOUT`、`CANCELLED`。
- 附带：node/agent、payload、错误、延迟、confidence、attempt、metrics。
- 作用：供 `TaskToolkit` 更新计划状态和向主 Agent 返回摘要。

### `RunOutput`

- 表示：Agno Agent/Workflow 层的运行输出。
- 在 direct 路径中，远程 terminal state 会被包装成代理 `RunOutput`，让外层 Agno Step 能识别 completed/error/cancelled/paused。

## Main Flow

### 1. 普通编排步骤

```text
task_execute_tool
  -> _run_native_agent_stream
  -> execute_remote_agent_until_terminal
  -> executor.resolve_remote_targets
  -> resolver.build_remote_runnable
  -> runtime.stream_remote_run
  -> 事件透传
  -> DigitalWorkerTerminalState
  -> _build_terminal_state_result
  -> NodeResult
```

这里的“native agent”名称容易误导：当前实现的 `_run_native_agent_stream` 全程委托给远程数字员工统一执行器，主要职责是把远程终态映射成 `NodeResult`。

### 2. 普通 Loop 主 Agent 路径

```text
Workflow loop_execute
  -> DigitalWorkerProxyAgent._arun_stream
  -> 无 direct 标记、无 restore runtime
  -> LoopOrchestrationAgent.arun
  -> 主 Agent 进行规划和工具调用
  -> _adapt_plan_events
  -> Workflow 事件管道
```

Proxy 在这里不是远程调用代理，而是 Workflow 与主 Agent 之间的适配器。

### 3. Direct 数字员工路径

```text
用户直接指定数字员工
  -> session_state 写入 direct agent info/instruction
  -> Proxy 读取并 pop direct 标记
  -> 合成一个 direct plan
  -> execute_remote_agent_until_terminal
  -> terminal state
  -> RunOutput
  -> PlanStepCompletedEvent
```

direct 模式没有主 Agent 规划，因此 Proxy 合成一个虚拟计划和一个步骤，让前端仍能使用统一的计划展示。

### 4. Checkpoint 恢复路径

```text
checkpoint_restore_runtime
  -> 校验 workflow/session/run 坐标
  -> overlay semantic state
  -> build checkpoint run
  -> clone main agent
  -> acontinue_from_checkpoint
  -> _adapt_plan_events
  -> capture checkpoint events
```

恢复路径不是重新执行原始输入，而是从保存的 Agent run/message 边界继续。

## Runtime Channel Map

| 信息 | 来源 | 通道 | 适配后位置 | 保护机制 | 可能失效 |
|---|---|---|---|---|---|
| 执行指令 | Planner/TaskToolkit | `instruction -> remote arun` | 远程 Agent 输入 | instruction 非空校验 | 指令上下文不完整 |
| Agent 元信息 | session whitelist/AgentStore | `AgentInfo -> target/runnable` | remote runnable | 白名单、scope、endpoint 解析 | endpoint 过期或类型错误 |
| session state | Workflow run context | `session_state -> remote call` | 远程 session/工具环境 | `_workflow_run_id`、real_user_id 透传 | 子路径漏传字段 |
| remote run_id | 远程首个事件 | runtime -> cancel registry | 父子取消和事件改写 | register_child、extract_real_run_id | 首个事件前无法取消远程实例 |
| 远程事件 | Agno Remote runnable | runtime iterator | Workflow/计划/SSE | event name、run_id 改写 | Team/Workflow 事件结构不同 |
| HITL pause | 远程事件/Redis | `DigitalWorkerPauseSignal` | Proxy paused/continue | snapshot、claim、reaper | signal/snapshot 过期 |
| 终态 | runtime | `DigitalWorkerTerminalState` | NodeResult/RunOutput | 明确 status 映射 | timeout/error/cancel 语义错配 |
| token metrics | 远程完成事件 | session_state / terminal metrics | cost step / token log | scope、model 聚合 | 重复记账或异常未落库 |

### 同一个终态的多次转换

远程成功不是直接显示给用户，而是经过：

```text
远程 RunCompleted
  -> DigitalWorkerTerminalState(completed)
  -> NodeResult(SUCCESS)       # 编排工具路径
  或 RunOutput(completed)      # direct proxy 路径
  -> PlanStepCompletedEvent
  -> TaskActivity / 主 Agent 上下文 / 最终回答
```

远程 timeout 也不是 Agno 原生 `RunStatus.timeout`，direct 路径会将其包装为 `RunStatus.error`，再通过内容前缀 `[执行超时]` 识别为计划层的 `timeout`。这是一个典型的跨层语义适配。

## Mechanism Interrogation

### 1. Proxy 三路由

**问题压力：** 同一个 Workflow step 可能承载普通编排、直接数字员工或 checkpoint 恢复。

**核心思想：** 使用 session state 和 ContextVar 中的运行态标记做一次性路由。

**触发：** `DigitalWorkerProxyAgent._arun_stream` 每次被 Workflow step 调用。

**决策标准：**

1. 有 `checkpoint_restore_runtime`：走 checkpoint；
2. 有 `LOOP_DIRECT_AGENT_INFO_KEY`：走 direct；
3. 否则：走普通 Loop Agent。

**第一性目标 vs 实现代理：**

- 第一性目标：恢复/执行正确的业务上下文和执行模式；
- 实现代理：检查 session_state 标志和 ContextVar。

**状态变化：** direct 标记被 pop，避免同一次运行重复路由；checkpoint runtime 被消费并清空；普通路径构造 `:loop` session。

**可见输出：** 三条路径最终都进入 Workflow 事件流，但 direct 会额外生成合成计划。

**不变量：** 一个 Proxy run 只能选择一个执行模式。

**关键代码：** `src/agents/digital_worker_proxy_agent.py:128-288`。

**批判：** session_state 标记简单高效，但属于隐式协议；如果上游提前清理标记、重试复用旧 state 或 restore runtime 坐标不一致，可能产生路由漂移。

### 2. endpoint 目标解析与回退

**问题压力：** AgentInfo endpoint 可能明确指向 Agent/Team/Workflow，也可能只有裸 base URL。

**核心思想：** 优先从 URL 末段解析类型；无法解析时按 Agent、Team、Workflow 候选尝试。

**触发：** 每次远程执行前调用 `resolve_remote_targets`。

**决策标准：** endpoint path 是否包含 `agents`、`teams` 或 `workflows`。

**状态变化：** 得到一个或多个 `AgnoRemoteTarget`，构造对应 runnable。

**可见输出：** 明确类型时直接透传事件；多候选时只输出最终候选的事件，隐藏试错事件。

**不变量：** endpoint 类型识别错误不能把中间试错事件误展示给用户。

**关键代码：** `src/digital_worker/resolver.py`、`src/digital_worker/executor.py:30-210`。

**批判：** 404/405 作为“类型不匹配”代理指标，能兼容模糊 endpoint，但可能把真实路由错误误判为可回退错误，或造成额外请求。

### 3. 终态归一化

**问题压力：** Agno、远程 runtime 和计划工具使用不同状态类型与错误格式。

**核心思想：** 在适配边界把远程/Agno 输出转换为有限的统一结果集合。

**触发：** 远程终态到达或本地/代理 run 结束。

**决策标准：** terminal status、RunStatus、事件名称和 content/error 字段。

**状态变化：** 生成 `DigitalWorkerTerminalState`、`RunOutput` 或 `NodeResult`，随后更新步骤状态。

**可见输出：** 统一的成功、失败、超时、取消状态和错误消息。

**不变量：** 同一种执行结果在前端、计划状态和主 Agent 侧不能表现为互相矛盾的状态。

**关键代码：** `TaskToolkit._build_terminal_state_result`、`DigitalWorkerProxyAgent._build_direct_terminal_output`、`NodeResult`。

**批判：** 统一结果降低了上层复杂度，但有信息损失：例如 timeout 被包装成 error，再依赖内容前缀恢复 timeout 语义。

### 4. 事件适配

**问题压力：** Workflow Step 会覆盖或改变 Agent 事件中的 step_id，原始事件不能直接满足计划展示。

**核心思想：** 在事件进入 Workflow 广播管道前，把计划事件转换为 `PlanExecutorNodeStarted/Completed` 等 Workflow 事件。

**触发：** `_adapt_plan_events` 遍历主 Agent 或 direct 事件流。

**决策标准：** event name、step_id、run_id、计划 bookkeeping 和取消状态。

**状态变化：** `PlanStepBookkeeping`、`TaskActivityTracker`、token request collection 更新。

**可见输出：** 前端看到正确的计划步骤、Agent 名称、状态和 HITL review。

**不变量：** Workflow step_id 不能覆盖业务 plan step_id；已 cancelled 的任务不能被后续 running/review 事件覆盖。

**关键代码：** `DigitalWorkerProxyAgent._adapt_plan_events`、`workflow/loop_plan_event_adapter.py`。

**批判：** 适配器保证了用户体验，但同一事件在多层被改写，增加了调试难度和对 Agno 事件时序的依赖。

## Algorithms

### Execution mode routing

- Problem：同一 Workflow step 可能对应三种执行模式。
- Main idea：按 restore/direct/default 优先级选择单一路径。
- Priority：primary
- Trigger：Proxy `arun`。
- Decision criteria：ContextVar restore runtime、session_state direct keys。
- Input：input、session_state、workflow_run_id。
- Output：checkpoint stream、direct stream 或 loop agent stream。
- Visible output：统一 Workflow 事件流。
- State written：消费路由标记、绑定 loop session、登记 checkpoint child run。
- Invariant：不会在一次执行中重复或漂移路由。
- Failure：标记提前清理、恢复坐标不一致、重试复用错误 state。
- Key files/functions：`DigitalWorkerProxyAgent._arun_stream`。

### Remote target fallback

- Problem：endpoint 类型信息不完整。
- Main idea：明确类型单候选直连，未知类型按 Agent/Team/Workflow 尝试。
- Priority：secondary
- Trigger：远程执行开始。
- Decision criteria：URL path marker、终态错误是否像 404/405。
- Input：AgentInfo.endpoint、agent_id。
- Output：Agno Remote runnable 和最终事件流。
- Visible output：只输出成功或最终失败候选的事件。
- State written：候选临时事件列表，不把试错事件直接发给前端。
- Invariant：类型试错不污染用户可见执行过程。
- Failure：错误码误判、额外延迟、远端产生副作用后再回退。
- Key files/functions：`resolve_remote_targets`、`execute_remote_agent`。

### Terminal state mapping

- Problem：不同执行协议的终态和错误格式不统一。
- Main idea：有限状态映射到 `NodeResult` 或代理 `RunOutput`。
- Priority：primary
- Trigger：远程 terminal 或 Agno final event。
- Decision criteria：completed/error/cancelled/timeout、RunStatus、事件名。
- Input：DigitalWorkerTerminalState、RunOutput、last event。
- Output：SUCCESS/FAILED/TIMEOUT/CANCELLED 或 completed/error/cancelled。
- Visible output：PlanStepCompletedEvent、主 Agent 结果摘要和用户回答。
- State written：计划步骤状态、result record、metrics。
- Invariant：取消不变成失败，超时不变成成功。
- Failure：错误信息丢失、timeout 需要前缀恢复、paused 被误判为 failed。
- Key files/functions：`_build_terminal_state_result`、`_build_direct_terminal_output`。

## System Design

## Invariants

- 每个执行入口都必须产生事件流或明确终态；
- 远程 run_id 获取后必须登记到父级取消关系；
- remote Agent/Team/Workflow 的差异不能泄露给上层计划状态；
- cancelled、timeout、error、success 不能互相误映射；
- direct 路径必须仍能产生前端所需的计划/步骤事件；
- 远程事件中的 session/user/workflow 上下文必须正确透传；
- HITL pause 期间不能提前发出步骤 completed；
- 远程 token metrics 只能由一个责任层记账，避免重复落库。

## Boundaries

执行适配层负责：

- 选择执行模式；
- 构造本地/远程执行对象；
- 事件流和终态转换；
- 取消、HITL、timeout、metrics 的适配；
- 向上层提供统一结果。

它不负责：

- 规划哪个 Agent 做什么；
- 远程 Agent 内部如何完成业务；
- 最终业务结果的真实性；
- 全局任务调度和持久化队列；
- 强制杀死远程进程。

## Tradeoffs

### 为什么需要 Proxy，而不是让 Workflow 直接调用主 Agent

Proxy 把 direct、normal、checkpoint 三种模式统一到 Workflow 的一个 Step 边界，避免 Workflow 知道每种执行细节。代价是路由标记、session_state 和事件适配逻辑集中到 Proxy，类会变复杂。

### 为什么 executor 和 runtime 分层

executor 面向业务调用方，负责“调用哪个远程目标”；runtime 面向事件运行，负责“如何读事件、等待 HITL、处理取消”。这避免每个业务入口复制远程流控制代码。代价是调用链更长，定位问题需要跨多个文件。

### 为什么统一成 `NodeResult`

计划层只需要知道成功、失败、超时、取消和 payload，不应依赖 Agno 事件细节。代价是一些底层信息需要通过 metrics、error_message 或 last_event 额外保留，状态语义可能出现包装。

### 为什么未知 endpoint 要缓冲候选事件

如果直接把第一种候选的事件发给前端，随后发现是错误类型，会让用户看到一段虚假的执行过程。缓冲能保护可见性一致性，但会增加内存和首事件延迟。

## Code Implementation Map

### Proxy 路由

- 文件：`src/agents/digital_worker_proxy_agent.py`
- 重点：`_arun_stream`、`_run_direct_stream`、`_stream_remote_direct`、`_adapt_plan_events`。
- 先读：三种路径的判定顺序和每条路径的输出契约。

### 远程目标解析

- 文件：`src/digital_worker/resolver.py`
- 重点：`resolve_remote_targets`、`build_remote_runnable`、timeout 构造。
- 先读：endpoint 如何变成 RemoteAgent/Team/Workflow。

### 远程高层执行

- 文件：`src/digital_worker/executor.py`
- 重点：`execute_remote_agent`、`continue_remote_agent`、`execute_remote_agent_until_terminal`。
- 先读：候选回退、HITL 入口和事件透传。

### 远程事件 Runtime

- 文件：`src/digital_worker/runtime.py`
- 重点：`iter_runnable_events`、`stream_remote_run`、`handle_remote_hitl`、`schedule_remote_cancel` 相关路径。
- 先读：run_id 登记、取消检查、终态构造和 metrics 收集。

### 编排任务映射

- 文件：`src/tools/task_tools.py`
- 重点：`_run_native_agent_stream`、`_build_terminal_state_result`、`task_execute_tool`。
- 先读：远程终态如何成为 `NodeResult` 和计划步骤状态。

### 统一模型

- 文件：`src/schema/result.py`、`src/digital_worker/types.py`。
- 先读：`NodeResult`、`DigitalWorkerTerminalState`、`DigitalWorkerPauseSignal`。

## Failure and Cost Model

### 常见失败

- endpoint 不可达、DNS、连接拒绝和 read timeout；
- endpoint 类型错误，需要 404/405 回退；
- 远程返回 4xx/5xx；
- Agent/Team/Workflow 事件字段差异导致适配错误；
- remote run_id 尚未获取就发生取消；
- HITL pause 在 direct/编排路径上采用不同兼容策略；
- RunStatus.error、timeout 和 cancelled 之间发生语义错配；
- checkpoint restore 坐标和当前 Workflow/session 不匹配。

### 降级行为

- 远程不可用被转换为明确的 terminal error，再显示为失败步骤；
- 未知 endpoint 只在像 404/405 时回退候选；
- 多候选执行只暴露最终候选事件；
- 远程 timeout 映射为失败 RunOutput，再由 direct 识别为计划 timeout；
- cancelled 终态转换为 CANCELED，不再重试；
- checkpoint snapshot 缺少新字段时按 endpoint 重新解析。

### 性能和成本

- 远程 SSE 长连接占用连接、task 和事件处理资源；
- endpoint 类型回退会增加额外网络请求；
- 多候选回退需要缓存事件，增加延迟和内存；
- 每次事件都要做 run_id 改写、状态检查和可能的 metrics 收集；
- 事件适配和结果转换增加 CPU 与维护成本；
- 远程读超时过长会长期占用任务资源，过短会误判慢任务。

## Evolution

### 当前稳定设计

- Proxy 统一三种 Workflow 执行入口；
- executor 统一远程 Agent/Team/Workflow 调用；
- runtime 统一事件、HITL、取消和终态；
- `NodeResult` 隔离计划层与执行协议；
- direct 路径通过合成计划保持前端体验一致。

### 当前过渡或薄弱部分

- `_run_native_agent_stream` 名称暗示本地执行，但实际主要委托远程数字员工 executor；
- timeout 在 Agno 没有原生状态，依赖 error + 内容前缀恢复；
- 编排场景 `enable_paused_continue=False`，仍保留旧 future 阻塞/HITL takeover 路径，直连路径和编排路径语义不完全一致；
- 未知 endpoint 的 404/405 回退是启发式，不是能力发现协议；
- Proxy 同时承担路由、事件适配、direct 结果格式化和 HITL 兼容，职责偏重；
- `NodeResult` 归一化会丢失部分远程协议细节。

### 演进方向

#### 1. 统一执行协议

定义明确的执行接口：

```text
execute(request) -> EventStream[ExecutionEvent] + ExecutionResult
continue(request) -> EventStream[ExecutionEvent] + ExecutionResult
cancel(request) -> CancelAck
```

让 Agent、Team、Workflow、direct 和 checkpoint 都通过相同的事件/终态协议接入，减少运行时类型判断。

#### 2. 用能力发现替代 endpoint 试错

远程服务提供明确的 kind、版本、能力和 schema：

```text
AgentInfo
  -> capability metadata
  -> target kind
  -> protocol version
  -> runnable adapter
```

这样可以减少 404/405 回退请求和错误副作用。

#### 3. 统一 timeout/cancel/pause 语义

把 HTTP read timeout、业务 timeout、用户 cancel 和 HITL timeout 映射为统一的执行命令和终态，而不是依赖内容前缀或不同路径的兼容分支。

#### 4. 让 `NodeResult` 保留可追踪 provenance

在统一结果中显式保留：protocol、remote_run_id、attempt、target kind、model metrics、source event 和错误分类，既保持上层简单，又避免适配时丢失诊断信息。

#### 5. 抽离事件适配器

将 Proxy 中的 direct 计划生成、Plan event 转换、TaskActivity 同步抽成独立 adapter，使 Proxy 只负责路由和生命周期绑定。

#### 6. 统一编排与直连 HITL

当前编排路径和直连路径的 paused/continue 策略不同。未来应统一为基于 snapshot + signal + continue 的协议，减少两套恢复语义。

## Synthesis

执行适配层的本质是：**屏蔽执行形态的差异，让上层只面对统一的事件、终态和步骤结果。**

它让规划层不用知道远程对象是 Agent、Team 还是 Workflow，也不用知道 HTTP timeout、HITL 和 run_id 如何处理；让生命周期层可以统一传播取消和完成状态。

当前最大成本是 Proxy/runtime 适配逻辑复杂、部分状态语义通过包装恢复，以及 endpoint 类型和 HITL 仍存在兼容分支。

下一步适合深入：`digital_worker.runtime` 的远程事件循环与 HITL/取消机制，或者 `NodeResult` 和多协议终态归一化设计。

