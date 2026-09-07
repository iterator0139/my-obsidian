---
name: skill-confluence-markdown-upload
description: >-
  Upload local Markdown files to Confluence as child pages (batch or single),
  with preprocessing for skynet-base markdown converter quirks, image handling,
  title-collision resolution, page move, and cross-document link rewrite.
  Use when user asks to upload/sync/publish markdown to Confluence, create
  sub-pages under a parent pageId, or migrate doc/*.md to Confluence.
---

# Confluence Markdown Upload

将本地 Markdown 批量或单篇上传到 Confluence 子页面。依赖 `skynet-base confluence`（见 `skill-confluence`）和本 skill 的预处理规则。

**目标实例**：`https://confluence.shopee.io`

## 何时使用

- 用户给出父页面 URL / `pageId`，要求上传一个或多个 `.md` 为子文档
- 用户说「同步到 Confluence」「发布设计文档」「把 doc 目录挂到 CF 页面下」
- 本地 Markdown 含相对链接、本地图片、blockquote、`---` 分隔线等需兼容处理

## 前置条件

1. 已安装 `skynet-base`（`npm install @shopee/skynet-base@latest -g --registry https://npm.shopee.io`）
2. 已配置 `CONFLUENCE_TOKEN`：
   ```bash
   skynet-base setup token
   # 或 macOS 打开 Terminal 配置：
   osascript -e 'tell application "Terminal" to do script "skynet-base setup token"'
   ```
3. 读取父页面元数据（spaceKey）：
   ```bash
   skynet-base confluence read "<PARENT_PAGE_ID>" --raw
   ```

程序化取 token 时必须用 `--raw`，避免输出装饰文本：
```bash
skynet-base key get CONFLUENCE_TOKEN --raw
```

## 推荐执行方式

**优先使用本 skill 自带脚本**（已封装预处理、创建/更新、移动、链接回写）：

```bash
python3 scripts/upload_markdown_to_confluence.py \
  --parent-id 3118410900 \
  --file doc/trd.md \
  --file doc/forward-api-design.md \
  --title "正排接口开发设计（V2 草案）"  # 仅对最后一个 --file 生效；批量见 manifest
```

批量上传用 manifest JSON（推荐）：

```bash
python3 scripts/upload_markdown_to_confluence.py \
  --parent-id 3118410900 \
  --manifest upload-manifest.json
```

`upload-manifest.json` 示例：

```json
{
  "pages": [
    { "file": "doc/trd.md", "title": "正排去除basic表的依赖详细设计" },
    { "file": "doc/forward-api-design.md", "title": "正排接口开发设计（V2 草案）" },
    { "file": "doc/forward-api-get-ads-plan-info.md" }
  ],
  "image_map": {
    "./images/foo.png": "https://confluence.shopee.io/download/attachments/PAGE_ID/foo.png?version=1&modificationDate=0&api=v2"
  },
  "rewrite_links": true
}
```

未指定 `title` 时，取 Markdown 首个 `# ` 标题。

脚本路径（canonical）：

```
/Users/hom/Documents/Obsidian Vault/skills/skill-confluence-markdown-upload/scripts/upload_markdown_to_confluence.py
```

## 工作流（Agent 手动执行时）

无脚本或需微调时，按此顺序：

```
- [ ] 1. 确认 token、读取父页面 spaceKey
- [ ] 2. 预处理每个 .md（见下方规则）
- [ ] 3. 检查空间内标题冲突（search 精确标题）
- [ ] 4. 创建或更新页面
- [ ] 5. 将已有页面移动到父页面下（REST move）
- [ ] 6. 回写文档间相对链接为 Confluence URL
- [ ] 7. 验证 ancestors 指向父页面
```

### 1. 标题冲突策略

同一 `spaceKey` 下标题唯一。上传前搜索：

```bash
skynet-base confluence search "精确标题" --space O2OAlgo --limit 5
```

| 情况 | 动作 |
|------|------|
| 无同名页 | `confluence create --parent-id ... --body-format markdown` |
| 已有同名页 | `confluence write <pageId> ...` 更新内容，再 **move** 到父页面下 |
| 需保留旧页 | 使用新标题创建（如加版本后缀） |

### 2. 创建 / 更新

```bash
# 新建子页面
skynet-base confluence create \
  --title "页面标题" \
  --space-key O2OAlgo \
  --parent-id 3118410900 \
  --file /tmp/preprocessed.md \
  --body-format markdown

# 更新已有页面
skynet-base confluence write "<PAGE_ID>" \
  --file /tmp/preprocessed.md \
  --body-format markdown \
  --title "新标题（可选）" \
  --version-message "Sync from local markdown"
```

### 3. 移动已有页面到父页面下

`skynet-base` 无 move 命令。用 REST API（token 用 `--raw`）：

```python
PUT https://confluence.shopee.io/rest/api/content/{pageId}
{
  "id": "{pageId}",
  "type": "page",
  "title": "{currentTitle}",
  "ancestors": [{"id": "{parentId}"}],
  "version": {"number": currentVersion + 1, "message": "Move under parent page"}
}
```

### 4. 验证父子关系

```python
GET /rest/api/content/{pageId}?expand=ancestors
# 最后一级 ancestor.id 应等于 parent-id
```

## Markdown 预处理规则（必须）

`skynet-base` 用 markdown-it 转 storage HTML，以下语法会导致 **HTTP 400 xhtml 解析失败**：

| 问题语法 | 处理 |
|----------|------|
| 单独一行的 `---` | **删除**（会生成未闭合 `<hr>`） |
| `> blockquote` 元信息行 | 去掉 `> ` 前缀，改为普通段落 |
| 行尾双空格硬换行 + 行内 `` `code` `` | 去掉行尾空格 |
| `![alt](url)` 图片 | 改为 `<img src="..." alt="..." />`，URL 中 `&` → `&amp;` |
| `./images/xxx.png` 本地图 | 映射到 Confluence attachment 完整 URL，或无映射则 **删除** 该行 |
| `<!-- confluence meta -->` 头注释 | 删除 |
| 含 `doc/images` 的「阅读说明」示例行 | 删除（避免行内 `![]()` 干扰） |

图片映射：父页面或已有页面的 attachment URL 形如：

```
https://confluence.shopee.io/download/attachments/{pageId}/{filename}?version=1&modificationDate=...&api=v2
```

### 相对链接回写

全部页面上传后，将 `./foo.md`、`foo.md` 替换为：

```
https://confluence.shopee.io/pages/viewpage.action?pageId={targetPageId}
```

对含链接的页面再执行一次 `confluence write`。

## 错误处理

| 错误 | 处理 |
|------|------|
| `CONFLUENCE_TOKEN is not configured` | 引导用户 `skynet-base setup token` |
| `page with this title already exists` | 搜索已有 pageId → write + move，勿重复 create |
| `Unexpected close tag </p>; expected </br>` | 检查 blockquote / 行尾双空格 |
| `Unexpected close tag </xml>; expected </hr>` | 删除文中 `---` 分隔线 |
| `Unexpected close tag </p>; expected </img>` | 图片改 HTML `<img>` + `&amp;` 转义 |
| `Invalid leading whitespace... in header value` | `key get` 必须加 `--raw` |

## 输出给用户

完成后汇报：

1. 父页面链接
2. 每个子页面 title + pageId URL
3. 哪些是 update+move、哪些是新建
4. 未上传的本地图片及原因
5. 测试页误创建时提示可删除

## 附加资源

- 基础 Confluence CLI：`skill-confluence`
- 上传脚本：[scripts/upload_markdown_to_confluence.py](scripts/upload_markdown_to_confluence.py)
- Manifest 示例：[scripts/manifest.example.json](scripts/manifest.example.json)
