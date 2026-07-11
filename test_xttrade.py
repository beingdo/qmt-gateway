import os
import sys
import time

QMT_BIN = r"C:\qmt\bin.x64"
if QMT_BIN not in sys.path:
    sys.path.insert(0, QMT_BIN)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(SCRIPT_DIR, "test_xttrade.log")
account_id_file = os.path.join(SCRIPT_DIR, "account_id.txt")

# 资金账号不写进代码（这个仓库是 Public 的）。优先读环境变量 QMT_ACCOUNT_ID，
# 其次读本地 account_id.txt（已加入 .gitignore，不会被提交）。
# 首次用可以直接：echo 你的账号 > account_id.txt
ACCOUNT_ID = os.environ.get("QMT_ACCOUNT_ID", "").strip()
if not ACCOUNT_ID and os.path.isfile(account_id_file):
    ACCOUNT_ID = open(account_id_file, "r", encoding="utf-8").read().strip()
if not ACCOUNT_ID:
    print("请先设置账号：")
    print(f"  方式一：设置环境变量 QMT_ACCOUNT_ID")
    print(f"  方式二：把账号写进 {account_id_file}（新建这个文件，第一行填账号）")
    sys.exit(1)

# userdata_mini 目录（通过 C:\qmt 联结访问，避免中文路径问题）
USERDATA_MINI_PATH = r"C:\qmt\userdata_mini"


def log(msg):
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def main():
    log("=" * 60)
    log("xttrade 真实持仓/账户查询验证")
    log("=" * 60)

    log("\n[1] 导入 xttrader...")
    try:
        from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
        from xtquant.xttype import StockAccount
        log("[OK] xttrader 已导入")
    except Exception as e:
        log(f"[FAIL] 无法导入 xttrader: {repr(e)}")
        return

    log(f"\n[2] 连接 XtQuantTrader（session_id 随意取一个整数）...")
    log(f"    userdata_mini 路径: {USERDATA_MINI_PATH}")
    if not os.path.isdir(USERDATA_MINI_PATH):
        log(f"[FAIL] 路径不存在，请确认 userdata_mini 实际位置并修改脚本里的 USERDATA_MINI_PATH")
        return

    session_id = int(time.time())  # 用当前时间戳当 session_id，避免和已有会话冲突
    xt_trader = XtQuantTrader(USERDATA_MINI_PATH, session_id)

    class MyCallback(XtQuantTraderCallback):
        def on_disconnected(self):
            log("    [callback] on_disconnected 被触发")

        def on_stock_order(self, order):
            log(f"    [callback] on_stock_order: {order}")

        def on_stock_trade(self, trade):
            log(f"    [callback] on_stock_trade: {trade}")

        def on_order_error(self, order_error):
            log(f"    [callback] on_order_error: {order_error}")

        def on_cancel_error(self, cancel_error):
            log(f"    [callback] on_cancel_error: {cancel_error}")

    xt_trader.register_callback(MyCallback())

    try:
        xt_trader.start()
        connect_result = xt_trader.connect()
        log(f"[connect] 返回值: {connect_result}（0 通常表示成功，非 0 是错误码）")
    except Exception as e:
        log(f"[FAIL] start/connect 异常: {repr(e)}")
        return

    log(f"\n[3] 订阅账户 {ACCOUNT_ID}（股票账户 STOCK）...")
    try:
        acc = StockAccount(ACCOUNT_ID, "STOCK")
        subscribe_result = xt_trader.subscribe(acc)
        log(f"[subscribe] 返回值: {subscribe_result}（0 通常表示成功）")
    except Exception as e:
        log(f"[FAIL] subscribe 异常: {repr(e)}")
        return

    log("\n[4] 查询真实持仓 query_stock_positions...")
    try:
        positions = xt_trader.query_stock_positions(acc)
        if not positions:
            log("[WARN] 没有持仓，或者返回空列表（如果你手动开仓在券商那边确认过有持仓，这里应该不为空）")
        else:
            log(f"[OK] 拿到 {len(positions)} 条持仓：")
            for p in positions:
                try:
                    log(
                        f"    {p.stock_code}  数量={p.volume}  可用={getattr(p, 'can_use_volume', '?')}  "
                        f"成本价={p.avg_price}  市值={getattr(p, 'market_value', '?')}"
                    )
                except Exception as e:
                    log(f"    [解析单条持仓失败] {repr(e)}, 原始对象: {p}")
    except Exception as e:
        log(f"[FAIL] query_stock_positions 异常: {repr(e)}")

    log("\n[5] 查询账户资金 query_stock_asset...")
    try:
        asset = xt_trader.query_stock_asset(acc)
        if asset is None:
            log("[WARN] 没查到账户资金")
        else:
            log(
                f"[OK] 总资产={getattr(asset, 'total_asset', '?')}  "
                f"可用资金={getattr(asset, 'cash', '?')}  "
                f"市值={getattr(asset, 'market_value', '?')}"
            )
    except Exception as e:
        log(f"[FAIL] query_stock_asset 异常: {repr(e)}")

    log("\n验证结束，把完整输出发给 Claude。")
    xt_trader.stop()


if __name__ == "__main__":
    open(log_file, "w", encoding="utf-8").close()
    main()
