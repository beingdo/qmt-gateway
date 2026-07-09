import os
import sys
import time

QMT_BIN = r"C:\qmt\bin.x64"
if QMT_BIN not in sys.path:
    sys.path.insert(0, QMT_BIN)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(SCRIPT_DIR, "test_xtdata.log")

def log(msg):
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def main():
    log("=" * 60)
    log("M1 QMT Test")
    log("=" * 60)

    log("\nStep 1: import xtquant...")
    try:
        from xtquant import xtdata
        log("[OK] xtquant imported")
        try:
            data_dir = xtdata.get_data_dir()
            log("data_dir = " + str(data_dir))
        except:
            pass
    except Exception as e:
        log("[FAIL] import xtquant error: " + repr(e))
        return

    code = "600519.SH"

    log("\nStep 2: download_history_data...")
    try:
        xtdata.download_history_data(code, period="1d", start_time="20240101", end_time="20240110")
        data = xtdata.get_market_data_ex([], [code], period="1d", start_time="20240101", end_time="20240110")
        df = data.get(code)
        if df is None or len(df) == 0:
            log("[WARN] no history data")
        else:
            log("[OK] got " + str(len(df)) + " rows")
            log(df.tail().to_string())
    except Exception as e:
        log("[FAIL] history error: " + repr(e))

    log("\nStep 3: get_full_tick...")
    try:
        xtdata.subscribe_quote(code, period="tick", count=1)
        time.sleep(1)
        tick = xtdata.get_full_tick([code])
        if not tick or code not in tick:
            log("[WARN] no tick data")
        else:
            log("[OK] tick: " + str(tick[code]))
    except Exception as e:
        log("[FAIL] tick error: " + repr(e))

    log("\n" + "=" * 60)
    log("Test Complete")
    log("=" * 60)

if __name__ == "__main__":
    open(log_file, "w", encoding="utf-8").close()
    main()
