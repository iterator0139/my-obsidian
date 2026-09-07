# 运行治理层深度分析

## Layer Judgment

本项目整体链路是“请求接入 → Workflow 生命周期 → 意图与规划 → 执行适配 → 远程 Runtime / 专业 Agent”。运行治理层横切这条链路：它不负责判断任务是什么，也不负责具体执行任务，而是负责让一次运行在真实生产环境中可控、可追踪、可计量、可停止、可恢复。

## 先用一条完整流程理解运行治理层

直白地说，一次任务开始后，治理层会做下面这些事：

~~~text
任务启动
  -> 确认调用哪个数字员工、是否需要 JWT
  -> 建立父 Workflow run 与子 Agent/远程 run 的关系
  -> 执行中收集事件、状态、trace 和 token 用量
  -> 遇到 HITL，保存暂停现场和恢复所需信息
  -> 用户继续、取消，或 reaper 判定超时
  -> 传播到本地子 run、远程 run 和其他 Pod
  -> 统一收敛 completed / failed / cancelled / paused
  -> 记录费用、活动状态，清理锁、快照、任务注册
~~~

这一层解决的核心问题是：一个可能跨多个协程、多个 Agent、多个 Pod 和多个服务的长任务，如何在任何时刻都能被正确控制，并且最终留下可信的状态和成本记录。

它与生命周期层的区别是：生命周期层回答“任务处于什么阶段，如何走到终态”；运行治理层回答“运行时如何被授权、暂停、取消、计费、观测，以及实例下线时如何保护它”。

## Core Idea

核心想法不是把所有执行逻辑集中到一个管理器，而是建立横向控制通道：

- ParentChildRunRegistry 把分散的 run 串成可取消的父子树。
- Redis pending snapshot、signal 和租约锁，把 HITL 从单 Pod 内存等待升级为跨 Pod 可接管状态机。
- JWT、auth_token 和远程取消通知维护服务之间的信任边界。
- 事件、trace、TaskActivity 和 token usage 把运行过程转成可观测、可核算的数据。
- GracefulShutdownManager 把实例关闭变成先摘流量、再排空任务。

没有这一层，主流程即使能跑通，也会出现：父任务取消但远程员工继续耗费资源、Pod 重启后 HITL 永远挂住、费用漏记、无法解释任务为何结束，以及实例下线时新任务被截断。

## Mechanism Priority Map

### Primary mechanisms

1. 取消传播与终态收敛：解决跨 run、跨协程、跨 Pod、跨远程服务停止任务。主要代码是 src/utils/cancel_registry.py、src/digital_worker/cancel.py、src/digital_worker/runtime.py。
2. HITL 持久化与接管：解决人工等待很长且原执行 Pod 可能消失。主要代码是 src/utils/hitl_registry.py、src/utils/hitl_reaper.py、src/digital_worker/hitl_takeover.py。

### Secondary mechanisms

3. 鉴权与信任边界：按 AgentInfo.need_auth 运行时获取签名密钥并签发 JWT，覆盖启动、继续和取消。
4. 优雅关闭与任务排空：通过 RUNNING → DRAINING、readiness 503 和远程任务注册，降低发布或重启的影响。

### Supporting mechanisms

5. token 成本记账：收集每次模型请求的 metrics，按 provider/model 聚合并幂等写库。
6. 观测和活动同步：把事件、trace、TaskActivity、SSE/Redis stream 和数据库审计连接起来。
7. checkpoint 与后台清理：保存可恢复的语义状态，清理已经失去对应 run 的孤儿记录。

## Layer Problem

一次编排会创建多个独立的 Agno run，而原生 cancel 通常只命中一层；远程数字员工可能在另一个服务、另一个 Pod 中运行；HITL 不能依赖一个长期 HTTP 请求；一次任务又可能包含多次模型请求、嵌套 Team/Workflow 和不同模型；Kubernetes 还会主动终止实例。

因此治理层优先保证三件事：控制信号能送达、状态最终可解释、异常路径尽可能记账。

## Core Abstractions

### ParentChildRunRegistry

表示父 run 到子 run 的取消关系。它拥有注册、级联取消、注销和取消原因映射，但不拥有业务计划，也不负责等待子任务自然完成。

### HitlSnapshot 与 Redis Registry

表示一次暂停所需的最小恢复现场，包括 workflow/run/session、远程目标、pause event、继续 session、用户和 deadline。Redis 还保存 signal、continue/takeover 锁和 workflow 索引。

### JwtTokenIssuer

表示一次远程调用所需的服务身份。私钥按 group 运行时获取并短期缓存；issue 只负责同步签发，便于塞入 Agno 的同步闭包。

### GracefulShutdownManager

表示本 Pod 的接收状态和正在运行的远程任务集合。它拥有准入、注册、注销和等待排空，不拥有远程任务本身。

### Token usage、Activity、Trace

这是治理层的事实记录面：session_state 是运行中累积的临时数据，数据库是费用明细和活动审计，OpenTelemetry/Langfuse 是诊断链路，事件流是前端实时反馈。它们不是同一份数据，不能互相替代。

## Main Flow

### 1. 建立信任和运行关系

执行适配器准备远程 runnable 后，runtime.py 根据 AgentInfo.need_auth 获取签名密钥。需要鉴权时，JwtTokenIssuer 依据 agent 所属 group 获取私钥和 kid，为 run、continue 或 cancel 生成 JWT。初始运行可把 user_id 写入 sub；继续和取消使用服务令牌，避免错误触发远程 run owner 校验。

远程事件第一次带出真实 remote_run_id 后，iter_runnable_events 将它登记为父 Workflow 的 child。之后父级取消就能找到它。

### 2. 执行中形成多条治理通道

~~~text
远程事件
  ├─ event stream / SSE：前端实时显示
  ├─ session DB：可回放和审计
  ├─ TaskActivity：running / paused / cancelled 等业务状态
  ├─ OpenTelemetry / Langfuse：调用链和模型请求
  └─ session_state["_token_requests"]：每次模型请求的用量
~~~

runtime.py 对嵌套 Agent/Team/Workflow 的完成事件按 provider、model_id 聚合，并用 seen_metric_event_run_ids 防重复累计；每个 ModelRequestCompleted 则通过 collect_request_tokens 写入 remote_worker 范围的请求明细。

### 3. HITL 暂停、恢复和接管

出现人工输入、确认、外部执行或输出审核时，系统把暂停事件和恢复字段组成 HitlSnapshot 写入 Redis pending，owner 协程通过 Redis signal 等待。

用户响应先进入 Redis resume mailbox，再通过 claim/continue 锁保证同一 workflow 不会被两个 Pod 同时 acontinue_run。原 Pod 存活时 signal 唤醒它；原 Pod 消失时，另一个 Pod 通过 hitl_takeover.py 取得租约，重建 runnable 和 pause event，继续远程运行，并把事件写回原 workflow 的 Redis stream。

如果继续后再次 HITL，接管协程生成新的 snapshot，等待下一次用户响应，而不是长时间持锁。若超过 deadline，reaper 原子投递 timeout signal，并调用顶层 acancel_run，不能只写一个无人消费的 timeout 消息。

### 4. 取消传播

取消有三条互补路径：

1. 同进程：父 Workflow 的 acancel_run 通过 ParentChildRunRegistry.cascade_cancel 调用每个子 run 的 acancel_run。
2. 跨 Pod：HITL registry 以 workflow 为索引写 Redis cancel signal；运行事件循环每轮检查 is_workflow_cancelled。
3. 跨服务：子 run 感知 RunCancelledException 或 Redis cancel 后，调用 schedule_remote_cancel，按 Agent/Team/Workflow 构造远程 /cancel，携带 JWT 和 session_id。该调用 fire-and-forget，避免远程网络故障阻塞本地终止。

取消原因通过 ContextVar 在当前协程传递；由于不同 asyncio task 不会自动共享该上下文，cancel_registry 另外保存 reason，供流末兜底读取。这样用户主动取消和 hitl timeout 能在 TaskActivity 中区分。

### 5. 终态、成本和资源清理

任务结束时，事件适配器产出统一 terminal state，父子关系注销，HITL pending、索引和锁清理，远程任务从 shutdown manager 注销。费用计算步骤从 session_state 汇总 token，调用 calculate_cost，再以 run_id 幂等写入 token_usage_log；日汇总表由刷新任务覆盖式聚合。

## Runtime Channel Map

| 信息类型 | 实际通道 | 有效时长/保护 | 可能丢失或过期的地方 |
|---|---|---|---|
| 取消状态 | Agno cancel manager + Redis workflow cancel signal | 本地即时；Redis 支持跨 Pod | 远程 HTTP cancel 失败时，远端只能等自身协作检查 |
| 取消原因 | ContextVar + ParentChildRunRegistry | 当前 cancel 流程及消费完成前 | 消费者未读取时会残留；进程崩溃前可能无法记录 |
| HITL 现场 | Redis hitl:pending snapshot | TTL + deadline；takeover 锁保护 | Redis 过期或 snapshot 不完整会恢复失败 |
| HITL 用户响应 | Redis mailbox + signal list | 入队原子、可幂等 claim | signal TTL 到期后无法继续 |
| 运行事件 | 内存/Redis event buffer、SSE、session DB | stream 可回放，DB 可审计 | SSE 断开不等于任务丢失；未落库的瞬时事件有窗口 |
| token metrics | session_state["_token_requests"] + DB log | run 内累积，DB 以 run_id 幂等 | 硬杀可能跳过最终算费；取消路径需兜底 |
| 远程身份 | ContextVar 签名密钥 + 短期 JWT cache | 协程链路和 token TTL | 跨 Pod takeover 需重新取密钥 |
| 运行中任务 | 进程内 shutdown manager registry | finally 注销 | Pod 崩溃会丢本地登记 |

## Mechanism Interrogation

### 取消传播的不变量

- 子 run 取得真实 run_id 后必须登记；取消可能先于子 run 启动，因此 register_child 会检查父级是否已取消。
- 取消调用必须幂等，级联时对 child 并发 acancel_run，并在锁外执行。
- 远程 cancel 不应阻塞本地终态收敛，但必须携带正确的 auth_token 和 session_id。
- RunCancelledException 应映射为 cancelled，而不是普通 error；取消原因应继续传到活动记录。

### HITL 的不变量

- resume/cancel/timeout 必须通过 Redis 原子状态转换，重复响应不能重复续跑。
- 同一 workflow 同时只能有一个 continue owner。
- owner 丢失后 takeover 必须能重建 runnable；锁丢失的旧协程必须停止写事件。
- reaper 必须同时投递 signal 和推进顶层 workflow 终态。
- snapshot 只保存恢复所需的白名单状态，不能把私钥等敏感运行态写入 checkpoint。

### 成本记账的不变量

- 嵌套完成事件要聚合，但同一个 metrics run_id 不能重复计入。
- cache read 已包含在 input 口径时，计算 input cost 要扣除 cache read，避免重复计费。
- token_usage_log 以 run_id 幂等，daily 表按日期、scope、agent、model 聚合。

## System Design

### 为什么取消采用“本地 + Redis + 远程 HTTP”三段式

三者解决的故障域不同：Agno cancellation manager 负责当前进程的快速协作式退出；Redis 负责 Pod 之间传递信号；远程 HTTP 负责通知另一个服务的运行时。只使用其中任何一段都会留下盲区。

### 为什么 HITL 不直接依赖 workflow paused

当前数字员工 HITL 快路径保持 owner workflow 运行并在 Redis 上等待。这样跨 Pod resume/cancel 可以由 signal 唤醒，reaper 也能统一处理 deadline；HitlSnapshot 负责恢复现场，而不是让一个长 coroutine 永久占住进程资源。

### 为什么签名密钥使用 ContextVar

私钥不能进入 session_state 或 checkpoint；同一协程链路内又希望多次远程调用复用。ContextVar 同时提供隔离和短生命周期。跨 Pod takeover 是新 task，因此重新获取密钥是有意设计。

## Failure and Cost Model

### 常见失败

- 远程 cancel 请求超时或返回 4xx：本地继续收敛，远端可能延迟退出。
- Redis 不可用：HITL 跨 Pod 接管、跨进程 cancel 和 reaper 会退化或失败。
- worker 在 signal 入队后、消费前崩溃：pending snapshot 和 takeover 锁使其他 Pod 有机会接管；snapshot 过期后只能报恢复失败。
- 进程被硬杀：进程内 registry、shutdown task、内存 event buffer 和未落库 token 可能丢失。
- ContextVar 跨独立 task 不传播：取消原因和密钥不能假设天然可见，所以代码中存在显式 registry 和重新 acquire。

### 运行成本

- Redis 需要维护 pending、signal、锁和 workflow 索引。
- 每个远程调用增加事件归一化、metrics 聚合和取消检查开销。
- reaper、checkpoint sweeper、Agent sync 和 draining log 都是后台任务，需要在 shutdown 时停止。
- token 明细和事件审计带来 DB 写入，但换取可计费、可追责和可运营性。

## Evolution

### 当前主要问题

1. 本地 ParentChildRunRegistry 仍是进程内状态；非 HITL 的远程任务在 owner Pod 异常时，关系和取消能力不完整。
2. 取消是协作式的，事件流每轮才检查，远程服务也可能不及时响应，无法保证严格停止时延。
3. 运行事实分散在 event buffer、session、TaskActivity、Redis snapshot、trace 和 token log，需要多种 id 关联。
4. 硬杀可能让 token 汇总和最终 activity 没有机会落库。
5. graceful shutdown 主要追踪当前 Pod 的远程任务，跨 Pod 接管任务和纯本地 Agent 任务不完全纳入排空集合。

### 演进方向

- 建立持久化 run control plane，统一保存 parent-child、remote run、desired state、observed state 和最后心跳。
- 为取消增加带版本和时间戳的 durable command，让远程 runtime 定期确认 command version，形成可重试的 cancel handshake。
- 将 HITL、普通远程任务、checkpoint 恢复统一为 lease + durable state machine，减少多套锁和状态语义。
- 使用稳定 correlation id 统一关联 token、activity、event 和 trace，并明确实时事件、审计事件、计费明细的保留策略。
- 为异常退出补充 outbox/异步补偿记账，并对 cancel、timeout、takeover、remote cancel failure 建立指标和告警。
- 让 shutdown manager 追踪所有可继续或可取消的运行，drain 超时后明确执行后台化、转移租约或标记待恢复的策略。

## Code Implementation Map

| 能力 | 主要代码 |
|---|---|
| 父子取消注册与 reason | src/utils/cancel_registry.py、src/utils/cancel_user_context.py |
| 远程 cancel URL、JWT、fire-and-forget | src/digital_worker/cancel.py、src/utils/jwt_token_issuer.py |
| 远程事件取消检查、run 登记、metrics/token 收集 | src/digital_worker/runtime.py |
| HITL 事件识别和用户 payload 回填 | src/digital_worker/hitl.py |
| HITL Redis signal、pending、锁和快路径 | src/utils/hitl_registry.py、src/utils/hitl_snapshot.py |
| HITL 超时和分布式 reaper | src/utils/hitl_reaper.py |
| 跨 Pod 远程接管 | src/digital_worker/hitl_takeover.py |
| token 定价与计算 | src/utils/token_cost_tools.py |
| token 明细、幂等和日聚合 | src/db/token_usage.py |
| 运行活动和状态同步 | src/utils/task_activity.py |
| 优雅关闭、readiness、排空 | src/utils/graceful_shutdown.py、src/lifespan.py、src/agentos_main.py |
| checkpoint 语义快照与孤儿清理 | src/utils/workflow_checkpoint.py、src/lifespan.py |

## Synthesis

运行治理层的本质可以压缩成一句话：**它把一个能执行的 Agent 任务，变成一个在分布式运行环境中可被授权、暂停、恢复、取消、计费、观测并最终收敛的运行。**

最值得继续下钻的是三条跨层链路：

1. Workflow.acancel_run → cancel_registry → runtime → remote /cancel 的取消时序和竞态。
2. RunPaused → HitlSnapshot → Redis signal/claim → takeover → acontinue_run 的恢复状态机。
3. ModelRequestCompleted → _token_requests → calculate_token_cost → token_usage_log 的成本闭环。
