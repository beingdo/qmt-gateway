# QMT Gateway

Windows 执行网关，包装国金 QMT `xtquant` 库，为 AlphaDesk 后端提供内网 HTTP 行情和交易接口。

## 三层架构

```
AlphaDesk 后端（CentOS）
    ↓ HTTP + Token
Windows 执行网关（FastAPI，本项目）
    ↓ xtquant 本地调用
国金 QMT 客户端（极简模式 XtMiniQmt.exe）
    ↓
券商柜台
```

## M1 ✅ 完成

验证 xtquant 能从 QMT 极简模式取到历史日线和实时快照。

运行 test_xtdata.py（standalone 验证脚本）。

## M2a 当前阶段

基础行情网关框架，提供 HTTP 接口：

- `GET /health` — QMT 连接状态检查
- `GET /quote/history?code=600519.SH&start=20240101&end=20240110&period=1d` — 历史日线
- `GET /quote/tick?code=600519.SH` — 实时快照
- `GET /quote/intraday?code=600519.SH` — 今日分时（当天 tick 序列精简为价格/成交量时间序列，用于分时图）
- `GET /account/positions` — 真实持仓（只读，返回 `stock_code`/`volume`/`can_use_volume`/`avg_price`/`market_value`）
- `GET /account/asset` — 账户资金（只读，返回 `total_asset`/`cash`/`market_value`）

`/account/*` 是纯查询接口，网关代码里不包含任何下单/撤单能力。

### 路径说明

QMT 安装目录含中文（如 `C:\国金证券QMT交易端`），部分工具对非 ASCII 路径处理不稳定。已在 Windows 上创建 NTFS 目录联结把它映射成纯英文路径，所有脚本统一走这条路径：

```powershell
New-Item -ItemType Junction -Path "C:\qmt" -Target "C:\国金证券QMT交易端"
```

`C:\qmt` 和真实中文路径指向同一份文件，两者等价。

### 前置条件

1. **启动 Mini QMT 极简模式**，登录成功：

```powershell
& "C:\qmt\bin.x64\XtMiniQmt.exe"
```

保持这个窗口打开。

2. **启动 Gateway 服务**（另一个 PowerShell 窗口）：

```powershell
cd C:\<qmt-gateway路径>
.\start_gateway.ps1
```

或手动：

```powershell
& "C:\qmt\bin.x64\python.exe" gateway.py
```

### 安全模型

- **网关只监听内网 IP**（`gateway.py` 里 `Config.HOST`，默认 `10.0.0.69`，不是 `0.0.0.0`），即使 Windows 防火墙 / 云安全组配置有误，进程本身也不会在公网网卡上接受连接。如果这台机器的内网 IP 变了，用环境变量 `QMT_GATEWAY_HOST` 覆盖。
- **所有接口都要求 `Authorization: Bearer <token>`**。Token 首次启动 `gateway.py` 时自动生成，写入同目录下的 `gateway_token.txt`（已加入 `.gitignore`，不会提交到仓库），启动日志也会打印一次。
- 云厂商安全组和 Windows 防火墙的入站规则，**来源 IP 必须锁定为 CentOS VPS 的内网 IP**，不要用 `0.0.0.0/0`。

### 配置资金账号（`/account/*` 接口需要）

真实资金账号（数字账户）**绝不能写进代码**，因为这个仓库是 Public 的。配置方式二选一：

- 环境变量 `QMT_ACCOUNT_ID`
- 在 `qmt-gateway` 目录下新建 `account_id.txt`，第一行写账号（已加入 `.gitignore`，不会被提交）：

```powershell
"你的资金账号" | Out-File -Encoding utf8 account_id.txt
```

> 如果之前跑过 `test_xttrade.py`，多半已经建好这个文件了，可以直接复用，无需重复创建。

`gateway.py` 启动时会读取这个账号，建立一个**长期复用的交易会话**（`XtQuantTrader.connect()` + `subscribe()` 只在启动时做一次，不会每次请求都重连）。如果没配置账号，或者 connect/subscribe 失败，网关仍会正常启动，只是 `/account/positions` 和 `/account/asset` 会返回 503 并说明原因；行情相关接口不受影响。

配置或修改 `account_id.txt` 后，需要**重启网关服务**（`gateway.py`）才会生效。

### 测试网关

新开第三个 PowerShell 窗口：

```powershell
cd C:\<qmt-gateway路径>
& "C:\qmt\bin.x64\python.exe" test_gateway.py
```

会自动读取 `gateway_token.txt` 并测试鉴权、行情接口，以及"不带 Token 应被拒绝"。

或用 curl 手动测试（把 `<TOKEN>` 换成 `gateway_token.txt` 里的内容）：

```powershell
curl -H "Authorization: Bearer <TOKEN>" http://10.0.0.69:8888/health
curl -H "Authorization: Bearer <TOKEN>" "http://10.0.0.69:8888/quote/history?code=600519.SH"
curl -H "Authorization: Bearer <TOKEN>" "http://10.0.0.69:8888/quote/tick?code=600519.SH"
curl -H "Authorization: Bearer <TOKEN>" "http://10.0.0.69:8888/quote/intraday?code=600519.SH"
curl -H "Authorization: Bearer <TOKEN>" "http://10.0.0.69:8888/account/positions"
curl -H "Authorization: Bearer <TOKEN>" "http://10.0.0.69:8888/account/asset"
```

CentOS 端调用示例：

```bash
TOKEN=$(cat gateway_token.txt)  # 需从 Windows 安全地拷贝过来一次，不要提交进任何仓库
curl -H "Authorization: Bearer $TOKEN" http://10.0.0.69:8888/health
curl -H "Authorization: Bearer $TOKEN" "http://10.0.0.69:8888/quote/intraday?code=600519.SH"
```

### 日志

- `logs/gateway.log` — 服务日志
- `logs/test_xtdata.log` — M1 测试日志

## M2b 计划

支持多周期 K线（1分钟、5分钟、30分钟、周线等）。

## M3 计划

交易接口（下单、撤单、持仓查询）。
