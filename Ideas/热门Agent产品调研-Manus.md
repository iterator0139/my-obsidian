# 热门 Agent 框架深度调研（机制拆解 + 对比分析）

> 版本目标：从“产品介绍”升级为“核心机制视角”。  
> 覆盖对象：`Codex`、`Claude Code`、`Hermes Agent`、`OpenClaw`（并补充 `Manus/ChatGPT Agent` 作为产品化参照）。

---

## 0. 先给结论（架构视角）

- 如果你要的是**软件工程代理中枢**：优先看 `Codex`（核心是可复用 harness + App Server 协议层）。
- 如果你要的是**IDE/终端内高安全自治编码**：优先看 `Claude Code`（核心是权限系统 + hooks + sandbox）。
- 如果你要的是**长期运行且会“积累技能”的自托管 Agent**：优先看 `Hermes Agent`（核心是 learning loop + skills + 分层记忆）。
- 如果你要的是**多渠道入口 + 常驻网关 + 路由控制平面**：优先看 `OpenClaw`（核心是 Gateway WS 协议 + session routing）。
- `Manus/ChatGPT Agent` 更偏交付产品体验，适合快速产出；上面四个框架更偏“可编排系统能力”。

---

## 1) 统一分析框架：看 Agent 必看哪 6 层

为避免“功能清单式分析”，本文固定使用 6 层机制框架：

1. **执行循环层**：单轮/多轮如何推进任务（agent loop）。
2. **上下文层**：提示词、历史、压缩(compaction)如何管理。
3. **工具调度层**：tool registry、并发/串行、失败重试如何做。
4. **权限安全层**：审批模式、策略优先级、沙箱边界。
5. **状态记忆层**：会话状态、跨会话记忆、技能沉淀如何持久化。
6. **运行时与接口层**：CLI/IDE/Cloud/Gateway 的控制平面协议。

---

## 2) 单框架深度拆解

## 2.1 Codex（OpenAI）

### a) 本质定位
`Codex` 的本质不是一个“聊天模型”，而是一个**可跨终端、IDE、云端复用的 agent harness**。  
OpenAI 官方明确把核心称为 Codex harness（agent loop + execution logic），并通过 App Server 作为协议中枢。

### b) 核心机制
- **执行循环层**：通过 Responses API 驱动“模型输出 -> 工具调用 -> 结果回注 -> 继续迭代”的 loop。
- **上下文层**：支持会话压缩/上下文整理，避免长任务耗尽上下文窗口。
- **工具调度层**：工具来源三类：内建工具、Responses API 提供工具、MCP 工具。
- **权限安全层**：本地执行有沙箱隔离（不同平台机制不同），并通过审批/策略控制高风险动作。
- **运行时与接口层**：`codex app-server` 采用双向 JSON-RPC，支持多客户端并发接入；同一线程可被 IDE/CLI/桌面面板统一控制。

### c) 关键独特点
- 把“agent 能力”抽成协议化中枢，便于多产品面统一复用。
- Cloud task 模式天然支持并行任务隔离（每任务独立沙箱）。

### d) 代价与风险
- 优势是一致性和扩展性，代价是架构复杂度上移（线程管理、协议一致性、权限策略一致性）。

---

## 2.2 Claude Code（Anthropic）

### a) 本质定位
`Claude Code` 是**以安全可控为一等公民的编码代理运行时**，不是“会写代码的聊天壳”。

### b) 核心机制
- **执行循环层**：围绕 query loop（模型决策 + 工具执行 + 反馈）持续迭代，直到 `end_turn` 或停止条件。
- **上下文层**：通过上下文组装与压缩机制，维持长会话任务可持续执行。
- **工具调度层**：文件、Shell、搜索、子代理等以统一工具抽象暴露；支持 MCP 扩展。
- **权限安全层（最强项）**：
  - 默认谨慎模式（高影响操作需审批）。
  - allow/ask/deny 规则和 mode 组合。
  - 多级配置（managed/user/project/local）叠加与优先级治理。
  - shell sandbox 进一步提供 OS 级边界，不只靠“规则匹配”。
- **状态层**：会话轨迹、配置和上下文文件共同塑造长期协作行为。

### c) 关键独特点
- “规则系统 + 交互审批 + sandbox”三层叠加，是企业落地最关键的一环。
- 对“自治程度”可细粒度调节（从只读 plan 到高自治模式）。

### d) 代价与风险
- 配置能力强，但策略体系本身有学习成本；治理不当会出现“要么太保守、要么过放开”的摆动。

---

## 2.3 Hermes Agent（Nous Research，开源）

### a) 本质定位
`Hermes Agent` 的核心不是“多工具”，而是**长期运行 + 自我改进**：  
把短期会话能力升级为长期复利能力（skills/memory 累积）。

### b) 核心机制
- **执行循环层**：标准 agent loop，但强调长期服务模式（可常驻、可消息入口、可定时任务）。
- **上下文层**：稳定前缀 + 动态能力注入（工具与技能按需进入上下文）。
- **工具调度层**：内建工具 + MCP 扩展 + 可委派子代理。
- **状态记忆层（最强项）**：
  - Durable memory（稳定偏好与用户画像）。
  - 会话历史检索（含全文检索能力）。
  - Procedural memory（技能文档）可被自动创建与复用。
- **学习闭环层**：
  - 做成任务 -> 归纳步骤 -> 写入 skill -> 后续优先复用并改进。
  - 这是它和“只会临场推理的 agent”最大机制差异。

### c) 关键独特点
- 重点不是一次任务成功率，而是“同类任务随时间变快变稳”。
- 适合“知识流程可沉淀”的团队（运营、研究、重复分析链路）。

### d) 代价与风险
- 记忆与技能沉淀越强，治理越重要（版本漂移、错误经验固化、技能污染）。

---

## 2.4 OpenClaw（开源）

### a) 本质定位
`OpenClaw` 是**Gateway-first 的个人/团队 Agent 控制平面**：  
先解决“多渠道接入与会话路由”，再解决“单个 agent 推理能力”。

### b) 核心机制
- **运行时与接口层（最强项）**：
  - 单一 Gateway 作为控制平面（WS 协议）。
  - 客户端在握手时声明 role/scope（operator/node）。
  - 请求/响应/事件是 typed schema 驱动，便于生态集成。
- **会话路由层**：
  - DM/群组/房间/cron/webhook 分不同 session 语义。
  - Session 生命周期与清理策略内建，适合常驻运行。
- **工具与节点层**：
  - 支持节点能力（如设备、画布、系统动作）通过网关编排。
- **状态层**：
  - session store + transcript 持久化，形成可回放与可运维对象。

### c) 关键独特点
- 它是“Agent 网络入口系统”，不是单纯“智能体内核”。
- 强项在于可接入性、可路由性、常驻运维性。

### d) 代价与风险
- 网关是单点关键组件，需重点做高可用与访问控制。
- 渠道越多，权限域和密钥治理越复杂。

---

## 2.5 Manus / ChatGPT Agent（产品化参照）

### a) 本质定位
- `Manus`：交付导向，面向“非工程用户的一句话任务执行”。
- `ChatGPT Agent`：通用任务代理 + ChatGPT 生态连接器 +（组织版）workspace agent。

### b) 机制特点（与框架型产品对比）
- 有 agent loop、工具调用、浏览器/文件系统，但底层细节多封装在产品内。
- 优点是上手快、交付快；缺点是可编排深度与运行时可控性通常弱于框架型方案。

---

## 3) 横向机制对比（深度版）

## 3.1 架构层对比表

| 机制层 | Codex | Claude Code | Hermes Agent | OpenClaw | Manus/ChatGPT Agent |
|---|---|---|---|---|---|
| 执行循环 | 强（harness 标准化） | 强（query loop + 工具循环） | 强（长期运行导向） | 中（更偏网关编排） | 强（产品封装） |
| 上下文压缩 | 强（长任务会话管理） | 强（压缩 + 组装） | 中高（稳定前缀 + 动态注入） | 中（以会话存储为主） | 中（平台内黑盒） |
| 工具系统 | 强（内建 + API + MCP） | 强（内建 + MCP + hooks） | 强（工具集 + delegation + MCP） | 中高（网关能力 + runtime tools） | 中高（够用但可编排受限） |
| 权限/安全 | 中高（依赖配置与沙箱） | 很强（规则 + mode + sandbox） | 中（可做但治理要自建） | 中高（网关边界清晰） | 中（平台策略主导） |
| 记忆/持久化 | 中（会话为主） | 中（会话与配置主导） | 很强（memory + skills 闭环） | 中高（session 与路由状态） | 中（平台能力为主） |
| 控制平面 | 强（App Server/多端） | 中（偏本地开发体验） | 中（CLI/网关并存） | 很强（Gateway-first） | 中（产品界面主导） |

## 3.2 “最小不可再分”核心差异

- `Codex`：**把 agent 内核协议化**（harness + App Server）。
- `Claude Code`：**把自治风险治理产品化**（permission stack）。
- `Hermes`：**把经验沉淀机制化**（skills 自增长闭环）。
- `OpenClaw`：**把多入口编排系统化**（Gateway WS control plane）。
- `Manus/ChatGPT Agent`：**把结果交付消费化**（低门槛高产出）。

---

## 4) 适用场景与不适用场景（决策版）

## 4.1 适用场景映射

- **研发团队（代码任务为主）**：`Codex` / `Claude Code`
- **需要强安全边界的企业编码环境**：优先 `Claude Code`
- **长期知识工作自动化（会反复做同类任务）**：优先 `Hermes`
- **多聊天渠道统一接入（客服/个人助理/团队入口）**：优先 `OpenClaw`
- **业务侧快速出成果（报告/PPT/分析）**：优先 `Manus/ChatGPT Agent`

## 4.2 不适用场景

- 没有治理能力却直接上线高自治 agent（任何框架都高风险）。
- 强合规行业里没有审计链路却放开写操作和外部调用。
- 把“生成快”误当“系统可控”。

---

## 5) 成本与风险（机制导向）

## 5.1 成本结构

- `Codex/Claude Code`：工程接入成本中等，收益在研发效率和协作闭环。
- `Hermes/OpenClaw`：自托管与运维成本更高，但换来长期可控与可复利能力。
- `Manus/ChatGPT Agent`：引入最快，但对底层机制控制力相对有限。

## 5.2 主要风险

- **正确性风险**：长链任务中间步骤偏差不易被发现。
- **自治风险**：权限放开后错误动作放大。
- **记忆污染风险**：错误经验写入长期记忆导致系统性偏差。
- **供应链风险**：第三方工具/插件带来不可预期行为。
- **运维风险**：网关型架构会出现会话积压、节点失活、通道波动等问题。

---

## 6) 选型建议（你这类“要深度分析”的使用场景）

如果你的目标是“做一套能长期演进的 agent 能力”而不是只做一次报告：

1. **底座优先级**：先定控制平面（Codex App Server 路线 or OpenClaw Gateway 路线）。
2. **安全优先级**：借鉴 Claude Code 的权限分层设计，先有边界再提自治。
3. **复利优先级**：引入 Hermes 风格的技能沉淀机制，把成功路径产品化。
4. **交付优先级**：业务端可并行使用 Manus/ChatGPT Agent 快速出结果，作为短期增益层。

建议采用“**双层架构**”：
- 上层：交付型 Agent（Manus/ChatGPT Agent）服务业务快产出。
- 下层：框架型 Agent（Codex/Claude Code/Hermes/OpenClaw）建设组织长期能力。

---

## 7) 资料来源（以官方资料优先）

- OpenAI Codex（官方）  
  - <https://openai.com/index/introducing-codex/>  
  - <https://openai.com/so-DJ/index/unrolling-the-codex-agent-loop/>  
  - <https://openai.com/so-DJ/index/unlocking-the-codex-harness/>
- Claude Code（官方）  
  - <https://www.anthropic.com/product/claude-code>  
  - <https://code.claude.com/docs/en/security>
- Hermes Agent（官方）  
  - <https://github.com/NousResearch/hermes-agent>  
  - <https://hermes-agent.nousresearch.com/docs/>
- OpenClaw（官方）  
  - <https://github.com/openclaw/openclaw>  
  - <https://docs.openclaw.ai/>  
  - <https://docs.openclaw.ai/gateway/protocol>
- 产品化参照  
  - Manus: <https://manus.is/>  
  - ChatGPT Agent: <https://openai.com/index/introducing-chatgpt-agent/>  
  - Workspace Agents: <https://openai.com/index/introducing-workspace-agents-in-chatgpt/>

