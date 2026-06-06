# Notion 个人任务中心 — 一表流

> 一张表、五个字段、四个视图，覆盖大盘 / Focus / 回溯 / 周报。

## 结构预览

```
个人任务中心（页面）
├── 💡 使用说明 + 周日 AI 周报指令
└── 任务总表（数据库）
    ├── 🗓️ 大盘视图         ← Timeline，按项目着色
    ├── 🎯 Focus 今日重点       ← 仅显示手动勾选 ☑️今日重点 的任务
    ├── 🔲 四象限矩阵         ← 今日重点按重要/紧急四象限分列
    ├── 📅 回溯视图         ← 日历，仅「已完成」
    ├── 📈 项目统计         ← 表格分组（免费，替代 Chart）
    └── 📋 全部任务         ← 原始表格

个人任务中心主页（免费总览）：
    ├── 📊 快速总览 — 3 个「关联数据库」嵌入页（Timeline / Focus / 回溯）
    └── 任务总表（完整数据库）
```

### 五个字段

| 字段 | 类型 | 说明 |
|------|------|------|
| 任务名称 | Title | 任务标题 |
| 项目 | Select | 个人成长 / 工作 / 生活琐事（可自增） |
| 状态 | Status | 未开始 / 进行中 / 已完成 |
| 日期 | Date | 开始 + 截止日期（支持范围） |
| 复盘笔记 | Text | 心得、延期原因等 |
| 今日重点 | Checkbox | 手动勾选进入 Focus（建议每天 ≤3 个） |
| 象限 | Select | ①重要且紧急 / ②重要不紧急 / ③紧急不重要 / ④不重要不紧急 |

---

## 一键创建 — PAT 流程（推荐，2 步）

PAT（Personal Access Token）以**你的账号权限**调 API，不需要 OAuth 授权，也**不用**给页面手动 Add connections。

### 第一步：创建 PAT

1. 打开 [Notion Developer Portal](https://www.notion.so/profile/integrations)
2. 左侧进入 **Personal access tokens** → **New personal access token**
3. 填写：
   - **Name**：`个人任务中心`
   - **Workspace**：选你的工作区
   - **Capabilities**：勾选 **Notion API**
4. 点击 **Create token**，复制 token（`ntn_...`，只显示一次）
5. 存到环境变量（不要提交到 git）：

   ```bash
   export NOTION_TOKEN="ntn_你的token"
   ```

> PAT 有效期 1 年，到期前在 portal 新建并更新脚本里的 token 即可。

### 第二步：运行脚本

1. 在 Notion 里新建一个空白父页面，例如「工作台」
2. 从 URL 复制页面 ID（32 位十六进制）：

   ```
   https://www.notion.so/工作台-abc123def4567890abcdef1234567890
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   ```

3. 运行：

   ```bash
   cd "/Users/hom/Documents/Obsidian Vault/dev-notes/tools/notion-task-hub"

   export NOTION_TOKEN="ntn_你的token"
   export PARENT_PAGE_ID="abc123def4567890abcdef1234567890"

   python3 setup_notion_task_hub.py
   ```

脚本会自动：
- 创建「个人任务中心」页面（含 AI 周报指令）
- 创建「任务总表」数据库及 5 个字段
- 配置 Dashboard + 四大视图
- 写入 3 条示例任务

### PAT 和 Internal / OAuth 的区别

| | PAT | Internal | OAuth |
|--|-----|----------|-------|
| 权限来源 | 你的用户账号 | Bot，需手动分享页面 | 每个用户单独授权 |
| 页面授权 | 你能看到的都能访问 | 须 Add connections | 授权时页面选择器 |
| 适合场景 | 个人脚本、CLI、Workers | 团队 bot 自动化 | 给别人安装的产品 |
| Token 格式 | `ntn_...` | `secret_...` | `ntn_...`（access_token） |

---

## 日常使用

### 每天早上（Focus）

1. 打开 **📋 全部任务**，取消昨天勾选的 **☑️ 今日重点**
2. 今天挑 **最多 3 个** 任务，勾选 **☑️ 今日重点**（可顺手标为「进行中」）
3. 打开 **🔲 四象限矩阵**，把任务拖入对应象限（或逐条设置「象限」字段）
4. 打开 **🎯 Focus 今日重点** —— 按列表顺序执行，优先 ① → ②

### 随时记录

在「📋 全部任务」或任意视图新建一行即可，所有视图自动同步。

### 每周日（AI 周报）

1. 打开「个人任务中心」主页，复制 AI 指令：

   ```
   请分析我本周已完成的任务，总结我在各个项目上的时间投入比例，
   并指出有哪些任务经常延期，给出下周优化建议。
   ```

2. 打开「任务总表」→ 点击右上角 **Notion AI**
3. 粘贴指令，上下文选 **当前数据库**
4. 可同时参考 **📈 项目统计** 视图（按项目分组计数）

### 大盘复盘

- **🗓️ 大盘视图**：看各项目任务的时间跨度
- 如需按项目分组：打开大盘视图 → **Layout** → **Group by** → **项目**
- **📅 回溯视图**：看哪天完成了什么

---

## 手动创建（不用脚本）

若不想跑脚本，在 Notion 里按以下步骤操作：

1. 新建数据库「任务总表」，添加 5 个字段（见上表）
2. 创建视图：
   - **大盘**：Layout 选 Timeline，Date 选「日期」，Group by「项目」
   - **Focus**：Layout 选 List，Filter `今日重点 = checked`
   - **回溯**：Layout 选 Calendar，Filter `状态 = 已完成`
3. 在父页面用 `/linked` 嵌入三个关联视图（大盘 / Focus / 回溯）
4. 贴上 AI 周报指令

> **Dashboard 和 Chart 视图需要 Notion 付费会员。** 免费方案用「关联数据库视图」+ 表格分组统计替代。

---

## 备选认证方式

### Internal connection

```bash
export NOTION_TOKEN="secret_..."
export PARENT_PAGE_ID="..."
# 父页面须手动 ··· → Connections → 添加该 integration
python3 setup_notion_task_hub.py
```

### OAuth connection

适合要上 Marketplace、给其他用户安装的场景。见 `oauth_login.py`：

```bash
export OAUTH_CLIENT_ID="..."
export OAUTH_CLIENT_SECRET="..."
python3 oauth_login.py
export NOTION_TOKEN="$(python3 -c 'import json; print(json.load(open(".notion_token"))["access_token"])')"
python3 setup_notion_task_hub.py
```

---

## 故障排查

| 错误 | 原因 | 解决 |
|------|------|------|
| `401 unauthorized` | PAT 无效、过期或被撤销 | Developer portal 新建 PAT 并更新 `NOTION_TOKEN` |
| `401 unauthorized` | 工作区禁止成员创建 PAT | 联系管理员调整 Settings → Connections → PAT 策略 |
| `404 object_not_found` | 父页面 ID 错，或你没有该页面权限 | 检查 URL 中的 ID；确保页面在你账号下可访问 |
| `403 restricted_resource` | PAT 未勾选 Notion API 能力 | 重建 token 并勾选 Notion API |
| 视图创建失败 | API 版本过旧 | 脚本已用 `2026-03-11` |
