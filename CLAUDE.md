# Obsidian Vault · Claude 项目说明

## 所有文档输出（必读）

产出的**所有文档**在返回前都必须过一遍 `skills/humanizer/SKILL.md`（也可用
`$humanizer` / `/humanizer` 触发）；未自动触发时仍须读取并遵循该文件。

- **范围**：技术文档、架构与方案文档、报告、计划、README、`skills/*/SKILL.md` 的说明文字、
  commit / PR 文案、vault 笔记。
- **例外**：与用户的对话回复本身不过 humanizer（那是对话语气，不是文档语气）；代码块、
  行内代码、命令、路径、YAML 元数据及其链接目标一律不改。

## LeetCode 题解（必读）

用户给出 **LeetCode / 算法题**、要求 **做题解 / 分析 / 破局眼 / 五分钟读题法** 时：

1. **必须先调用 skill**：`/leetcode-five-minute-read`（或 `$leetcode-five-minute-read`）
2. 若未自动触发，仍须 **读取并遵循**：
   - `skills/leetcode-five-minute-read/SKILL.md`
   - `skills/leetcode-five-minute-read/property-algorithm-mapping.md`
   - `skills/leetcode-five-minute-read/decision-trees.md`
3. **默认落盘**：`leetcode/{题号}. {题名}.md` = 题干 + `---` + 四步题解

四步结构：**分析性质（识别信号）→ 读题盲猜 → 最优解法 → 拆解记忆点**

完整方法论：`leetcode/五分钟读题法.md`
