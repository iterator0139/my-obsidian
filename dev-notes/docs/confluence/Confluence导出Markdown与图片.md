---
tags: [dev-notes, confluence, markdown]
created: 2026-06-03
source: basic-migrate Confluence pageId=3128050280
---

# Confluence 导出 Markdown 与图片落盘

## 场景

把 Confluence 技术页（如 TRD）拉到 Git 仓库里做 `doc/trd.md`，并保证 **本地 Markdown 预览能看图**。

## 环境变量

```bash
export CONFLUENCE_BASE_URL=https://confluence.shopee.io
export CONFLUENCE_BEARER_TOKEN=<token>   # 或 CONFLUENCE_PERSONAL_TOKEN
```

## 单页下载

使用 Cursor skill 脚本（本机路径示例）：

```bash
CONFLUENCE_BASE_URL=https://confluence.shopee.io \
python3 ~/.cursor/skills/confluence-business-kb/scripts/fetch_confluence.py \
  'https://confluence.shopee.io/pages/viewpage.action?pageId=3128050280' \
  --output ./confluence-downloads/3128050280
```

产物：

```text
confluence-downloads/<pageId>/
├── page.md      # 原始 Markdown
└── images/      # 本页附件中已解析的图片
```

再复制到项目文档目录：

```bash
cp confluence-downloads/3128050280/page.md doc/trd.md
cp -R confluence-downloads/3128050280/images doc/images
```

## 跨页附件（常见坑）

正文里引用的图可能挂在 **别的 pageId** 的 attachment 上（导出后仍是 Confluence URL）。需要 **单独下载** 后改为本地路径：

```bash
curl -sfL -H "Authorization: Bearer $CONFLUENCE_BEARER_TOKEN" \
  -o doc/images/xxx.png \
  'https://confluence.shopee.io/download/attachments/<pageId>/xxx.png?...'
```

然后在 `trd.md` 里改为：

```markdown
![说明](./images/xxx.png)
```

## 导出后建议处理

1. **Proto / Go 单行** → 整理为 fenced code block（`protobuf` / `go`）  
2. **图片** → 全部 `./images/`，去掉 Confluence 外链  
3. **表格** → 检查 Timeline 等是否错行  
4. 预览排障 → [[editor/cursor/Markdown预览本地图片不显示]]

## 关联

- [[editor/cursor/Markdown预览本地图片不显示]]
- [[README|dev-notes 索引]]
- Confluence 源页：<https://confluence.shopee.io/pages/viewpage.action?pageId=3128050280>
