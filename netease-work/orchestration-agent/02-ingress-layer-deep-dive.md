---
tags: [netease, orchestration-agent, ingress-layer, agentos, fastapi, sse]
aliases: [Orchestration Agent 接入层深度分析]
---

# 接入层深度分析

## Layer Judgment

在本项目中，整体系统思想是：通过 `OrchestrationWorkflow` 把用户任务转换为可规划、可执行、可观察、可取消、可恢复的多智能体运行。

本篇选择接入层。它位于外部调用方与 Workflow 运行时之间，负责把 HTTP/Webhook 请求转换为合法的 Workflow run，并决定请求连接、后台执行、SSE 事件、重连、鉴权、健康状态和取消之间的关系。

本篇重点覆盖：代码实现、运行时通道、系统设计和失败模式；不深入 Loop Agent 的规划算法或远程 Agent 的内部执行算法。

## Core Idea

接入层的核心思想是：

> 接入层不执行任务本身，而是建立“请求身份 + Workflow run + 事件交付”的契约，并根据任务生命周期选择同步流、后台流或重连流。

它解决的不是“如何调用 FastAPI”，而是三个边界问题：

1. 外部短生命周期 HTTP 请求如何启动内部长生命周期 Workflow；
2. Workflow 事件如何以 SSE 方式实时可见并支持断线重连；
3. 取消、HITL、健康检查和优雅停机如何在入口处保持一致。

如果移除接入层，Workflow 仍可能在进程内运行，但外部系统无法安全地启动、鉴权、观察、恢复和停止它。

## 先用一条完整流程理解接入层

直白地说，接入层做的事情是：**把外部的一次请求，包装成一个可被系统持续管理的 Workflow run，并把这个 run 的过程和结果交还给调用方。**

以用户调用 `/runs` 为例，完整过程只有六步：

```text
1. 接收请求
   解析 workflow_id、session_id、user_id、输入内容和 stream/background 参数

2. 建立运行身份
   确认“谁”要调用“哪个 Workflow”以及“哪一个会话”，生成或接收 run_id

3. 选择执行交付方式
   普通模式：请求连接保持打开，边执行边返回 SSE
   background：请求可以立即结束，Workflow 在后台继续执行

4. 启动 Workflow
   接入层调用 OrchestrationWorkflow.arun，把输入和 session_state 交给编排层
   接入层不负责决定任务拆成哪些 Agent

5. 交付运行过程
   Workflow 产生计划、Agent 状态、文本增量、HITL 和错误事件
   接入层把事件发送到当前 SSE，并按 run_id/index 写入 event_buffer

6. 处理结束或中断
   完成：写入终态，返回最终结果
   断线：后台继续，调用方通过 /resume 补事件
   取消：根据 run_id 找到运行并触发取消
   draining：拒绝新任务，保留已有任务收尾
```

因此，接入层不是“把 HTTP 请求转发给 Agent”这么简单，而是在做一个**运行控制适配器**：

```text
外部协议 HTTP/Webhook
        ↓
运行协议 Workflow run + session + event stream
        ↓
内部编排协议 Workflow.arun / acontinue_run / acancel_run
```

### 接入层和编排层的分工

可以用两个问题区分它们：

| 问题 | 负责层 |
|---|---|
| 请求是否合法、用户有没有权限？ | 接入层 |
| 这次任务对应哪个 run/session？ | 接入层 |
| 客户端断开后任务是否继续？ | 接入层 |
| 如何把事件发给前端并支持重连？ | 接入层 |
| 用户目标要拆成哪些步骤？ | 编排层 |
| 每个步骤调用哪个 Agent？ | 编排层 |
| 子任务具体怎么完成？ | 执行层/数字员工 |
| 业务结果是否专业、准确？ | 专业数字员工 |

### `/runs`、`/continue`、`/cancel` 的角色

- `/runs`：创建并启动一次新的 Workflow run；
- `/continue`：向一个已经 paused 的 run 注入用户输入或 HITL 结果，让它继续；
- `/cancel`：将一个 run 推进到 cancelled，并向它的子 Agent/远程 run 传播取消；
- `/resume`：不是重新执行任务，而是从 event buffer 按序号补发已经产生但客户端错过的事件。

这四个入口共同构成一个长任务的生命周期，而不是四个互不相关的 API。

## Mechanism Priority Map

### Primary mechanisms

#### 1. AgentOS 原生 Workflow 路由

- 优先级：primary
- 作用：提供 `/workflows/{workflow_id}/runs`、`/resume`、`/cancel` 等标准运行入口。
- 核心思想：让 Workflow 遵循 Agno AgentOS 的统一 API/事件协议。
- 关键文件：`src/agentos_main.py`、`src/workflow/orchestration_workflow.py`

#### 2. Stream / Background 生命周期分流

- 优先级：primary
- 作用：把客户端连接生命周期与长任务执行生命周期解耦。
- 核心思想：SSE 只负责事件消费；background 模式将真正执行放入 detached asyncio task。
- 关键文件：`src/workflow/continue_background_mixin.py`、Agno 原生 Workflow router、`src/api/continue_background_router.py`

#### 3. 身份、资源权限与运行态传递

- 优先级：primary
- 作用：确保 Workflow、session、user、workflow_id 和请求权限在入口到执行层之间保持一致。
- 核心思想：入口校验资源权限，运行态通过 `session_state` 向下游传播。
- 关键文件：`src/api/continue_background_router.py`、`src/utils/cancel_user_context.py`、`src/workflow/orchestration_workflow.py`

### Secondary mechanisms

#### 4. Event buffer / SSE 重连

- 优先级：secondary
- 作用：保存带序号的事件，让断开的客户端按 index 补发事件。
- 关键文件：Agno `event_buffer`、`src/workflow/continue_background_mixin.py`

#### 5. Webhook 异步接入与幂等去重

- 优先级：secondary
- 作用：接收易协作事件，快速返回 202，在后台启动派单 Workflow。
- 关键文件：`src/api/yixiezuo_webhook_router.py`、`src/yixiezuo/dedup.py`

#### 6. Health / Drain 生命周期探针

- 优先级：secondary
- 作用：给 Kubernetes 提供存活、就绪和主动 drain 接口。
- 关键文件：`src/utils/graceful_shutdown.py`、`src/lifespan.py`

### Supporting mechanisms

- 自定义路由 prepend，覆盖 Agno 同路径 `/continue`；
- `EventStorageFilterMixin`，区分实时事件和持久化事件；
- cancel middleware，将用户信息放入取消上下文；
- lifespan 启动 Agent 同步、HITL reaper、checkpoint sweeper 和 tracing；
- CORS、HTTP client、OpenTelemetry 等应用级配置。

## Layer Problem

接入层承受的主要系统压力是：

| 压力 | 具体表现 |
|---|---|
| 生命周期不一致 | HTTP 请求通常几秒结束，Agent 任务可能运行数分钟甚至更久 |
| 事件交付 | LLM token、计划、Agent 状态和 HITL 事件需要实时推送 |
| 断线恢复 | 浏览器或网关断开不能等价于任务取消 |
| 权限边界 | `/runs`、`/continue`、`/cancel` 必须绑定正确的 workflow/run/session/user |
| 多 Pod | 续跑或 HITL 可能在不同 Pod 上发生 |
| 运维状态 | draining 时不能再接收新任务，但已有任务要尽可能完成 |
| 兼容性 | 项目需要扩展 Agno 原生路由，同时保持其他 Workflow 的默认行为 |

## Core Abstractions

### `AgentOS app`

- 表示：Agno 提供的 FastAPI 应用和标准 Agent/Workflow API。
- 拥有：原生 Workflow 路由、认证配置、应用生命周期基础。
- 不拥有：本项目的 webhook 业务语义、特殊 `/continue` background 逻辑。
- 相邻抽象：`OrchestrationWorkflow`、自定义 APIRouter。
- 代码：`src/agentos_main.py:166-177`

### `OrchestrationWorkflow`

- 表示：一个可运行的顶层 Workflow。
- 拥有：步骤执行、run 结果、事件流和取消后的业务状态处理。
- 不拥有：HTTP 请求参数解析和所有路由匹配。
- 相邻抽象：Agno Workflow router、`ContinueBackgroundMixin`。
- 代码：`src/workflow/orchestration_workflow.py:411`

### `run_id / session_id / workflow_id`

- `workflow_id`：被注册的 Workflow 身份，决定调用哪个 Workflow。
- `run_id`：一次执行实例身份，决定观察、继续或取消哪次运行。
- `session_id`：多轮会话和持久化上下文身份。

接入层必须避免把三者混用。`run_id` 负责运行实例，`session_id` 负责持久化会话，`workflow_id` 负责资源定位。

### `ContinueBackgroundMixin`

- 表示：对 Workflow continue 行为的后台化扩展。
- 拥有：detached task、SSE subscription、事件消费和终态收尾。
- 不拥有：通用 Workflow 计划和具体 Agent 执行。
- 相邻抽象：自定义 `/continue` router、Agno `acontinue_run`。
- 代码：`src/workflow/continue_background_mixin.py`

### `event_buffer`

- 表示：按 run 保存带 index 的事件缓冲。
- 拥有：事件顺序、重连补发和运行终态 TTL。
- 不拥有：完整业务结果和永久审计存储。
- 相邻抽象：SSE subscriber、Workflow session、数据库事件。

### Webhook adapter

- 表示：将外部易协作 payload 转换为内部派单 Workflow 输入。
- 拥有：JSON 校验、标准化、去重和后台启动。
- 不拥有：派单决策和实际创建 QA session。
- 代码：`src/api/yixiezuo_webhook_router.py`

## Main Flow

### 主用户请求

```text
HTTP POST /workflows/{workflow_id}/runs
  -> AgentOS 原生路由
  -> 认证 / 资源权限 / 参数解析
  -> Workflow.arun
  -> OrchestrationWorkflow.arun 强制 stream=True + stream_events=True
  -> Workflow steps
  -> SSE 事件 + event_buffer
  -> WorkflowCompleted/Error/Paused/Cancelled
```

`OrchestrationWorkflow.arun` 在 `src/workflow/orchestration_workflow.py:540` 附近统一打开事件流，因此调用方即使没有显式传入完整事件参数，项目仍以事件驱动方式运行。

### Background 主请求

Agno 原生 background 机制负责把 Workflow 运行与请求响应解耦。项目的历史/当前测试明确要求：`background=True` 且客户端断开后，后台 producer 仍继续到终态，事件进入 event buffer。

### Continue 请求

```text
POST /workflows/{workflow_id}/runs/{run_id}/continue
  -> 自定义路由优先匹配
  -> 校验 workflow/run/session/权限
  -> 检查 paused 和 continue lock
  -> background=true ? detached task : 原生同步 SSE
  -> event_buffer / subscriber / 原始 SSE
  -> /resume 按 index 重连
```

自定义路由只服务于当前 `OrchestrationWorkflow`；其他 Workflow 仍交给 Agno 原生路由。

### Webhook 请求

```text
POST /api/webhook/yixiezuo
  -> 解析 JSON
  -> 校验 group_name/webhook
  -> parse_payload 标准化
  -> Redis 指纹去重
  -> 写入 dispatch Workflow session_state
  -> asyncio.create_task
  -> 立即返回 202
```

Webhook 不等待派单 Workflow 的 LLM 和 create_session IO。

## Runtime Channel Map

| 信息类型 | 入口来源 | 传输/转换通道 | 运行时生效位置 | 保护机制 | 失败或丢失方式 |
|---|---|---|---|---|---|
| 用户输入 | `/runs` form/json | Agno request parser -> Workflow input | `TaskContext`、prompt | Pydantic/Workflow 输入校验、guardrail | 参数非法或安全检查失败 |
| `workflow_id` | URL path | 路由匹配 | 选择 Workflow、资源权限 | router path match、resource access | 找不到 Workflow 或路由落到错误实现 |
| `run_id` | URL/请求或框架生成 | Agno run context | run 状态、event buffer、cancel | run 存储和权限校验 | 运行不存在、session 不匹配 |
| `session_id` | 请求参数 | session lookup | Agno session、session_state | ownership 校验 | 缺失或查不到 session |
| `user_id` | JWT/request/query | auth dependency + cancel ContextVar | 资源权限、个性化和取消原因 | JWT/RBAC、middleware | 未认证、用户范围错误 |
| 事件 | Workflow/Agent 运行时 | event stream -> event buffer/SSE | 前端实时视图、重连补发 | event index、终态 sentinel、TTL | buffer 过期、事件过滤或客户端未重连 |
| `background` | form/query 参数 | router 分流 | detached asyncio task | task set、finally、终态写入 | 进程崩溃时内存任务丢失 |
| webhook payload | 外部 JSON | parse_payload -> session_state | 派单 Workflow steps | Pydantic/字段校验/去重 | 非法 payload、重复事件、后台异常 |
| drain state | health/lifespan | `GracefulShutdownManager` | 新请求接受与远程任务登记 | readiness、DrainingError | 已进入 drain 后新任务被拒绝 |

### 同一事件的多个通道

一个 Workflow 事件至少可能经过：

```text
事件对象
  -> async generator yield（当前连接可见）
  -> event_buffer（可重连）
  -> sse_subscriber_manager（其他订阅者）
  -> WorkflowRunOutput.events（部分事件持久化）
  -> TaskActivityTracker（业务状态快照）
```

这些通道保证不同：实时 SSE 断开可能丢当前连接数据，但 event buffer 可补发；数据库事件可能被合并或过滤；TaskActivity 只保留状态快照，不是完整事件日志。

## Mechanism Interrogation

### 1. `stream/background` 分流

**问题压力：** 长任务不能绑定 HTTP 连接生命周期。

**核心思想：** 把执行协程与事件消费连接拆开。

**触发：** `/runs` 或 `/continue` 收到 `background=True`；`/continue` 还根据 `stream` 决定是否保留原始 SSE 订阅。

**决策标准：**

- `background=False`：同步消费事件，保持原生 SSE 语义；
- `background=True, stream=True`：后台执行，同时可以向当前连接和重连订阅推送；
- `background=True, stream=False`：立即返回 202，后台执行。

**第一性目标 vs 实现代理：**

- 第一性目标：任务不因客户端断开而取消；
- 实现代理：`asyncio.create_task` + 全量消费事件 + event buffer。

**状态变化：** 创建 detached task，事件写入 buffer，最终状态写入 `set_run_completed`，释放 continue lock。

**可见输出：** 当前 SSE、`/resume` 补发事件、202 accepted/in_progress 响应和最终 run 状态。

**保护的不变量：** 客户端连接状态不决定 Workflow 是否继续执行。

**关键代码：** `ContinueBackgroundMixin.start_background_continue`、`_drive_background_continue`。

**关键限制：** detached task 仍是进程内内存任务；Pod 崩溃不能单靠它恢复执行，需要更高层任务持久化或重试机制。

### 2. 自定义 `/continue` 路由覆盖

**问题压力：** Agno 原生 `/continue` 不满足本项目 background/resume 语义，但不能破坏其他 Workflow 的原生行为。

**核心思想：** 构造只匹配当前 Workflow 的自定义 APIRoute，并把它 prepend 到 Starlette 路由表。

**触发：** 应用启动阶段注册路由；请求到达 `/workflows/{workflow_id}/runs/{run_id}/continue` 时进行匹配。

**决策标准：** URL path 中的 `workflow_id` 是否等于当前 `orchestrator.id`。

**状态变化：** 只有当前编排 Workflow 命中自定义路由；其他 workflow 返回 `Match.NONE`，交给原生路由。

**可见输出：** 本项目得到 background-capable `/continue`；其他 Workflow 行为不变。

**保护的不变量：** 自定义扩展不能扩大到所有 Workflow，也不能因路由顺序被 Agno 原生实现遮蔽。

**关键代码：** `src/api/continue_background_router.py:140`、`src/agentos_main.py:230`。

**关键限制：** 路由 prepend 依赖 Starlette 首匹配优先规则，属于框架路由内部行为；升级 Agno/FastAPI 后必须回归验证。

### 3. Webhook 去重后异步接收

**问题压力：** 外部 webhook 发送方需要快速得到 ack，同时派单过程包含 LLM 和远程 IO。

**核心思想：** 入口只做可信的解析、校验、去重和任务投递，不等待业务 Workflow 完成。

**触发：** POST 请求到 `/api/webhook/yixiezuo`。

**决策标准：**

- JSON 是否合法；
- `group_name`、`webhook` 是否存在；
- payload 是否能标准化；
- Redis 指纹是否已存在。

**状态变化：** Redis 写入去重 key；生成 `run_id`；构造 session_state；创建后台 task。

**可见输出：** 400 参数错误、200 duplicate 或 202 accepted。

**保护的不变量：** 同一个 webhook 事件在 TTL 内不重复派单；已接受请求不因 HTTP 返回而丢失本次进程内执行机会。

**关键代码：** `src/api/yixiezuo_webhook_router.py:34-180`、`src/yixiezuo/dedup.py`。

**关键限制：** `asyncio.create_task` 不是持久化队列；进程崩溃、滚动发布或 OOM 可能使已返回 202 的任务没有完成。

### 4. 事件持久化过滤与合并

**问题压力：** 流式 token 事件数量巨大，直接存数据库会膨胀内存和存储。

**核心思想：** 实时事件仍可发送，但持久化层合并连续内容增量并丢弃仅用于实时展示的事件。

**触发：** Workflow 处理每个事件和保存 session 时。

**决策标准：** 事件类型、run_id、agent_id/team_id 和 custom_event 类型。

**状态变化：** `WorkflowRunOutput.events` 内存列表中的连续内容增量被合并；部分 heartbeat/intermediate 事件不落库；event buffer/SSE 不受同样过滤影响。

**可见输出：** 前端仍可看到实时事件；数据库保存更紧凑的事件集。

**保护的不变量：** 持久化不会无限增长，同时不能因为 `events_to_skip` 误伤实时 SSE。

**关键代码：** `src/workflow/event_storage_filter.py`。

**关键限制：** 数据库历史不是完整实时事件重放日志；依赖事件分组字段正确，且框架事件模型变化会影响过滤逻辑。

## Algorithms

### Background execution selection

- Problem：连接断开不能取消长任务。
- Main idea：根据 `background`/`stream` 选择同步生成器或 detached producer。
- Priority：primary
- Trigger：`/continue` 表单参数，原生 `/runs` background 参数。
- Input：run_id、session_id、step requirements、background、stream。
- Output：SSE async iterator 或 202 JSON。
- Visible output：当前事件、event buffer 中的 indexed event、终态 sentinel。
- State written：后台 task set、event buffer、subscriber、run status、continue lock。
- Invariant：客户端生命周期与任务生命周期解耦。
- Failure：进程级 task 丢失、重复 continue、锁未释放或终态未写入。

### Route matching fallback

- Problem：只扩展目标 Workflow，避免覆盖所有原生路由。
- Main idea：先按 path 匹配，再按 `workflow_id == orchestrator.id` 过滤。
- Priority：secondary
- Trigger：每次 `/continue` 请求。
- Input：URL path 参数。
- Output：自定义 router 或 Agno 原生 router。
- State written：无持久化状态，只有路由选择。
- Invariant：其他 Workflow 保持原生语义。
- Failure：Workflow id 不一致、路由注册顺序改变、框架匹配规则变化。

### Webhook idempotency gate

- Problem：外部系统可能重试同一个 webhook。
- Main idea：标准化事件后计算指纹，以 Redis 原子标记作为派单闸门。
- Priority：secondary
- Trigger：每个 webhook 请求。
- Input：标准化 webhook event。
- Output：duplicate 或 accepted。
- State written：Redis dedup key、派单 Workflow session_state。
- Invariant：同一指纹在有效期内只触发一次派单。
- Failure：Redis 降级时可能放宽幂等；后台启动失败需要回滚 key，否则重试会被错误吞掉。

## System Design

## Invariants

- 请求中的 `workflow_id`、`run_id`、`session_id` 必须指向同一个合法运行对象；
- 资源权限检查不能因自定义路由而绕过；
- 客户端断开不能自动等价于 background 任务取消；
- background task 必须消费完整事件管道并写入终态；
- `/continue` 自定义扩展只作用于 `OrchestrationWorkflow`；
- 实时事件过滤不能影响 SSE/WebSocket/event buffer 的即时交付；
- Webhook 返回 202 后，去重状态和后台任务语义必须一致；
- draining 后不再接收新任务，但存量远程任务要进入等待/取消策略；
- cancel 请求携带的 user/session 信息必须能到达取消后的状态同步逻辑。

## Boundaries

接入层负责：请求解析、路由、认证依赖、资源权限、生命周期分流、事件交付、健康状态和入口级错误。

接入层不负责：Agent 选择、计划生成、远程任务业务逻辑、最终结果质量和专业领域校验。

跨层数据主要是：`workflow_id`、`run_id`、`session_id`、`user_id`、`session_state`、事件对象和终态状态。

## Tradeoffs

### 为什么复用 AgentOS 原生路由

优点是统一 API、认证、运行结果和事件协议，减少自定义协议数量；代价是项目必须理解并适配 Agno 的内部路由、事件和 session 行为。

### 为什么 background 使用进程内 detached task

优点是实现简单、延迟低、能立即复用当前 Workflow 实例和事件管道；代价是任务可靠性依赖进程存活，不能替代真正的分布式任务队列。

### 为什么 event buffer 与数据库分离

event buffer 面向短期实时重连，数据库面向会话和运行历史。两者生命周期、容量和完整性需求不同；代价是必须处理 TTL、索引、终态 sentinel 和持久化过滤之间的一致性。

### 为什么自定义 `/continue` 需要 prepend

因为 Agno 已经先注册同路径的原生路由；普通 `include_router` 会匹配到后面的自定义路由之前就结束。prepend 能覆盖目标路径，但增加了对框架路由顺序的隐式依赖。

## Code Implementation Map

### 应用组装

- 文件：`src/agentos_main.py`
- 函数/对象：`AgentOS(...)`、`app.include_router(...)`、route prepend
- 先读：`orchestration_workflow` 创建、lifespan 注入、自定义路由注册顺序
- 暂时跳过：模型 provider 适配和业务 Agent 实现

### 顶层 Workflow 接入契约

- 文件：`src/workflow/orchestration_workflow.py`
- 重点：`arun`、`acancel_run`、`initialize_workflow`、事件适配方法
- 重要字段：`session_id`、`run_id`、`session_state`、`event_buffer`

### Continue 扩展

- 文件：`src/api/continue_background_router.py`
- 重点：`get_continue_background_router`、自定义 route class、continue endpoint、checkpoint ownership 校验
- 关注：认证依赖、resource access、paused 检查、continue lock、background 分流

### Background producer

- 文件：`src/workflow/continue_background_mixin.py`
- 重点：`start_background_continue`、`_drive_background_continue`、`ContinueSSESubscription`
- 关注：事件消费、订阅发布、终态写入、锁释放和异常收尾

### Webhook

- 文件：`src/api/yixiezuo_webhook_router.py`
- 重点：`_yixiezuo_webhook_route`
- 关注：payload 校验、dedup、session_state、202 返回和失败回滚

### 健康与生命周期

- 文件：`src/utils/graceful_shutdown.py`、`src/lifespan.py`
- 重点：`/health/live`、`/health/ready`、`/health/drain`、lifespan 启停顺序
- 关注：readiness 与 liveness 的区别、draining、远程任务等待、HITL reaper

## Failure and Cost Model

### 正常失败

- 参数不合法：路由层返回 400；
- 未认证/无权限：认证依赖或资源权限返回 401/403；
- Workflow/session/run 不存在：404；
- run 未暂停却 continue：409；
- checkpoint 不可用：503；
- 服务 draining：新任务在 Workflow 准备阶段被拒绝；
- webhook 重复：200 duplicate，不重复派单。

### 降级行为

- 当前 SSE 连接断开：background 模式继续，前端通过 `/resume` 或 event buffer 重连；
- Redis dedup 降级：请求可能继续接受，但幂等保证可能降低；
- event buffer 过期：无法补发历史事件，只能读取最终 run/session 状态；
- 后台 task 异常：HTTP 已返回后只能记录日志、回滚去重或写入错误终态；
- tracing/export 失败：不应阻断主业务，但会损失观测数据。

### 性能和运维成本

- 每个长任务需要 asyncio task、事件缓冲和可能的 Redis 订阅资源；
- 高频 token 事件会产生事件分发压力，因此需要持久化层合并；
- 多 Pod continue 需要分布式锁，避免同一 paused run 被重复恢复；
- `health/ready` 是流量摘除信号，不能简单等同于进程存活；
- detached task 让应用内存成为任务可靠性的边界。

### 安全成本

- 自定义路由必须复用 Agno 认证和 RBAC dependency；
- cancel middleware 读取 query 中 user/session 信息，必须防止伪造导致错误状态同步；
- webhook `request_token` 会进入派单 Workflow 的 session_state，只能在受信任调用方边界使用；
- 内部 additional input 和系统消息不能通过 SSE 泄露。

## Evolution

### 稳定设计

- AgentOS 作为标准服务入口；
- Workflow run + session + event stream 的主模型；
- `/health/live`、`/health/ready`、draining 生命周期；
- Webhook 接收与派单 Workflow 分离。

### 过渡/兼容设计

- 自定义 `/continue` 通过 prepend 覆盖 Agno 原生路由；
- `ContinueBackgroundMixin` 是对 Agno continue 语义的扩展；
- `EventStorageFilterMixin` 通过临时控制 `store_events` 适配框架持久化行为；
- 仓库中同时存在旧 HITL takeover 路径和新 Redis signal 路径，测试明确标注部分 legacy 路径不可达。

### 未来方向推断

从当前代码的复杂度看，接入层未来最值得演进的是：将后台长任务从进程内 task 提升到可恢复的外部任务协调机制，并进一步明确实时事件、持久化历史和最终状态的协议边界。这是架构推断，不是当前已实现功能。

## Current Gaps and Evolution

### 当前主要问题

#### 1. 长任务可靠性依赖进程内 Task

background 和 webhook 当前通过 `asyncio.create_task` 执行。进程重启、Pod 崩溃或 OOM 后，已经返回 202 的任务可能丢失。

这意味着当前的 202 更准确地表示“任务已提交到当前进程”，还不等价于“任务已可靠进入持久化任务系统”。

#### 2. 事件存在多套真相来源

同一个运行过程可能同时进入：

```text
SSE
event_buffer
sse_subscriber_manager
WorkflowRunOutput.events
TaskActivityTracker
```

它们的生命周期和过滤规则不同，可能导致：前端看到了但数据库没有、数据库有记录但 SSE 已过期、运行结束但活动状态仍为 running，以及重连事件重复或缺失。

#### 3. 自定义路由依赖框架内部注册顺序

自定义 `/continue` 通过 prepend 覆盖 Agno 原生路由。这解决了当前扩展需求，但依赖 Starlette 的首匹配规则和 Agno 当前路由注册顺序。框架升级后必须重新验证路由优先级、认证依赖和其他 Workflow 的匹配行为。

#### 4. 接入层职责逐渐变重

当前接入相关代码同时处理路由、权限、SSE、background、event buffer、checkpoint、HITL、取消、draining 和持久化过滤，已经从单纯的入口适配器演进成运行控制层，模块之间存在较强耦合。

#### 5. Webhook 的异步接收缺少外部持久化队列

Webhook 经过校验和去重后立即创建进程内后台任务。如果后台任务启动失败，代码会回滚 dedup key，允许外部重试；但在进程整体崩溃时，已经返回的 202 仍可能无法恢复。

#### 6. 取消和恢复存在分布式竞态

当前取消依赖：

```text
进程内 cancel_registry
  + Redis HITL signal
  + 远程 cancel API
```

它可以覆盖主要路径，但仍需处理子 run 尚未登记、多 Pod 同时 continue、远程已结束后才收到 cancel，以及 signal、run status、业务状态更新时序不一致等情况。

### 演进方向

#### 第一阶段：统一 Run 状态协议

先定义清晰的状态集合：

```text
accepted -> running -> paused -> completed
                    ├-> failed
                    ├-> cancelled
                    └-> expired
```

同时明确：

- 哪个组件是最终状态来源；
- 哪些事件必须持久化；
- 哪些事件只用于实时展示；
- `/resume` 是补发事件还是读取最终状态；
- 每种状态允许哪些迁移。

优先解决多套状态来源造成的不一致。

#### 第二阶段：抽象统一 Run Gateway

将 `/runs`、`/continue`、`/cancel`、`/resume` 的公共逻辑收敛为统一服务：

```text
RunGateway
  - create_run
  - continue_run
  - cancel_run
  - resume_events
  - get_run_status
```

路由只负责 HTTP 参数转换，Gateway 负责身份绑定、权限校验、run/session 校验、状态迁移、事件订阅和错误映射。这样可以降低对 Agno 原生路由内部实现的依赖。

#### 第三阶段：外部化长任务执行

将进程内 detached task 演进为可恢复的任务协调机制：

```text
API 接入
  -> 持久化 Run
  -> 投递任务队列
  -> Worker 执行 Workflow
  -> 事件写入事件存储
  -> SSE /resume 订阅事件
```

目标是支持 Pod 重启恢复、跨 Pod 调度、失败重试和可靠的 webhook 202 语义。

#### 第四阶段：分离事件日志与状态视图

明确拆分四类对象：

```text
Run State：当前状态，单一真相
Event Log：完整事件记录
Activity View：前端任务摘要
SSE Stream：实时交付通道
```

SSE 不再承担持久化职责，TaskActivity 不再承担完整事件日志职责，event buffer 只作为短期重连和实时交付设施。

#### 第五阶段：标准化取消和 HITL 命令

将用户取消、HITL 超时、跨 Pod cancel 和远程取消统一为命令模型：

```text
CancelCommand(run_id, reason, source)
  -> 更新 Run 状态
  -> 唤醒本地等待
  -> 取消子 run
  -> 通知远程 run
  -> 写入终态事件
```

resume、timeout、cancel 也可以沿用同一套命令和状态迁移规则，降低多通道竞态。

### 当前架构到目标架构

```text
当前：
HTTP 路由
  -> 进程内 Workflow task
  -> 多通道事件同步

目标：
HTTP 接入
  -> 统一 Run Gateway
  -> 持久化 Run + 外部任务协调
  -> 统一状态机
  -> 事件日志 + SSE 订阅
```

### 演进判断

当前接入层最大的问题不是功能缺失，而是它已经承担了长任务运行时职责，但运行状态、事件、任务可靠性和路由扩展仍分散在多个组件中。

因此最重要的方向不是继续增加更多路由，而是先统一 Run 状态和事件协议，再把长任务执行从进程内生命周期逐步提升为可恢复的外部运行时。

## Synthesis

接入层的价值在于把“一个 HTTP 请求”提升为“一个可治理的 Workflow run”：它建立身份、权限、连接、事件、重连、取消和运维状态之间的契约。

它让上层编排器可以专注于任务规划，让下层执行器可以专注于 Agent 运行；其主要代价是必须同时维护 Agno 原生协议、FastAPI 路由规则、SSE/event buffer、Redis 信号和进程生命周期。

下一步建议深入：`OrchestrationWorkflow` 的事件管道与 `ContinueBackgroundMixin`，因为接入层的核心复杂度最终都集中在“事件如何从 Workflow 运行变成可靠的外部可见状态”。
