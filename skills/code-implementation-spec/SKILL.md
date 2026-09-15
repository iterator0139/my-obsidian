---
name: code-implementation-spec
description: Turn approved semantic, architecture, product, or refactoring designs into code-level implementation specifications. Use when entering formal development, detailing how a design maps to code, defining interfaces, algorithms, sequences, exceptions, state ownership, integration contracts, or test evidence; use for whole workflows and independently implementable submodules.
---

# 代码实现规格

把一个定稿的语义、架构或重构设计，落成可执行、可评审的代码级详细设计。产物是一份开发任务
详细设计。

## 何时用

- 进入正式开发，要把设计映射到接口、算法、调用顺序、异常和状态归属。
- 要定义跨模块的接口、事件或数据结构变更。
- 一个独立可实现的模块，或一条完整流程，要写详细设计。

不属于这个 skill 的部分：任务怎么拆、每个任务交付什么，归 `define-development-task-contract`；
验证方案归 `plan-behavioral-validation`；文字风格归 `humanizer`。

## 工作流

1. 读权威来源：语义设计、架构设计、项目约束，以及要改动的现有代码和测试。说明依据哪份
   文档，未核实的假设单独列出。
2. 把要的行为写成可观察承诺：必须发生什么、绝不能发生什么、谁能观察到结果。
3. 判断范围和正确性边界：一条完整流程负责从外部触发到外部结果；子模块只负责自己的局部
   保证，包括输入假设、局部不变量和非责任。
4. 用一句话写任务边界：在什么前提下，这个任务完成哪一件局部效果，然后交给谁。这句话写不
   出来，说明边界没切好。把它记成上游依赖，不要为了文档看起来完整而去造接口，或改动父级
   设计。
5. 选视角：读[视角清单](references/capability-lenses.md)，只取这次改动命中的视角。
6. 找决策点：事实归属、状态与副作用的提交点、不可逆的外部副作用、冲突的裁决者。归属不
   留白。
7. 按[输出骨架](references/output-blueprints.md)写。命中数据模型变更时，数据定义节要写全。
8. 机制只为承诺服务：先写要守住的承诺和必须成立的约束，再选机制，最后说明这个机制哪里还
   没被证明。局部实现的方便、现有代码的位置、测试好不好造，都算不上系统级证据。
9. 收尾时列出未决事项：谁负责，没定就动手会坏在哪。

## 自检

- 只读第 0 层，没参与的人能说出问题、改后行为、动哪几个模块、还差什么决定。
- 只读全部标题，能复述这次改动的全貌。
- 每一段内容只有一个正确位置：正文、附录，或删。
- 逻辑流与数据流的编号对得上，同一件事没有写两遍。

## 纪律

- 子模块不重复父级设计，也不重新定义父级策略。父级负责的状态转换，只作为前提和交接出现。
- 简单改动不配状态机、不加分布式失败分析、不加没有对应风险的抽象。
- 未决事项不要悄悄变成实现假设。实现过程中发现规格无法兑现，回到拥有该决策的层级修订。
