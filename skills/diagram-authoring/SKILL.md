---
name: diagram-authoring
description: 把设计文档里的机制画成对应的图，渲染出来验证后再交付。Use when a design, architecture, or process document needs diagrams — 架构图、组件图、状态机、流程图、顺序图、定时图、ERD、C4、泳道图 — or when existing diagram sources must be rendered, checked, or exported to SVG/PNG.
---

# 绘图与渲染

图是设计文档的一部分，不是插图。先用机制决定画什么图，再写图源码，再渲染出来看一眼，最后
才交付。

## 工作流

1. 定机制：要表达的是状态流转、控制分支、数据流转、责任交接、竞态窗口、数据关系，还是
   判定规则。
2. 定图类型：见 `code-implementation-spec` 的"图的对应关系"表。一张图只回答一个问题。
3. 定引擎：默认 PlantUML；需要 Markdown 就地渲染时用 Mermaid。
4. 写图源码：名字与正文、数据定义保持一致。节点、步骤、交接点带编号，编号与正文对齐。
5. 渲染：按[环境与渲染](references/environment-and-rendering.md)里的命令跑，必须带
   `-failfast2`。
6. 看成图：确认没有报错图、没有交错重叠、没有正文里没写的分支、并发画成了并发、条件写的
   是正向条件。
7. 交付：正文内嵌 SVG（可缩放、可检索），预览用 PNG。源码和产物一起提交。

## 引擎选择

| 需求 | 引擎 |
| --- | --- |
| 状态机、顺序图、组件图、类图、部署图、ERD、C4、ArchiMate、定时图、官方云图标 | PlantUML |
| 需要 Markdown 就地渲染（Obsidian、GitHub、带插件的 Confluence） | Mermaid |
| 给人看的手绘示意图 | Excalidraw |

Mermaid 没有定时图，也没有真正的 DFD，这两类只能走 PlantUML。Excalidraw 的文件是 JSON，
AI 改不动、diff 看不出变化，别拿它当设计文档的图。

## 自检

- 图里的每个名字都能在正文或数据定义里找到。
- 编号与正文对得上，图可以当索引翻。
- 渲染命令带了 `-failfast2`，而且你确实看过成图，不是只看退出码。
- 并发画成并发，返回条件写的是正向条件，正文里没有的分支没画。
- 图与正文冲突时改图，不改正文。
