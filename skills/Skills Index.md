---
tags: [skills, moc, agent]
aliases: [Agent Skills 索引, Skills Hub]
---

# Agent Skills 索引

> **唯一来源（Source of Truth）**：本 vault 的 `skills/` 目录。  
> Cursor / Claude Code / Codex 通过符号链接或同步脚本读取，不在多处维护副本。

## 技能列表

| Skill | 用途 | 入口 |
|-------|------|------|
| learn-tech-framework | 从 0 到 1 认识技术框架，输出宏观文档 | [[skills/learn-tech-framework/SKILL\|SKILL]] |
| layered-tech-deep-dive | 在宏观理解之后，选择某一层做抽象、流程、算法、系统设计、代码实现下钻 | [[skills/layered-tech-deep-dive/SKILL\|SKILL]] |

### AI Coding 流程（来自 Codex，见 [[AI Coding流程]]）

按“语义 → 架构 → 模块 → 实现 → 验证”分层，产物不互相越权：

| Skill | 层级 | 用途 | 入口 |
|-------|------|------|------|
| analyze-change-context | 0. 问题定界 | 变更前梳理真实问题、基线行为、约束与非目标 | [[skills/analyze-change-context/SKILL\|SKILL]] |
| define-capability-contract | 1. 能力语义 | 定义能力的可观察行为、状态规则、系统级不变量、失败语义 | [[skills/define-capability-contract/SKILL\|SKILL]] |
| design-responsibility-architecture | 2. 总体架构 | 把语义契约分解为事实归属、决策权、边界与架构不变量 | [[skills/design-responsibility-architecture/SKILL\|SKILL]] |
| define-development-task-contract | 3. 开发任务契约 | 从架构切出可独立实现的任务，声明局部保证与非责任 | [[skills/define-development-task-contract/SKILL\|SKILL]] |
| code-implementation-spec | 4. 实现规格 | 把任务契约映射到接口、算法、调用顺序、异常与状态归属 | [[skills/code-implementation-spec/SKILL\|SKILL]] |
| plan-behavioral-validation | 5. 验证计划 | 按范围（单元/接口/集成/能力）规划行为优先的验证方案 | [[skills/plan-behavioral-validation/SKILL\|SKILL]] |
| execute-contract-verification | 5. 验证执行 | 执行验证计划、收集证据、给出有边界的通过/失败结论 | [[skills/execute-contract-verification/SKILL\|SKILL]] |

## 相关方法论（vault 内）

- [[Ideas/怎么认识一个事物]] — 认识事物的 SOP（宏观）
- [[Ideas/分析对比的SOP]] — 对比分析
- [[prompt/架构学习]] — 架构师视角深度学习（源码 / 机制 / 面试向，比 macro skill 更深）

## 学习产出（frameworks/）

框架学习文档统一放在 `frameworks/{name}/`：

| 框架 | 文档 |
|------|------|
| Zep | [[frameworks/zep/from-zero-to-one\|宏观版]] · [[frameworks/zep/from-zero-to-one-obsidian\|Obsidian 紧凑版]] |

## 同步到 Agent 工具

在 vault 根目录执行：

```bash
bash skills/sync-to-agents.sh
```

会创建/更新：

- `~/.cursor/skills/{skill}` → 本 vault（Cursor）
- `~/.claude/skills/{skill}` → 本 vault（Claude Code）
- `~/.codex/skills/{skill}` → 本 vault（Codex）

覆盖 `learn-tech-framework`、`layered-tech-deep-dive`、`leetcode-five-minute-read`、`skill-confluence-markdown-upload`
以及 AI Coding 流程的全部 7 个 skill。

## 使用方式

**Cursor / Claude Code**

```
用 learn-tech-framework 从 0 到 1 认识 LangGraph
```

**Obsidian 内（RealClaudian 等）**

Agent 工作目录设为 vault 根目录，直接读取 `skills/learn-tech-framework/SKILL.md`。

## 维护约定

1. 只改 `my-obsidian/skills/` 下的文件
2. 改完后运行 `sync-to-agents.sh`
3. 学习产出写入 `frameworks/{slug}/`，不在 skill 目录里堆 output
4. 新增 skill：在 `skills/` 下建子目录 + 更新本索引
