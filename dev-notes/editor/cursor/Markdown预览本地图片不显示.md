---
tags: [dev-notes, cursor, markdown, vscode]
created: 2026-06-03
source: basic-migrate/doc/trd.md 排版与预览排障
---

# Cursor / VS Code · Markdown 预览本地图片不显示

## 现象

在 `doc/trd.md` 中写了标准图片语法，预览里 **看不到图**，只看到 alt 文字连在一起，例如：

```text
2.1 现状架构
现状架构（数据流）现状架构（服务依赖）
```

说明 **Markdown 语法没问题**，是 **图片资源没被预览加载**。

## 根因（按优先级）

1. **外链图片**  
   Confluence 导出常保留 `https://confluence.xxx/download/attachments/...`，预览环境 **无登录态**，必然失败。

2. **路径写法与预览解析不一致**  
   - `./images/a.png` — 相对 **当前 md 文件**（推荐）  
   - `/doc/images/a.png` — 相对 **工作区根**（依赖工作区打开方式）  
   工作区根目录不一致时，后者容易失效。

3. **预览安全策略（Cursor / VS Code）**  
   默认 `markdown.preview.securityLevel` 较严时，可能拦截本地 `file:` 资源；表现为 **仅显示 alt**。

## 推荐做法

### 1. 图片与 md 同仓、标准语法

```text
project/
└── doc/
    ├── trd.md
    └── images/
        └── arch-xxx.png
```

```markdown
![现状架构（数据流）](./images/image2026-3-9-15-49-56.png)
```

- 路径：**相对于 `trd.md` 所在目录** 的 `./images/`  
- alt 要有意义，便于图片失败时仍能看懂占位

### 2. 工作区级预览配置

在项目 `.vscode/settings.json`（Cursor 同样读取）：

```json
{
  "markdown.preview.securityLevel": "allowInsecureContent"
}
```

若仍不显示，可尝试：

```json
{
  "markdown.preview.securityLevel": "allowScriptsAndAllContent"
}
```

改完后：**Developer: Reload Window**，再 `Cmd+Shift+V` 打开预览。

### 3. 确认预览方式

- 用 **`Markdown: Open Preview`**（`Cmd+Shift+V`）  
- 工作区根目录应包含 `doc/`（例如 `basic-migrate`），不要只打开子文件夹导致路径错位

### 4. Confluence 图先落盘再引用

不要长期依赖 Confluence attachment URL；下载到 `doc/images/` 后再用相对路径引用。  
（下载脚本见 [[docs/confluence/Confluence导出Markdown与图片]]）

## 反模式（本次踩坑）

| 方案 | 问题 |
|------|------|
| base64 内嵌 `![alt](data:image/png;base64,...)` | `trd.md` 膨胀到 ~500KB，编辑器卡顿，diff 难看 |
| HTML `<img src="data:...">` | 同上，且部分场景仍被过滤 |
| 仅改 `/doc/images/` 不写工作区 settings | 部分环境仍只显示 alt |

**结论**：预览通了之后，坚持 **标准 Markdown + 本地相对路径** 即可。

## 快速排查清单

- [ ] 图片文件是否存在于 `doc/images/`（不是只有 md 里的链接）
- [ ] 语法是否为 `![说明](./images/xxx.png)`（相对 trd.md）
- [ ] 是否仍残留 Confluence `https://` 图片链接
- [ ] `.vscode/settings.json` 是否已配置 `markdown.preview.securityLevel`
- [ ] 是否 Reload Window 后重新预览
- [ ] 工作区是否以含 `doc/` 的仓库根打开

## 关联

- [[docs/confluence/Confluence导出Markdown与图片]]
- [[README|dev-notes 索引]]
- 项目文档：`basic-migrate/doc/trd.md`
