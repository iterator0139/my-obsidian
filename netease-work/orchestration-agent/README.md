# Orchestration Agent 项目学习

## 学习目标

理解本项目如何把用户请求转换为可规划、可执行、可观察、可取消、可恢复的多智能体任务。

## 文档导航

- [[01-from-zero-to-one]]：项目宏观认知，从 0 到 1
- [[02-ingress-layer-deep-dive]]：接入层深度分析（当前学习内容）
- [[03-lifecycle-layer-deep-dive]]：生命周期层深度分析（当前学习内容）
- [[04-intent-planning-layer-deep-dive]]：意图与规划层深度分析（当前学习内容）
- [[05-execution-adapter-layer-deep-dive]]：执行适配层深度分析（当前学习内容）
- [[06-runtime-governance-layer-deep-dive]]：运行治理层深度分析（当前学习内容）
- [[07-infrastructure-layer-deep-dive]]：基础设施层深度分析（当前学习内容）
- [[08-iteration-roadmap]]：Agent 编排平台迭代规划
- [[09-react-dag-hybrid-architecture]]：ReAct + DAG 混合编排架构

推荐顺序：先阅读 `01-from-zero-to-one`，再依次阅读 `02-ingress-layer-deep-dive`、`03-lifecycle-layer-deep-dive`、`04-intent-planning-layer-deep-dive`、`05-execution-adapter-layer-deep-dive`、`06-runtime-governance-layer-deep-dive` 和 `07-infrastructure-layer-deep-dive`。

## 当前架构判断

项目的核心路径是：

```text
OrchestrationWorkflow
  -> LoopOrchestrationAgent
  -> TaskToolkit
  -> DigitalWorkerProxyAgent
  -> 本地 Agent / 远程数字员工
```

当前代码以 Agentic Loop 为主。旧 DAG / `execute_plan` 相关内容主要存在于历史注释、兼容逻辑或测试语境中，当前 `OrchestrationWorkflow` 的核心执行步骤是 `loop_execute`。
