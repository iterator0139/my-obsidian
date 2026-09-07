# dev-notes · 开发经验库（初版）

> 沉淀可复用的排障与工具链经验，与 `leetcode/`、`paper/`、`interview/` 并列，专注 **工程实践** 而非业务 TRD。

## 目录结构（初版）

```text
dev-notes/
├── README.md                 # 本索引
├── editor/                   # IDE / 编辑器（Cursor、VS Code）
│   └── cursor/
│       └── Markdown预览本地图片不显示.md
├── docs/                     # 文档工作流（Confluence、Markdown 迁移）
│   └── confluence/
│       └── Confluence导出Markdown与图片.md
└── _templates/               # 可选：新经验笔记模板
    └── experience-note.md
```

## 分类约定

| 目录 | 放什么 | 命名 |
|------|--------|------|
| `editor/` | 编辑器、插件、预览、快捷键 | `工具-问题简述.md` |
| `docs/` | 文档下载、格式转换、图片资源 | 同上 |
| 未来可扩展 `toolchain/` | git、CI、脚本、MCP | 按需再加 |

## 单篇笔记建议结构

1. **现象** — 用户看到什么  
2. **原因** — 1～3 条根因  
3. **推荐做法** — 可复制步骤  
4. **反模式** — 踩坑方案（如 base64 内嵌）  
5. **关联** — 相关笔记双链  

## 已有笔记

- [[toolchain/gas/GAS配置加载与localhost覆盖]]
- [[editor/cursor/Markdown预览本地图片不显示]]
- [[docs/confluence/Confluence导出Markdown与图片]]

## 标签（Obsidian）

`#dev-notes` `#cursor` `#markdown` `#confluence`
