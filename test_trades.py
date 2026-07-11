import os
import sys
import time

QMT_BIN = r"C:\qmt\bin.x64"
if QMT_BIN not in sys.path:
    sys.path.insert(0, QMT_BIN)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(SCRIPT_DIR, "test_trades.log")
account_id_file = os.path.join(SCRIPT_DIR, "account_id.txt")

ACCOUNT_ID = os.environ.get("QMT_ACCOUNT_ID", "").strip()
if not ACCOUNT_ID and os.path.isfile(account_id_file):
    ACCOUNT_ID = open(account_id_file, "r", encoding="utf-8-sig").read().strip()
if not ACCOUNT_ID:
    print(f"请先设置账号：环境变量 QMT_ACCOUNT_ID 或 {account_id_file}")
    sys.exit(1)

USERDATA_MINI_PATH = r"C:\qmt\userdata_mini"


def log(msg):
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def main():
    from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
    from xtquant.xttype import StockAccount

    log("=" * 60)
    log("历史成交/委托记录可用性验证")
    log("=" * 60)

    session_id = int(time.time())
    xt_trader = XtQuantTrader(USERDATA_MINI_PATH, session_id)

    class MyCallback(XtQuantTraderCallback):
        def on_disconnected(self):
            log("    [callback] on_disconnected")

    xt_trader.register_callback(MyCallback())
    xt_trader.start()
    connect_result = xt_trader.connect()
    log(f"[connect] {connect_result}")

    acc = StockAccount(ACCOUNT_ID, "STOCK")
    subscribe_result = xt_trader.subscribe(acc)
    log(f"[subscribe] {subscribe_result}")

    log("\n[1] query_stock_trades（今日成交）...")
    try:
        trades = xt_trader.query_stock_trades(acc)
        if not trades:
            log("[WARN] 没有今日成交记录（如果你今天没交易，这是正常的）")
        else:
            log(f"[OK] 拿到 {len(trades)} 条成交记录，样例（打印全部字段看看有没有日期信息）：")
            for t in trades[:5]:
                log(f"    {vars(t) if hasattr(t, '__dict__') else t}")
    except Exception as e:
        log(f"[FAIL] query_stock_trades 异常: {repr(e)}")

    log("\n[2] query_stock_orders（今日委托）...")
    try:
        orders = xt_trader.query_stock_orders(acc)
        if not orders:
            log("[WARN] 没有今日委托记录")
        else:
            log(f"[OK] 拿到 {len(orders)} 条委托记录，样例：")
            for o in orders[:5]:
                log(f"    {vars(o) if hasattr(o, '__dict__') else o}")
    except Exception as e:
        log(f"[FAIL] query_stock_orders 异常: {repr(e)}")

    log("\n[3] 尝试查更早的历史成交（各种可能的方法名/参数，逐个试探）...")
    # xtquant 不同版本 API 差异较大，这里穷举几种可能存在的历史查询方式，
    # 能跑通哪个就用哪个，跑不通的都是正常现象（说明这个版本没有这个能力）。
    candidates = [
        ("query_stock_trades(acc, start_time, end_time)", lambda: xt_trader.query_stock_trades(acc, "20260101", "20260711")),
        ("query_stock_trades_his (如果存在)", lambda: getattr(xt_trader, "query_stock_trades_his")(acc)),
        ("query_history_trades (如果存在)", lambda: getattr(xt_trader, "query_history_trades")(acc)),
    ]
    for name, fn in candidates:
        try:
            result = fn()
            log(f"[OK] {name} 可用，返回 {len(result) if result else 0} 条")
        except AttributeError:
            log(f"[SKIP] {name}：这个方法不存在")
        except Exception as e:
            log(f"[FAIL] {name}: {repr(e)}")

    log("\n验证结束，把完整输出发给 Claude。")
    xt_trader.stop()


if __name__ == "__main__":
    open(log_file, "w", encoding="utf-8").close()
    main()
