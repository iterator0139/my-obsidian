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

- `~/.cursor/skills/learn-tech-framework` → 本 vault
- `~/.claude/skills/learn-tech-framework` → 本 vault
- `~/.claude/skills/layered-tech-deep-dive` → 本 vault

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
