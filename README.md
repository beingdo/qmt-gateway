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

### 前置条件

1. **启动 Mini QMT 极简模式**，登录成功：

```powershell
& "C:\国金证券QMT交易端\bin.x64\XtMiniQmt.exe"
```

保持这个窗口打开。

2. **启动 Gateway 服务**（另一个 PowerShell 窗口）：

```powershell
cd C:\<qmt-gateway路径>
.\start_gateway.ps1
```

或手动：

```powershell
& "C:\国金证券QMT交易端\bin.x64\python.exe" gateway.py
```

### 测试网关

新开第三个 PowerShell 窗口：

```powershell
cd C:\<qmt-gateway路径>
& "C:\国金证券QMT交易端\bin.x64\python.exe" test_gateway.py
```

或用 curl（需要安装 curl）：

```powershell
curl http://localhost:8888/health
curl "http://localhost:8888/quote/history?code=600519.SH"
curl "http://localhost:8888/quote/tick?code=600519.SH"
```

### 日志

- `logs/gateway.log` — 服务日志
- `logs/test_xtdata.log` — M1 测试日志

## M2b 计划

支持多周期 K线（1分钟、5分钟、30分钟、周线等）。

## M3 计划

交易接口（下单、撤单、持仓查询）。
