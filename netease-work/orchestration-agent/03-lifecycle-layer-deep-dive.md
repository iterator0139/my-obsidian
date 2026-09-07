---
tags: [netease, orchestration-agent, lifecycle-layer, workflow, hitl, graceful-shutdown]
aliases: [Orchestration Agent 生命周期层深度分析]
---

# 生命周期层深度分析

## Layer Judgment

本项目整体上把用户请求转换为一个可规划、可执行、可观察、可取消、可恢复的 Workflow run。

本篇深入生命周期层：它负责让应用、Workflow run、主 Agent、子任务和远程数字员工在创建、运行、暂停、恢复、取消、失败、完成和进程关闭时保持可解释的状态。

## 先用一条完整流程理解生命周期层

直白地说，生命周期层解决的是：**一个任务从出生到结束的全过程，谁负责推进状态、什么时候可以继续、什么时候必须停止、结束时要清理什么。**

一次正常请求大致经历：

```text
应用启动
  -> 应用进入 RUNNING
  -> 接收 Workflow 请求
  -> 创建 Workflow run
  -> run = running
  -> 执行 Workflow steps
  -> 启动主 Agent / 子 Agent / 远程 run
  -> 持续产生事件和状态快照
  -> 正常完成
  -> 写入 completed、终态事件、费用和资源清理
```

如果中途需要人工输入：

```text
running
  -> WorkflowPaused
  -> run = paused
  -> 保存 requirements / 当前步骤 / 运行上下文
  -> /continue 或 /resume
  -> run 回到 running
  -> 继续剩余步骤
```

如果用户取消或 HITL 超时：

```text
running/paused
  -> 标记父 run cancelled
  -> 取消子 Agent / 远程 run
  -> 唤醒 HITL 等待
  -> 写入 cancelled 事件和状态
  -> 清理资源
```

如果应用关闭：

```text
RUNNING
  -> DRAINING
  -> readiness 返回 503
  -> 停止接收新任务
  -> 停止同步/reaper 等后台组件
  -> 等待已有远程任务
  -> 超时后结束进程
```

所以生命周期层不是某一个状态类，而是一套“状态推进 + 事件通知 + 资源清理 + 异常收敛”的协作机制。

## Core Idea

核心机制是：

> 用 Agno 的 run/session 状态作为基础，用项目自定义的事件、取消注册表、HITL signal、TaskActivity 和资源清理逻辑，把多个独立生命周期拼成一个可收敛的任务生命周期。

它解决的真实问题是跨层状态一致性：顶层 Workflow 结束时，主 Agent、远程数字员工、HITL future、event buffer、设备和 token 统计不能各自停留在不同状态。

关键设计不是“让每个对象有 status”，而是让终态能够传播并完成收尾。

## 三条生命周期

### 1. 应用生命周期

```text
startup -> running -> draining -> shutdown
```

由 FastAPI lifespan 和 `GracefulShutdownManager` 管理。

### 2. Workflow run 生命周期

```text
pending -> running -> completed
                  -> error
                  -> cancelled
                  -> paused -> running
```

由 Agno `Workflow`、`OrchestrationWorkflow` 和 continue/background 机制共同管理。

### 3. 子任务生命周期

```text
pending/retry -> running -> succeeded
                         -> failed
                         -> timeout
                         -> cancelled
```

由 `TaskToolkit`、Proxy、远程 Runtime 和 `cancel_registry` 管理。

三条生命周期不是完全相同的状态机，但存在父子约束：应用 draining 会阻止新任务，父 Workflow cancel 会传播到子任务，Workflow 终态需要触发资源清理和事件收尾。

## Mechanism Priority Map

### Primary mechanisms

#### 1. Workflow run 状态推进

- 优先级：primary
- 作用：定义一次任务何时运行、暂停、完成、失败或取消。
- 关键文件：`src/workflow/orchestration_workflow.py`、Agno Workflow。

#### 2. 取消传播与终态收敛

- 优先级：primary
- 作用：把父 Workflow 的取消传递给主 Agent、子 Agent 和远程数字员工，并确保前端看到 cancelled。
- 关键文件：`src/workflow/orchestration_workflow.py:563`、`src/utils/cancel_registry.py`、`src/digital_worker/cancel.py`。

#### 3. 暂停/继续与 HITL 生命周期

- 优先级：primary
- 作用：保存暂停点和 requirements，支持用户继续、超时或取消。
- 关键文件：`src/workflow/continue_background_mixin.py`、`src/api/continue_background_router.py`、`src/utils/hitl_registry.py`。

### Secondary mechanisms

#### 4. 应用启动、draining 和优雅关闭

- 优先级：secondary
- 作用：管理 Agent 同步、HITL reaper、checkpoint sweeper、远程任务等待和 tracing。
- 关键文件：`src/lifespan.py`、`src/utils/graceful_shutdown.py`。

#### 5. 终态资源清理

- 优先级：secondary
- 作用：释放 DK 设备、HITL snapshot、continue lock、远程任务登记和 token 临时数据。
- 关键文件：`src/workflow/orchestration_workflow.py`、`src/digital_worker/runtime.py`。

### Supporting mechanisms

- `TaskActivityTracker`：把内部运行状态映射成前端任务状态；
- event buffer 终态 TTL 和 sentinel；
- 取消原因 ContextVar + registry 跨协程传递；
- checkpoint orphan sweeper；
- `on_error="fail/skip"` 和 `max_retries=0` 等步骤策略。

## Layer Problem

生命周期层主要承受以下压力：

| 压力 | 具体问题 |
|---|---|
| 状态一致性 | DB、内存 run、前端活动状态和 event buffer 可能不同步 |
| 并发 | cancel、resume、timeout、正常完成可能同时发生 |
| 父子关系 | 顶层 run 和远程 run 使用不同 run_id |
| 长任务 | Workflow 可能在 HTTP 连接断开后继续运行 |
| 人工介入 | paused 之后要保存足够信息才能恢复 |
| 资源释放 | 设备、锁、Redis key、远程任务和 tracing 需要最终清理 |
| 进程关闭 | 新任务要拒绝，已有任务要等待或超时退出 |

## Core Abstractions

### `OrchestrationWorkflow`

- 表示：顶层业务 Workflow。
- 拥有：步骤编排、run 事件适配、取消后处理、正常完成清理。
- 不拥有：Agno 底层所有 run 存储细节、专业 Agent 业务逻辑。
- 关键方法：`arun`、`_aexecute_stream`、`acancel_run`、`_handle_run_cancelled`。

### `RunStatus`

- 表示：Agno 层面的 Workflow run 状态。
- 作用：决定是否能 continue、是否需要终态 TTL、是否需要持久化更新。
- 注意：它不等同于前端 `TaskActivityTracker` 的 `running/completed/error/review/cancelled`。

### `ParentChildRunRegistry`

- 表示：父 run 到子 run 的进程内关系。
- 拥有：注册、反注册、级联取消和取消原因。
- 不拥有：远程服务真正的取消执行；远程取消由 `schedule_remote_cancel` 负责。

### `ContinueBackgroundMixin`

- 表示：paused run 继续执行时的生命周期适配器。
- 拥有：detached task、事件消费、终态哨兵和 continue lock 释放。
- 不拥有：暂停原因的业务决策和主 Agent 的规划。

### `GracefulShutdownManager`

- 表示：进程内应用生命周期状态和远程任务登记表。
- 拥有：RUNNING/DRAINING、拒绝新远程任务、等待任务清空。
- 不拥有：所有 Workflow run 的统一持久化状态，也不负责强制终止远程服务。

### `TaskActivityTracker`

- 表示：面向前端的任务活动快照。
- 拥有：步骤名称、执行状态、review 信息。
- 不拥有：完整事件历史和 Agno run 的唯一状态。

## Main Flow

### 应用启动

```text
agentos_main import
  -> 创建 AgentOS / Workflow / AgentStore
  -> 配置 checkpoint repository
  -> 配置 tracing 和 JWT issuer
  -> FastAPI lifespan startup
  -> begin_running
  -> 启动 Agent sync scheduler
  -> 启动 HITL reaper
  -> 启动 checkpoint sweeper / aiomonitor
```

### Workflow 正常运行

```text
Workflow.arun
  -> Agno 创建/加载 session 和 run
  -> OrchestrationWorkflow.arun 强制事件流
  -> 准备 session data / Agent / sandbox / skills
  -> loop_execute
  -> _aexecute_stream 适配事件
  -> WorkflowCompleted
  -> 释放设备
  -> token cost 汇总
  -> return_final_output
  -> event buffer 写 completed
```

`loop_execute` 设置 `on_error="fail"`，使关键执行异常和取消能够离开 Step 边界，避免被默认 skip 吞掉。

### Workflow 暂停与继续

```text
Agent/数字员工触发 HITL
  -> WorkflowPaused / StepExecutorPausedEvent
  -> 保存 requirements、paused step、step results
  -> event_buffer.set_run_completed(paused)
  -> 前端显示 review
  -> /continue
  -> 校验 run 仍 paused + 获取 continue lock
  -> acontinue_run
  -> 继续消费事件
  -> completed / error / paused / cancelled
```

主 Agent HITL 和远程数字员工 HITL 的等待实现不同，但生命周期层需要把它们都映射为可观察的 review/paused 状态。

### Workflow 取消

```text
用户 /cancel 或 HITL reaper timeout
  -> OrchestrationWorkflow.acancel_run
  -> Agno 标记父 run cancelled
  -> mark_cancelled(reason)
  -> cascade_cancel 子 run
  -> Redis/HITL signal 唤醒等待者
  -> schedule_remote_cancel 远程通知
  -> paused/running run 持久化为 cancelled
  -> 写 WorkflowCancelledEvent
  -> 同步 TaskActivity = cancelled
  -> 释放设备、HITL、registry
```

这里的关键是：取消不仅是写一个 status，而是要让所有阻塞点和观察者都收到终态。

### 应用关闭

```text
health/drain 或 lifespan shutdown
  -> begin_draining
  -> readiness = 503
  -> 停止 Agent sync
  -> 停止 checkpoint sweeper
  -> 停止 HITL reaper
  -> shutdown tracing
  -> wait_for_no_running_tasks(timeout)
  -> 停止 draining 日志
  -> 进程退出
```

## Runtime Channel Map

| 状态/信息 | 来源 | 通道 | 生效位置 | 保护机制 | 可能失效 |
|---|---|---|---|---|---|
| Workflow run status | Agno run | session/DB | `WorkflowRunOutput.status` | `upsert_run`、`asave_session` | 异常中断导致 DB 停留 running |
| 前端任务状态 | Workflow/Agent events | `TaskActivityTracker` | `TaskStatusDetail` | `sync_task_activity` | 状态同步失败或缺 tracker |
| 取消状态 | Agno cancellation manager | `cancel_registry` | 本地协程检查 | `araise_if_cancelled`、cascade | 子 run 未及时登记 |
| 取消原因 | ContextVar | registry reason map | 跨协程消费者 | `mark_cancelled/drop_cancel_reason` | 清理时序不当可能丢原因 |
| HITL paused state | Agno requirements / Redis snapshot | DB + Redis | continue/HITL handler | claim、TTL、reaper | snapshot 或 signal 过期 |
| 事件终态 | Workflow events | event buffer | SSE/resume | `set_run_completed`、sentinel | 某些 continue 路径需显式补写 |
| 远程任务状态 | Runtime | shutdown manager | draining 等待 | `track_remote_task` | 仅追踪当前进程任务 |
| token 临时数据 | session_state | `_token_requests` | cost step/异常兜底 | finalize + cleanup | 进程崩溃时可能未落库 |

### 同一终态的多个表现

一次 cancelled 需要同时表现为：

```text
Agno run.status = cancelled
WorkflowCancelledEvent
event_buffer completed(cancelled)
SSE subscriber complete
TaskActivity status = cancelled
子 run / 远程 run 被取消
HITL pending/signal 被清理
```

任何一个通道缺失，用户都可能看到“任务已经取消但页面还在运行”或“页面结束但远程仍在执行”。

## Mechanism Interrogation

### 1. `OrchestrationWorkflow._aexecute_stream` 终态收敛

**问题压力：** Agno 的异常、取消和事件路径可能不会自动把所有业务状态推进到一致终态。

**核心思想：** 在对象事件流边界统一捕获正常完成、取消和异常，补充清理和状态同步。

**触发：** 每个 Workflow 执行流结束、抛出 `RunCancelledException` 或其他异常。

**决策标准：** 异常类型和事件流是否正常结束。

**第一性目标 vs 实现代理：**

- 第一性目标：所有 run 和下游资源最终收敛到正确状态；
- 实现代理：在 `_aexecute_stream` 的 `async for/except` 分支中补清理、算费和活动状态。

**状态变化：** 正常路径释放设备；取消路径尝试算费；异常路径同步 error 并尝试算费。

**可见输出：** WorkflowCompleted、WorkflowError、WorkflowCancelledEvent、TaskActivity 终态和 SSE 终止。

**不变量：** 取消不能被 background runner 的通用异常处理重新标记为 error。

**关键代码：** `src/workflow/orchestration_workflow.py:852-930`。

**批判：** 该机制能补齐 Agno 与业务状态之间的缺口，但依赖事件流确实经过这个覆盖点；进程崩溃或框架在更早阶段失败时仍无法完成兜底。

### 2. `acancel_run` 级联取消

**问题压力：** 父 Workflow、主 Agent 和远程数字员工拥有不同 run_id，Agno 默认取消只覆盖当前 run。

**核心思想：** 先取消父 run，再依据 registry 级联子 run，并额外唤醒 HITL 和远程取消接口。

**触发：** 用户 `/cancel`、HITL timeout、内部取消。

**决策标准：** 父子 run 是否已登记、run 是否 paused/running、是否存在远程 HITL snapshot。

**状态变化：** cancellation manager、registry、Redis signal、DB run、event buffer 和 TaskActivity 同时变化。

**可见输出：** cancelled 事件、前端 cancelled 状态、远程终止通知。

**不变量：** 父级取消不会遗留正在等待的子任务和 review 状态。

**关键代码：** `src/workflow/orchestration_workflow.py:563`、`src/utils/cancel_registry.py:44`。

**批判：** 这是协作式取消，不是强杀；远程服务是否及时响应仍取决于网络和远端实现。

### 3. `ContinueBackgroundMixin` 终态管理

**问题压力：** paused run 的 continue 如果绑定原始 SSE，客户端断开会中断事件消费和续跑。

**核心思想：** detached task 消费完整 `acontinue_run` 流，原始连接只是一个可选订阅者。

**触发：** `background=True` 的 continue。

**决策标准：** 最终 run status 是否为 completed/error/cancelled/paused。

**状态变化：** 后台 task、event buffer、subscriber、终态 TTL 和 continue lock。

**可见输出：** 当前 SSE、重连事件、终态 sentinel。

**不变量：** 连接断开不能取消续跑；已知终态必须通知 subscriber 并释放锁。

**关键代码：** `src/workflow/continue_background_mixin.py:80-260`。

**批判：** 它解决了请求级断线，但 detached task 仍属于进程内资源，不解决 Pod 崩溃恢复。

### 4. Graceful shutdown

**问题压力：** 进程关闭时不能继续接收新任务，也不能立刻杀掉已登记的远程任务。

**核心思想：** 先通过 readiness 摘流量，再停止后台生产者，最后等待存量远程任务。

**触发：** `/health/drain`、FastAPI lifespan shutdown、Kubernetes 终止流程。

**决策标准：** lifecycle state 和 running task count。

**状态变化：** `RUNNING -> DRAINING`，readiness 变为 503，远程任务登记停止，后台组件停止。

**可见输出：** health 状态、日志、最终进程退出。

**不变量：** draining 后不启动新远程任务，已有任务获得有限收尾时间。

**关键代码：** `src/utils/graceful_shutdown.py:79-230`、`src/lifespan.py:206-310`。

**批判：** 当前 manager 只追踪进程内登记的远程任务，不是全局任务协调器；超时后只能记录仍在运行的任务。

## Algorithms

### Parent-child cancellation propagation

- Problem：不同 run_id 的父子任务需要协同取消。
- Main idea：登记父子关系，父取消时并发调用子 run cancel。
- Priority：primary
- Trigger：子 run 得到有效 run_id，或父级收到 cancel。
- Decision criteria：registry 中的 child set、父级 cancellation 状态。
- Input：parent_run_id、child_run_id、取消 reason。
- Output：本地 `acancel_run`、远程 fire-and-forget cancel、cancelled 终态。
- State written：registry、Agno cancellation manager、Redis HITL、DB/session、event buffer。
- Invariant：父取消后不遗留子 run。
- Failure：取消前子 run 未登记、网络失败、远端不响应、跨进程状态延迟。

### Graceful draining gate

- Problem：服务关闭期间新请求和已有任务需要区别处理。
- Main idea：先切换 DRAINING，再拒绝新远程任务，等待已登记任务。
- Priority：secondary
- Trigger：`health_drain` 或 lifespan shutdown。
- Decision criteria：`is_accepting_requests()`、任务登记时的 state 检查、等待 timeout。
- Input：生命周期状态、远程任务 metadata、shutdown timeout。
- Output：readiness 503、`DrainingError`、等待结果。
- State written：manager state、task registry、运行日志。
- Invariant：不接收新任务，已有任务有最大收尾窗口。
- Failure：任务未登记、任务卡死、等待超时、进程被强制终止。

### Paused run continuation

- Problem：HITL 暂停后需要从原状态继续，而不是创建无上下文的新任务。
- Main idea：持久化 paused run 和 requirements，continue 时恢复原 run。
- Priority：primary
- Trigger：`WorkflowPaused` 后调用 `/continue`。
- Decision criteria：run 是否存在、session 是否匹配、状态是否 paused、continue lock 是否取得。
- Input：run_id、session_id、step requirements、继续输入。
- Output：继续事件流、再次 paused 或最终终态。
- State written：run messages/requirements、session、event buffer、checkpoint、continue lock。
- Invariant：同一 paused run 不被多个 Pod 同时继续。
- Failure：状态已变化、锁竞争、checkpoint 不一致、requirements 丢失。

## System Design

## Invariants

- 一个 run 只能有一个明确的终态；
- cancelled 不能在后续通用异常处理里被覆盖为 error；
- paused 必须保存足够的 requirements 和恢复坐标；
- 父级取消必须覆盖已登记的子 run；
- 终态必须同步到 run、事件、前端活动和必要的远程/HITL 资源；
- draining 后不能启动新的受管控远程任务；
- 正常完成和取消都必须释放独占资源；
- token 临时数据在正常、取消和异常路径都应有落库/清理机会。

## Boundaries

生命周期层负责状态推进和收尾，不负责决定子任务业务内容。

它依赖：

- Agno 提供 run/session/requirements 基础；
- 接入层提供 `/continue`、`/cancel` 和 SSE；
- 执行层提供远程 run_id 和终态；
- Redis 提供跨 Pod HITL signal；
- DB 提供 session、checkpoint 和 token 持久化。

它刻意不解决：

- 远程服务一定可用；
- 取消一定立即生效；
- Agent 结果一定正确；
- 进程崩溃后的所有内存任务自动恢复。

## Tradeoffs

### 为什么在 Workflow 中覆盖 `acancel_run`

因为只有顶层 Workflow 知道父子 run、HITL、TaskActivity、设备和远程资源的完整关系。代价是取消逻辑集中且复杂，强依赖 Agno 的 cancel 调用时序。

### 为什么使用协作式取消

协作式取消能让 Agent、远程 HTTP 流和 HITL 等待自行清理，避免强杀造成锁、session 或远程任务残留。代价是取消有延迟，且依赖每个等待点主动检查取消状态。

### 为什么把 paused 当作一等状态

paused 不是 error，也不是 completed。它必须保留 requirements、step index 和事件 buffer，使用户可以继续或取消。代价是 resume、TTL、取消和前端状态都要显式处理 paused。

### 为什么 graceful shutdown 只等待远程任务

当前 `GracefulShutdownManager` 的直接职责是管理远程任务登记；Workflow、数据库请求和进程内 background task 的收尾由各自组件负责。这样职责清晰，但全局关闭完成条件不是一个统一的任务集合。

## Code Implementation Map

### Workflow 构造与步骤策略

- 文件：`src/workflow/orchestration_workflow.py:411`
- 重点：步骤列表、`loop_execute` 的 `on_error="fail"`、`max_retries=0`、cost step 的 `on_error="skip"`。
- 先读：步骤策略和每个步骤的终态影响。

### Workflow 运行覆盖点

- 文件：`src/workflow/orchestration_workflow.py:525`
- 重点：`arun`、`_aexecute_stream`、`_adapt_loop_workflow_events`。
- 先读：事件流如何进入正常、取消和异常分支。

### 取消收敛

- 文件：`src/workflow/orchestration_workflow.py:563`
- 重点：`acancel_run`、`_handle_run_cancelled`、`_advance_paused_run_to_cancelled`。
- 先读：父类 cancel、cascade、HITL signal、DB 状态、event buffer 和 TaskActivity 的顺序。

### 应用生命周期

- 文件：`src/lifespan.py:206`
- 重点：`_agent_sync_lifespan` 的 startup/yield/shutdown 三段。
- 先读：启动哪些后台组件，关闭时按什么顺序停止和等待。

### 优雅关闭状态机

- 文件：`src/utils/graceful_shutdown.py:38`
- 重点：`LifecycleState`、`register_task`、`track_remote_task`、`wait_for_no_running_tasks`。
- 先读：哪些任务会被计入 draining 等待。

### Continue 生命周期

- 文件：`src/workflow/continue_background_mixin.py:80`
- 重点：`start_background_continue`、`_drive_background_continue`、`_handle_background_continue_error`。
- 先读：后台续跑如何获取最终 run 并写入终态。

## Failure and Cost Model

### 正常失败

- Workflow step 抛异常：关键 `loop_execute` 通过 `on_error="fail"` 传播；
- cost step 失败：`on_error="skip"`，业务结果仍可返回；
- 用户取消：需要避免被通用异常路径改写为 error；
- HITL timeout：reaper 触发 cancel，而不是让等待协程自行构造多个 timeout 终态；
- continue 校验失败：保留 paused 状态，允许重新提交。

### 降级行为

- 无法读取 run：仍尝试使用 cancel request/session context 同步 TaskActivity；
- event buffer 写入失败：记录日志，但 run 状态可能仍可持久化；
- 资源释放失败：best-effort 日志，不阻断主终态；
- shutdown 等待超时：记录仍运行任务，进程继续退出；
- checkpoint 初始化失败：保留 Agent 原生 marker，但 checkpoint 查询/恢复不可用。

### 成本

- 每个 run 需要 session、事件、状态和可能的 checkpoint 持久化；
- 取消需要多次异步/Redis/远程操作；
- paused run 需要保留更长 TTL 和恢复数据；
- 终态补偿代码较多，维护成本高；
- graceful shutdown 只能对已登记任务提供强保证。

## Evolution

### 当前问题

1. 生命周期状态分散在 Agno run、TaskActivity、event buffer、HITL registry 和远程终态中；
2. `cancelled`、`error`、`paused` 的收敛需要多处补偿代码；
3. `cancel_registry` 是进程内结构，跨 Pod 依赖 Redis 补偿；
4. detached background task 和 webhook task 在进程崩溃后不可自动恢复；
5. graceful shutdown 的等待集合只覆盖已登记远程任务，不是所有 Workflow task；
6. 部分正常、异常、continue 和 cancel 路径需要分别写 event buffer 终态，存在漏写风险。

### 演进方向

#### 1. 统一 Run State Machine

定义唯一的 Workflow run 状态源和合法迁移：

```text
accepted -> running -> paused -> running
                    ├-> completed
                    ├-> error
                    ├-> cancelled
                    └-> expired
```

所有事件、TaskActivity、HITL 和远程状态都成为这个状态机的投影，而不是各自推进一份状态。

#### 2. 统一终态协调器

将正常完成、异常、取消、超时统一进入：

```text
finalize_run(run_id, final_status, reason)
  -> 持久化 run
  -> 写终态事件
  -> 完成 event buffer/subscriber
  -> 同步 TaskActivity
  -> 取消/清理子任务与 HITL
  -> 释放锁和资源
  -> 完成 token/checkpoint 收尾
```

减少 `_aexecute_stream`、`acancel_run`、background producer 和 reaper 之间的重复补偿逻辑。

#### 3. 外部化 Workflow 执行协调

把当前进程内 background task 演进为可恢复的外部任务：

```text
创建 Run
  -> 持久化 accepted
  -> 投递 Worker
  -> Worker 执行并心跳
  -> 持久化状态/事件
  -> Worker 重启后恢复或重试
```

这样应用关闭和 Pod 崩溃不再直接等价于任务丢失。

#### 4. 分离应用生命周期与任务生命周期

应用 draining 不应只等待本进程 remote task，而应由外部 Run Coordinator 负责全局任务状态；Pod 只负责停止接收新任务和安全退出本地 Worker。

#### 5. 标准化取消命令

```text
CancelCommand(run_id, reason, source)
  -> 原子推进 run 状态
  -> 唤醒本地等待
  -> 传播子 run
  -> 通知远程
  -> 发布终态
```

避免用户 cancel、HITL timeout、跨 Pod cancel 使用不同的状态推进路径。

## Synthesis

生命周期层的本质是：**让一个 Workflow run 从开始到结束能够正确收敛，而不是让每个模块各自记录一个 status。**

它使接入层可以提供可靠的 `/continue`、`/cancel`、SSE 和 readiness，使编排层可以专注于任务决策，使执行层可以专注于 Agent 工作。

当前最大成本是状态分散和终态补偿逻辑复杂。下一步最适合深入的是“事件管道与终态协调”，尤其是 `_aexecute_stream`、`acancel_run`、`ContinueBackgroundMixin` 三者如何共同决定最终状态。

