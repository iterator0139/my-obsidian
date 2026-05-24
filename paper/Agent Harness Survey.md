
# Context Management
## Short Term

### prompt calibration

anthropic altitude
prompts that are too specific introduce brittle, maintenance-heavy logic;
prompts that are too vague leave the model without concrete guidance.

good practice
organized into clearly delineated sections for background, instructions, tool guidance, and output format, using XML tags or Markdown headers to separate them

recommend workflow
最小 prompt 起步 → 实证找 failure mode → 针对性加指令，而不是 preemptively 枚举所有 edge case。

### token-efficient tool design
input level need fewer, more expressive tool
健壮性，无歧义

这里我还有个想法，工具输出需要后处理，我们只需要把和当前任务最重要的内容加载进短期记忆就可以了，其他结果可以外置。

### JIT  Retrieval & Progressive Disclosure
不 upfront 加载一切，而是维护轻量 identifier（path、query、link），按需加载。  
Claude Code 例子：`CLAUDE.md` 在 session 启动加载，具体文件用 glob/grep JIT 读。

### kv-cache-aware context design

Manus 团队：KV-cache hit rate 是 production agent 最重要指标之一（cached vs uncached 差 10× 成本）。
三条设计规则：
1. Prompt prefix 稳定 — 开头差一个 token 就 invalidate 后续 cache
2. Context append-only — 改历史 action/observation 会破坏 cache
3. Deterministic serialization — JSON key 顺序不稳定也会 invalidate
工具列表在前部 → 增删 tool 会 invalidate 后续 turn。Manus 用 logit masking 禁选不可用 action，而不是 runtime 改 tool list。
发展路径：short-term 优化从「写 prompt」转向 cache-aware context assembly（context-space、skill libraries 等）。