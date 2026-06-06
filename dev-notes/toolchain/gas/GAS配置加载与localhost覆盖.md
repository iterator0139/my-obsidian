---
tags: [dev-notes, gas, go, config, troubleshooting]
created: 2026-06-05
source: search-ads-service uat-id-gas debugb 排障
---

# GAS 配置加载与 localhost 覆盖

## 现象

`uat-id-gas debugb` 启动时报错：

```text
gas.spex.server: non-live config key empty
```

日志前面能看到 GAS / Config Center / Shark 已开始初始化，但 IoC 初始化 `gas.spex.server` 时失败。

## 根因

GAS Engine 的配置文件不是业务 `main.go` 决定的，而是 Engine 解析启动参数 `--gas.config` 决定。

本次仓库中：

```bash
--gas.config=etc/server.yml,etc/server.localhost.yml
```

`etc/server.yml` 配了完整的 Spex server：

```yaml
gas.spex.server:
  service_name: o2oalgo.food_ads.adssearchengine
  non_live_config_key: <non-live-key>
  sdu_id: default
  tag: master
```

但 `etc/server.localhost.yml` 原来只写了：

```yaml
gas.spex.server:
  logging:
    include_request: true
    include_response: true
```

如果 GAS 配置合并对该节点不是深合并，第二个文件中的 `gas.spex.server` 会覆盖第一个文件同名节点，导致 `service_name/non_live_config_key` 丢失，最终触发 `non-live config key empty`。

## 配置加载链路

`spkit build mod/server` 生成的 GAS wrapper 很薄：

```go
func main() {
    engine.Run(bm.RegisterModule)
}
```

真正逻辑在 GAS Engine：

```text
engine.Run
  -> pref.HandleFlags()
  -> localConfigRegistry(cfgFiles)
  -> config.NewConfig("gas.config", sharedFile, localhostFile)
```

关键代码位置：

```text
go-application-server/engine@v1.11.4/internal/run.go
go-application-server/engine@v1.11.4/internal/pref/cmdline.go
```

`--gas.config` 是 string slice，只使用前两个文件：

```bash
--gas.config=etc/server.yml,etc/server.localhost.yml
```

或：

```bash
--gas.config etc/server.yml --gas.config etc/server.localhost.yml
```

## 谁决定使用哪个配置

### 显式启动参数

优先看启动命令或 IDE args 是否传了：

```bash
--gas.config=...
```

本仓库中 `run-local.sh` 会自动追加 localhost：

```bash
CONFIG_ARG="--gas.config=etc/server.yml"
if [[ -f etc/server.localhost.yml ]]; then
  CONFIG_ARG="${CONFIG_ARG},etc/server.localhost.yml"
fi
```

`script/dev/prepare-vscode-gas-debug.sh` 也有同样逻辑：

```bash
LOCAL_CONFIG="${LOCAL_CONFIG:-etc/server.localhost.yml}"
CONFIG_ARG="--gas.config=etc/server.yml"
if [[ -f "${PROJECT_DIR}/${LOCAL_CONFIG}" ]]; then
  CONFIG_ARG="${CONFIG_ARG},${LOCAL_CONFIG}"
fi
```

### 自动探测

如果没有传 `--gas.config`，Engine 会根据 BM 路径推导配置文件。

例如 BM 是：

```text
mod/server
```

则默认查找：

```text
etc/server.yml
etc/server.localhost.yml
```

规则是：

```text
mod/<name> -> etc/<name>.yml
mod/<name> -> etc/<name>.localhost.yml
```

## 推荐修复

如果 localhost 文件里要覆盖 `gas.spex.server`，不要只写局部字段。写完整节点：

```yaml
gas.spex.server:
  service_name: o2oalgo.food_ads.adssearchengine
  non_live_config_key: <non-live-key>
  sdu_id: default
  tag: master
  logging:
    include_request: true
    include_response: true
    include_request_size: true
    include_response_size: true
```

更稳妥的原则：

- 对 GAS SPI 顶层 key 做本地覆盖时，默认假设它可能会整体覆盖，不要依赖深合并。
- `localhost.yml` 只放本地调试必须覆盖的配置。
- 如果要覆盖某个 required config 对象，补齐 required 字段。

## 排查清单

- [ ] 看启动参数是否包含 `--gas.config`。
- [ ] 如果包含两个文件，确认第二个是否覆盖了第一个同名顶层 key。
- [ ] 看启动日志中的 `initializing with local config`，确认实际加载的文件列表。
- [ ] 对报错的 SPI key，例如 `gas.spex.server`，同时检查 main config 和 localhost config。
- [ ] 对 `non-live config key empty`，优先查 `non_live_config_key` 是否被覆盖为空。

## 反模式（勿用）

只在 `etc/server.localhost.yml` 写局部子字段：

```yaml
gas.spex.server:
  logging:
    include_request: true
```

这类写法在非深合并场景下会覆盖完整 server 配置。

## 关联

- [[README|dev-notes 索引]]
