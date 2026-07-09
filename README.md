# QMT Gateway

Windows 执行网关，包装国金 QMT `xtquant` 库，为 AlphaDesk 后端提供内网 HTTP 行情和交易接口。

## 三层架构

```
AlphaDesk 后端（CentOS）
    ↓ HTTP + Token
Windows 执行网关（FastAPI，本项目）
    ↓ xtquant 本地调用
国金 QMT 客户端（极简模式）
    ↓
券商柜台
```

## 当前进度（M1）

验证 xtquant 能从 QMT 客户端取到历史日线和实时快照。

### 运行 test_xtdata.py

确保 QMT 客户端已登录、行情在跳，然后：

```powershell
cd C:\<qmt-gateway-path>
& "C:\国金证券QMT交易端\bin.x64\python.exe" test_xtdata.py
```

输出写到 `test_xtdata.log`。

## 下一步（M2）

用 FastAPI 包装 xtdata，暴露行情接口。
