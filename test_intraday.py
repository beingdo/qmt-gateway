import os
import sys
import time

QMT_BIN = r"C:\qmt\bin.x64"
if QMT_BIN not in sys.path:
    sys.path.insert(0, QMT_BIN)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(SCRIPT_DIR, "test_intraday.log")

def log(msg):
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def main():
    from xtquant import xtdata

    code = "002475.SZ"  # 立讯精密，用来对照手机软件

    log("=" * 60)
    log("分时/逐笔数据可用性验证")
    log("=" * 60)

    # 1) 分时：用今天的 tick 历史序列近似分时图（价格随时间变化）
    log("\n[1] 今日 tick 序列（分时图数据源）...")
    try:
        today = time.strftime("%Y%m%d")
        xtdata.subscribe_quote(code, period="tick", count=-1)
        time.sleep(1)
        data = xtdata.get_market_data_ex(
            field_list=[],
            stock_list=[code],
            period="tick",
            start_time=today,
            end_time=today,
        )
        df = data.get(code)
        if df is None or len(df) == 0:
            log("[WARN] 拿不到今日 tick 序列，可能需要先 download_history_data 或者当天还没有足够 tick")
        else:
            log(f"[OK] 拿到 {len(df)} 条 tick，末尾 5 条：")
            log(df.tail().to_string())
    except Exception as e:
        log(f"[FAIL] {repr(e)}")

    # 2) 逐笔成交：get_transaction_data，通常需要 Level-2 权限
    log("\n[2] 逐笔成交 get_transaction_data...")
    try:
        transactions = xtdata.get_transaction_data([code], count=20)
        if not transactions or code not in transactions or len(transactions[code]) == 0:
            log("[WARN] 拿不到逐笔成交，可能没有 Level-2 权限，或者这个接口需要额外订阅")
        else:
            log(f"[OK] 拿到逐笔成交，样例：")
            log(str(transactions[code][:5]))
    except AttributeError:
        log("[FAIL] xtdata 没有 get_transaction_data 这个方法——这个版本/权限不支持逐笔成交")
    except Exception as e:
        log(f"[FAIL] {repr(e)}")

    log("\n验证结束，把完整输出发给 Claude。")

if __name__ == "__main__":
    open(log_file, "w", encoding="utf-8").close()
    main()
