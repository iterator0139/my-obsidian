# Portability: Obsidian as Source of Truth

## Canonical location

```text
~/project/my-obsidian/skills/
├── Skills Index.md              # MOC，统一管理入口
├── sync-to-agents.sh            # 同步脚本
└── learn-tech-framework/
    ├── SKILL.md
    ├── reference.md
    ├── templates/
    └── examples/
```

**只在此目录编辑 skill。** 改完后运行同步脚本。

## Sync to agents

```bash
cd ~/project/my-obsidian
bash skills/sync-to-agents.sh
```

Creates symlinks:

| Agent | Path |
|-------|------|
| Cursor | `~/.cursor/skills/learn-tech-framework` |
| Claude Code | `~/.claude/skills/learn-tech-framework` |

If a real directory already exists at the target, script backs it up with `.bak.{timestamp}`.

## Cursor

Invoke:

- 「用 learn-tech-framework 认识 X」
- 「从 0 到 1 了解 X」

## Claude Code

Same symlinks under `~/.claude/skills/`. Project-level: `<project>/.claude/skills/` can also symlink to vault.

## Codex

**Option A** — project symlink:

```bash
ln -s ~/project/my-obsidian/skills/learn-tech-framework .codex/skills/learn-tech-framework
```

**Option B** — reference in `AGENTS.md`:

```markdown
Framework learning workflow: ~/project/my-obsidian/skills/learn-tech-framework/SKILL.md
```

## Obsidian + RealClaudian

Vault 已安装 RealClaudian 插件时，Agent 工作目录设为 vault 根目录，直接读 `skills/learn-tech-framework/SKILL.md`，无需同步。

## Output locations

| 类型 | 路径 |
|------|------|
| 框架学习文档（默认） | `frameworks/{slug}/from-zero-to-one.md` |
| 紧凑版 | `frameworks/{slug}/from-zero-to-one-obsidian.md` |
| 项目内临时产出 | `{project}/local/{slug}-from-zero-to-one.md` |

## Related vault notes

- [[Ideas/怎么认识一个事物]] — 宏观 SOP
- [[Ideas/分析对比的SOP]] — 对比分析
- [[prompt/架构学习]] — 架构师深度学习
- [[skills/Skills Index]] — 技能索引
