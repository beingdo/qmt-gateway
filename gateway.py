import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn

# Add QMT bin.x64 to path (via ASCII junction C:\qmt to avoid encoding issues in tooling)
QMT_BIN = r"C:\qmt\bin.x64"
if QMT_BIN not in sys.path:
    sys.path.insert(0, QMT_BIN)

from xtquant import xtdata

app = FastAPI(title="QMT Gateway", version="0.1.0")

# Config
class Config:
    QMT_BIN = QMT_BIN
    HOST = "0.0.0.0"
    PORT = 8888
    LOG_DIR = Path(__file__).parent / "logs"
    CACHE_DIR = Path(__file__).parent / "cache"

    def __init__(self):
        self.LOG_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)

config = Config()

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    log_file = config.LOG_DIR / "gateway.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def check_qmt_connection():
    try:
        data_dir = xtdata.get_data_dir()
        if not data_dir or not os.path.isdir(data_dir):
            return False, "data_dir not found or invalid"
        return True, data_dir
    except Exception as e:
        return False, str(e)

@app.get("/health")
async def health():
    connected, info = check_qmt_connection()
    if connected:
        return JSONResponse({
            "status": "ok",
            "qmt_connected": True,
            "data_dir": info,
            "timestamp": datetime.now().isoformat()
        })
    else:
        return JSONResponse({
            "status": "error",
            "qmt_connected": False,
            "error": info,
            "timestamp": datetime.now().isoformat()
        }, status_code=503)

@app.get("/quote/history")
async def get_history(
    code: str = Query(..., description="Stock code, e.g. 600519.SH"),
    start: str = Query("20240101", description="Start date YYYYMMDD"),
    end: str = Query("20240110", description="End date YYYYMMDD"),
    period: str = Query("1d", description="Period: 1d, 1w, 1m")
):
    try:
        connected, _ = check_qmt_connection()
        if not connected:
            raise HTTPException(status_code=503, detail="QMT not connected")

        log(f"Downloading history: {code} {start}-{end} {period}")
        xtdata.download_history_data(code, period=period, start_time=start, end_time=end)

        data = xtdata.get_market_data_ex(
            field_list=[],
            stock_list=[code],
            period=period,
            start_time=start,
            end_time=end
        )

        df = data.get(code)
        if df is None or len(df) == 0:
            raise HTTPException(status_code=404, detail=f"No data for {code}")

        records = df.reset_index().to_dict('records')

        return JSONResponse({
            "code": code,
            "period": period,
            "start": start,
            "end": end,
            "count": len(records),
            "data": records,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        log(f"Error in get_history: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/quote/tick")
async def get_tick(code: str = Query(..., description="Stock code, e.g. 600519.SH")):
    try:
        connected, _ = check_qmt_connection()
        if not connected:
            raise HTTPException(status_code=503, detail="QMT not connected")

        log(f"Fetching tick: {code}")
        xtdata.subscribe_quote(code, period="tick", count=1)
        time.sleep(0.5)

        tick = xtdata.get_full_tick([code])
        if not tick or code not in tick:
            raise HTTPException(status_code=404, detail=f"No tick for {code}")

        tick_data = tick[code]

        return JSONResponse({
            "code": code,
            "tick": tick_data,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        log(f"Error in get_tick: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    log("Gateway startup")
    connected, info = check_qmt_connection()
    if connected:
        log(f"QMT connected, data_dir: {info}")
    else:
        log(f"WARNING: QMT not connected: {info}")

@app.on_event("shutdown")
async def shutdown_event():
    log("Gateway shutdown")

if __name__ == "__main__":
    log("Starting QMT Gateway...")
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info")
