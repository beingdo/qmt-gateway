import os
import sys
import json
import time
import secrets
import hmac
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.responses import JSONResponse
import uvicorn

# Add QMT bin.x64 to path (via ASCII junction C:\qmt to avoid encoding issues in tooling)
QMT_BIN = r"C:\qmt\bin.x64"
if QMT_BIN not in sys.path:
    sys.path.insert(0, QMT_BIN)

# userdata_mini directory used by the trading session (same path test_xttrade.py verified)
USERDATA_MINI_PATH = r"C:\qmt\userdata_mini"

from xtquant import xtdata

app = FastAPI(title="QMT Gateway", version="0.1.0")

# Config
class Config:
    QMT_BIN = QMT_BIN
    # Bind to the VPC-internal IP only — never 0.0.0.0, so this process
    # never listens on the public NIC regardless of firewall/security-group
    # misconfiguration. Override with QMT_GATEWAY_HOST if the internal IP changes.
    HOST = os.environ.get("QMT_GATEWAY_HOST", "10.0.0.69")
    PORT = 8888
    LOG_DIR = Path(__file__).parent / "logs"
    CACHE_DIR = Path(__file__).parent / "cache"
    TOKEN_FILE = Path(__file__).parent / "gateway_token.txt"
    # Real fund account numbers must never be committed to this public repo.
    # Same lookup order/encoding as test_xttrade.py: env var first, then this
    # local file (already in .gitignore).
    ACCOUNT_ID_FILE = Path(__file__).parent / "account_id.txt"

    def __init__(self):
        self.LOG_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.TOKEN = self._load_or_create_token()
        self.ACCOUNT_ID = self._load_account_id()

    def _load_or_create_token(self):
        if self.TOKEN_FILE.exists():
            return self.TOKEN_FILE.read_text(encoding="utf-8").strip()
        token = secrets.token_urlsafe(32)
        self.TOKEN_FILE.write_text(token, encoding="utf-8")
        return token

    def _load_account_id(self):
        account_id = os.environ.get("QMT_ACCOUNT_ID", "").strip()
        if not account_id and self.ACCOUNT_ID_FILE.is_file():
            # utf-8-sig strips a possible BOM (e.g. from PowerShell's
            # `Out-File -Encoding utf8`) that would otherwise poison the
            # account string and make xt_trader.subscribe() fail silently.
            account_id = self.ACCOUNT_ID_FILE.read_text(encoding="utf-8-sig").strip()
        return account_id

config = Config()

# Long-lived trading session state. XtQuantTrader.connect()/subscribe() has
# real overhead and QMT may cap concurrent sessions, so we establish this once
# at startup and reuse it for every /account/* request instead of reconnecting
# per request. Populated by init_trader_session() below.
trader_state = {
    "trader": None,
    "account": None,
    "connected": False,
    "error": None,
}

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    provided = authorization[len("Bearer "):]
    if not hmac.compare_digest(provided, config.TOKEN):
        raise HTTPException(status_code=401, detail="Invalid token")
    return True

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
async def health(_: bool = Depends(verify_token)):
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
    period: str = Query("1d", description="Period: 1d, 1w, 1m"),
    _: bool = Depends(verify_token)
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
async def get_tick(
    code: str = Query(..., description="Stock code, e.g. 600519.SH"),
    _: bool = Depends(verify_token)
):
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

@app.get("/quote/intraday")
async def get_intraday(
    code: str = Query(..., description="Stock code, e.g. 002475.SZ"),
    _: bool = Depends(verify_token)
):
    try:
        connected, _ = check_qmt_connection()
        if not connected:
            raise HTTPException(status_code=503, detail="QMT not connected")

        today = time.strftime("%Y%m%d")
        log(f"Fetching intraday: {code} {today}")
        xtdata.subscribe_quote(code, period="tick", count=-1)
        time.sleep(1)

        data = xtdata.get_market_data_ex(
            field_list=[],
            stock_list=[code],
            period="tick",
            start_time=today,
            end_time=today
        )

        df = data.get(code)
        if df is None or len(df) == 0:
            raise HTTPException(status_code=404, detail=f"No intraday data for {code}")

        points = [
            {"time": str(t), "price": p, "volume": v}
            for t, p, v in zip(df.index.tolist(), df["lastPrice"].tolist(), df["volume"].tolist())
        ]
        pre_close = df["lastClose"].iloc[0]

        return JSONResponse({
            "code": code,
            "date": today,
            "pre_close": pre_close,
            "count": len(points),
            "points": points,
            "timestamp": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        log(f"Error in get_intraday: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/account/positions")
async def get_account_positions(_: bool = Depends(verify_token)):
    if not config.ACCOUNT_ID:
        raise HTTPException(status_code=503, detail="Account not configured: set QMT_ACCOUNT_ID or create account_id.txt")
    if not trader_state["connected"] or trader_state["trader"] is None:
        raise HTTPException(status_code=503, detail=f"Trading session not connected: {trader_state['error']}")

    try:
        positions = trader_state["trader"].query_stock_positions(trader_state["account"])
        result = [
            {
                "stock_code": p.stock_code,
                "volume": p.volume,
                "can_use_volume": getattr(p, "can_use_volume", None),
                "avg_price": p.avg_price,
                "market_value": getattr(p, "market_value", None),
            }
            for p in (positions or [])
        ]

        return JSONResponse({
            "count": len(result),
            "positions": result,
            "timestamp": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        log(f"Error in get_account_positions: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/account/asset")
async def get_account_asset(_: bool = Depends(verify_token)):
    if not config.ACCOUNT_ID:
        raise HTTPException(status_code=503, detail="Account not configured: set QMT_ACCOUNT_ID or create account_id.txt")
    if not trader_state["connected"] or trader_state["trader"] is None:
        raise HTTPException(status_code=503, detail=f"Trading session not connected: {trader_state['error']}")

    try:
        asset = trader_state["trader"].query_stock_asset(trader_state["account"])
        if asset is None:
            raise HTTPException(status_code=404, detail="No asset data returned")

        result = {
            "total_asset": getattr(asset, "total_asset", None),
            "cash": getattr(asset, "cash", None),
            "market_value": getattr(asset, "market_value", None),
        }

        return JSONResponse({
            "asset": result,
            "timestamp": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        log(f"Error in get_account_asset: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def init_trader_session():
    """Establish the long-lived XtQuantTrader session once at startup.

    Read-only account queries only — this module must never call
    order_stock/cancel_order or any other trade-execution method.
    Any failure here (no account configured, import failure, connect/subscribe
    error) is logged and leaves trader_state disconnected; it must never raise
    and must never block gateway startup, matching how check_qmt_connection()
    tolerates a not-yet-connected QMT client.
    """
    if not config.ACCOUNT_ID:
        log("WARNING: No QMT account configured (QMT_ACCOUNT_ID env var or account_id.txt) - /account/* endpoints will be unavailable")
        trader_state["error"] = "account not configured"
        return

    try:
        from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
        from xtquant.xttype import StockAccount
    except Exception as e:
        log(f"WARNING: Failed to import xttrader: {repr(e)}")
        trader_state["error"] = f"import failed: {e}"
        return

    class GatewayTraderCallback(XtQuantTraderCallback):
        def on_disconnected(self):
            log("[trader callback] on_disconnected")
            trader_state["connected"] = False

        def on_stock_order(self, order):
            log(f"[trader callback] on_stock_order: {order}")

        def on_stock_trade(self, trade):
            log(f"[trader callback] on_stock_trade: {trade}")

        def on_order_error(self, order_error):
            log(f"[trader callback] on_order_error: {order_error}")

        def on_cancel_error(self, cancel_error):
            log(f"[trader callback] on_cancel_error: {cancel_error}")

    if not os.path.isdir(USERDATA_MINI_PATH):
        log(f"WARNING: userdata_mini path not found: {USERDATA_MINI_PATH} - /account/* endpoints will be unavailable")
        trader_state["error"] = "userdata_mini path not found"
        return

    try:
        session_id = int(time.time())
        trader = XtQuantTrader(USERDATA_MINI_PATH, session_id)
        trader.register_callback(GatewayTraderCallback())
        trader.start()

        connect_result = trader.connect()
        if connect_result != 0:
            log(f"WARNING: XtQuantTrader.connect() failed, code={connect_result}")
            trader_state["error"] = f"connect failed: {connect_result}"
            return

        account = StockAccount(config.ACCOUNT_ID, "STOCK")
        subscribe_result = trader.subscribe(account)
        if subscribe_result != 0:
            log(f"WARNING: trader.subscribe() failed, code={subscribe_result}")
            trader_state["error"] = f"subscribe failed: {subscribe_result}"
            return

        trader_state["trader"] = trader
        trader_state["account"] = account
        trader_state["connected"] = True
        trader_state["error"] = None
        log("Trading session established (account subscribed, read-only queries only)")
    except Exception as e:
        log(f"WARNING: Failed to initialize trading session: {repr(e)}")
        trader_state["error"] = str(e)

@app.on_event("startup")
async def startup_event():
    log("Gateway startup")
    log(f"Auth token (from {config.TOKEN_FILE}): {config.TOKEN}")
    log(f"Listening on {config.HOST}:{config.PORT} (internal-only, not public)")
    connected, info = check_qmt_connection()
    if connected:
        log(f"QMT connected, data_dir: {info}")
    else:
        log(f"WARNING: QMT not connected: {info}")

    init_trader_session()

@app.on_event("shutdown")
async def shutdown_event():
    log("Gateway shutdown")

if __name__ == "__main__":
    log("Starting QMT Gateway...")
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info")
