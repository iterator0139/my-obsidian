# 基础设施层深度分析

## Layer Judgment

前面几层解决“请求怎么进来、任务怎么运行、Agent 怎么规划和执行、运行时怎么治理”。基础设施层解决的是：这些能力依赖的状态、消息、外部服务和执行环境，如何被可靠地提供。

它不是业务层，也不是 Agent 决策层，而是把进程内逻辑接到真实系统资源上的一层：

    配置
      -> 数据库、Redis、外部平台客户端、Sandbox、观测组件
      -> Workflow session、事件流、控制信号和隔离执行环境
      -> 健康检查、连接池、TTL、降级和关闭流程

## 先用一条完整流程理解基础设施层

一个任务从进入服务到完成，基础设施层大致这样工作：

1. 启动时读取环境变量，选择 dev、default 或 prod 配置。
2. 创建并缓存数据库对象，初始化 Redis event buffer、SSE subscriber、checkpoint repository 和外部客户端。
3. Workflow 把会话、计划、结果和审计事件写入数据库；高频实时事件先进入 Redis Stream，再由 SSE 推给前端。
4. HITL、取消、去重和接管通过 Redis 的 pending、signal、lock 和 TTL 在多个 Pod 间协同。
5. Agent 同步器从 MultiAgentWeb 获取数字员工，模型价格在算费前从同一平台加载并短时缓存。
6. 需要执行代码或文件操作时，通过 Sandbox 客户端连接隔离环境，复用连接并处理断线。
7. 下线时停止后台任务、摘除 readiness、等待资源完成；基础设施故障则按能力选择失败、降级或重试。

这一层的核心价值是：**把“进程内可以运行”变成“多实例部署下可以持续运行”。**

## Core Idea

基础设施层按数据和可靠性需求分流，而不是所有东西都写进同一个数据库：

- 数据库负责长期、可查询、可审计的会话和业务记录。
- Redis 负责低延迟、跨进程、带 TTL 的运行时状态和事件流。
- 外部平台 API 负责 Agent 注册、价格、工作空间和鉴权材料。
- Sandbox 负责把代码执行隔离到独立环境。
- 进程内缓存只保存可重建的数据，例如 DB 实例、Sandbox 连接、价格和签名 token。

关键判断是：**Redis 在这里不只是缓存，而是事件传输和分布式运行协调基础设施；数据库也不只是日志，而是 Workflow 可恢复和可审计的事实存储。**

## Mechanism Priority Map

### Primary mechanisms

1. 持久化与事件基础设施：数据库保存 session、token usage、checkpoint 和审计事件；Redis Stream 支持事件回放、跨进程 SSE 和长任务。
2. 分布式协调：Redis pending、signal、lock、TTL 支撑 HITL、取消、接管、去重和 continue 互斥。

### Secondary mechanisms

3. 外部平台访问：MultiAgentWebClient 连接 Agent 注册、价格、工作空间和远程服务。
4. 隔离执行环境：Sandbox client/session 管理代码执行环境的连接、缓存、断线重连和资源回收。
5. 配置和生命周期组装：configuration.py、lifespan.py 和 agentos_main.py 决定部署拓扑。

### Supporting mechanisms

6. 连接池、事件压缩、TTL 和大小限制，控制延迟、内存和存储成本。
7. 健康检查、监控和可观测性，让 Kubernetes 和运维系统知道实例是否能接流量。

## Core Abstractions

### Configuration / DbConfiguration

Configuration 是部署参数入口；DbConfiguration 根据 URL 选择 SQLite、同步 PostgreSQL 或异步 PostgreSQL，并缓存 DB 实例。它拥有依赖组装，不拥有业务状态。

### RedisEventsBuffer / RedisSSESubscriberManager

RedisEventsBuffer 把 run 事件写入 Redis Stream，并维护 run 元数据和 TTL；SSE subscriber 从同一 Stream 读取并推送。前者是实时层，后者是消费适配器，都不替代数据库持久化。

### AgentRunCheckpointRepository

以不可变坐标保存经过白名单投影的语义 checkpoint。它拥有 schema 初始化、冲突检测和精确删除，不保存完整私密上下文。

### MultiAgentWebClient

连接平台控制面，承担 Agent 查询/同步、模型价格、签名密钥、会话和工作空间等外部调用，不负责编排决策。

### SandboxSession / SandboxClient

是隔离执行环境的连接门面。进程内缓存按 sandbox_id 复用连接，LRU 超限淘汰；连接级异常触发失效和重连，业务错误不应误判为断线。

## Main Flow

### 1. 配置和数据库

configuration.py 从环境变量读取数据库 URL、Redis URL、Cluster 开关、事件大小上限、HITL TTL、优雅停机和 JWT 配置。数据库 URL 自动解析为对应 Agno DB 实现；同一 DbConfiguration 缓存 DB 对象，避免重复创建 engine 和连接池。

生产通常使用 PostgreSQL，本地或测试可使用 SQLite。Redis 未配置时 event buffer 可以退回进程内实现，但跨 Pod 事件回放、HITL 协同和分布式取消能力会下降。

### 2. 事件写入和读取

一个 run 的事件经过序列化、字段缩写和公共上下文抽取后，写入 agno:events:{run_id} Stream，同时更新 agno:run:{run_id} 元数据。SSE subscriber 用 XREAD 读取；前端断线后可以按游标或历史回放。

运行中、paused、completed/error/cancelled 使用不同 TTL。大事件超过上限时截断 content/result，防止异常输出撑爆 Redis；终态事件短暂保留，过期后回退数据库。

EventStorageFilterMixin 又对数据库路径做第二层治理：连续内容增量按 run_id 合并，心跳和只用于实时展示的事件不落库。因此“实时看到”和“长期保存”是两种不同语义。

### 3. 分布式控制

HITL registry 使用 Redis 保存 snapshot、resume mailbox、signal、workflow 索引和 takeover/continue 锁。状态转换通过 Lua 或条件操作完成，TTL 防止崩溃后永久残留。取消信号使用可消费的 signal list，而不是断连即丢消息的 Pub/Sub。

易协作 webhook 去重使用 Redis SET NX EX；Redis 不可用时选择放行，避免基础设施故障导致业务事件丢失，但代价是可能重复处理。

### 4. 外部平台和模型价格

AgentSyncScheduler 周期性调用 MultiAgentWebClient，把在线 Agent 信息同步进本地 agent store；规划从本地 store 读候选 Agent，而不是每次规划都同步远程平台。

算费前，QaAgentPricingStrategy 从平台批量加载模型价格并缓存约一小时。价格缓存不是账本，最终费用仍写入 token_usage_log。

### 5. 隔离执行环境

SandboxSession 按 sandbox_id 获取隔离环境，进程级缓存维护连接 LRU 和能力探测结果。连接操作放在锁外，避免网络 RTT 阻塞其他用户；并发创建时 double-check，避免重复连接。连接级错误会 drop 并重连，超过容量则关闭最旧连接。

## Runtime Channel Map

| 信息/能力 | 基础设施通道 | 持久性和保护 | 主要失效方式 |
|---|---|---|---|
| Workflow session | Agno DB：PostgreSQL/SQLite | 长期存储，可查询 | DB 不可用 |
| 必要事件审计 | DB events，经合并和过滤 | 长期但压缩 | 过滤规则过宽 |
| 实时 run 事件 | Redis Stream | TTL、游标、终态哨兵 | Redis 故障或 TTL 到期 |
| SSE 跨 Pod 订阅 | RedisSSESubscriberManager | Stream 回放 | 保留窗口过期 |
| HITL snapshot | Redis pending hash | TTL、deadline、takeover lock | 数据过期或不完整 |
| 取消/继续信号 | Redis list + 状态字段 | 原子 claim、signal TTL | Redis 不可用 |
| Agent 注册信息 | MultiAgentWeb + 本地 store | 周期刷新 | 数据陈旧或同步失败 |
| 模型价格 | 平台 API + 进程缓存 | 缓存 TTL | 价格旧或服务不可达 |
| checkpoint | agent_run_checkpoints 表 | 不可变坐标、唯一约束 | schema 不兼容 |
| 代码执行 | Sandbox 服务 + 连接 LRU | 隔离、连接回收 | 服务不可达或连接断开 |

## System Design and Invariants

### 数据库和 Redis 不能互相替代

数据库擅长一致查询、长期存储和审计；Redis 擅长低延迟、TTL、原子状态转换和流式消费。把所有事件写 DB 会增加写放大；把所有事实放 Redis 又会失去长期可靠性和复杂查询能力。

### 事件要做分层处理

运行时事件首先要实时到达前端；数据库又不能保存每个 token 增量；Redis 还要在网络重连时回放。因此代码分别做实时写入、内存事件合并、数据库持久化过滤。一个事件在不同通道的保留语义不同。

### 基础不变量

- 任何需要跨 Pod 共享的控制状态不能只放 Python dict 或 ContextVar。
- Redis 临时 key 必须有 TTL；业务 deadline 和存储 TTL 是两套保护。
- Redis 的阻塞读取必须使用异步客户端，不能阻塞事件循环。
- DB 写入需要幂等键或唯一约束，尤其是 token usage、checkpoint 和 webhook。
- 事件实时通道可以降级，但关键业务状态和费用不能默默丢失。
- Agent 注册和价格缓存必须允许刷新、失效并标记陈旧。
- Sandbox 连接必须在异常时失效，在淘汰时关闭。

## Failure and Cost Model

- PostgreSQL 不可用时 session、审计和费用写入受影响，应通过 readiness 或明确错误暴露。
- Redis 不可用时跨 Pod SSE、HITL 接管、取消和去重会降级。
- Redis Stream 事件过大时会被截断，代价是回放内容可能不完整。
- 外部平台超时时，Agent 同步可能继续使用旧快照；价格服务失败必须告警并有明确算费策略。
- Sandbox 连接断开时只对连接级异常重连，业务异常应原样反馈。
- Pod 崩溃时 Redis/DB 中的持久化状态有机会恢复，但进程内缓存、未提交事件和未完成补偿可能丢失。

运行成本主要来自 Redis Stream 和控制 key 的内存、PostgreSQL session/事件/token/checkpoint 的存储，以及外部同步和 Sandbox 连接。事件合并、字段压缩、TTL 和 LRU 都是在可靠性与成本之间做的平衡。

## Evolution

### 当前主要问题

1. Redis 同时承担事件、SSE、HITL、取消和去重，共享故障域。
2. Redis 实时层与数据库审计层存在短暂不一致窗口，需要多处关联 run_id/session_id。
3. Agent 注册和价格是缓存/周期同步，存在陈旧窗口。
4. 配置项较多且主要由环境变量管理，错误配置可能运行到特定路径才暴露。
5. “放行”或“回退内存”的降级策略保住可用性，但可能降低幂等性和跨实例一致性。
6. Sandbox 目前主要治理连接，还不是统一的执行资源配额与租约控制面。

### 演进方向

- 按职责拆分 Redis namespace、容量和监控，必要时将事件流与控制面 Redis 分离。
- 为关键事件和费用增加 outbox/补偿机制，明确 DB、Redis、SSE 的事实优先级。
- 建立启动期配置 schema 校验、依赖连通性检查和安全默认值。
- 为 Agent registry、价格和 workspace 引入版本号、更新时间和 stale 标记。
- 为 Sandbox 增加并发数、CPU、内存、超时和租约等资源治理。
- 建立事件可见延迟、取消传播延迟、HITL 恢复成功率、DB/Redis 错误率和 Sandbox 连接成功率等基础设施 SLO。

## Code Implementation Map

| 能力 | 主要代码 |
|---|---|
| 配置和 DB 选择/缓存 | src/configuration.py |
| Redis 事件 Stream、TTL、序列化 | src/redis_event_buffer.py |
| 跨进程 SSE 订阅 | src/redis_event_buffer.py 的 RedisSSESubscriberManager |
| HITL、取消、signal、锁 | src/utils/hitl_registry.py、src/utils/hitl_reaper.py |
| DB checkpoint | src/db/agent_run_checkpoint.py、src/utils/workflow_checkpoint.py |
| 事件持久化过滤和合并 | src/workflow/event_storage_filter.py |
| Agent 周期同步 | src/registry/sync.py |
| 外部平台调用 | src/utils/multiagentweb_client.py |
| token 价格与记账 | src/utils/token_cost_tools.py、src/db/token_usage.py |
| Sandbox 连接和缓存 | src/sandbox/sandbox_client.py、src/sandbox/sandbox_session.py |
| 启动、后台任务和停机 | src/lifespan.py、src/agentos_main.py |

## Synthesis

基础设施层的本质是：**为上层 Agent 系统提供正确的存储、消息、协调、外部依赖和隔离执行环境，并明确每种数据在故障时如何降级。**

从整体架构看：数据库是长期事实和审计，Redis 是实时事件与分布式控制，外部平台提供动态注册/价格/身份材料，Sandbox 提供隔离执行资源，配置和健康机制把它们组装成可部署服务。

最值得继续下钻的是 RedisEventsBuffer 的 Stream/TTL/SSE 回放、HITL Registry 在 Redis Cluster 下的原子状态机，以及 PostgreSQL session、checkpoint、token usage 和事件审计之间的一致性边界。
