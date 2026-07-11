import os
import sys
import requests
import json
import time
from pathlib import Path

# Gateway now binds to the internal IP only (not 0.0.0.0/localhost) — test against
# the same address AlphaDesk will use, so this test reflects real reachability.
GATEWAY_HOST = os.environ.get("QMT_GATEWAY_HOST", "10.0.0.69")
BASE_URL = f"http://{GATEWAY_HOST}:8888"

TOKEN_FILE = Path(__file__).parent / "gateway_token.txt"

def load_token():
    if not TOKEN_FILE.exists():
        print(f"ERROR: token file not found at {TOKEN_FILE}. Start gateway.py once to generate it.")
        sys.exit(1)
    return TOKEN_FILE.read_text(encoding="utf-8").strip()

TOKEN = load_token()
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def test_health():
    print("\n=== Testing /health ===")
    try:
        resp = requests.get(f"{BASE_URL}/health", headers=HEADERS, timeout=5)
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {repr(e)}")
        return False

def test_history():
    print("\n=== Testing /quote/history ===")
    try:
        resp = requests.get(
            f"{BASE_URL}/quote/history",
            params={"code": "600519.SH", "start": "20240101", "end": "20240110"},
            headers=HEADERS,
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Got {data.get('count')} rows")
        if data.get('count') > 0:
            print("First row:", data['data'][0])
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {repr(e)}")
        return False

def test_tick():
    print("\n=== Testing /quote/tick ===")
    try:
        resp = requests.get(
            f"{BASE_URL}/quote/tick",
            params={"code": "600519.SH"},
            headers=HEADERS,
            timeout=5
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if 'tick' in data:
            tick = data['tick']
            print(f"Code: {data['code']}")
            print(f"Last Price: {tick.get('lastPrice')}")
            print(f"Time: {tick.get('timetag')}")
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {repr(e)}")
        return False

def test_intraday():
    print("\n=== Testing /quote/intraday ===")
    try:
        resp = requests.get(
            f"{BASE_URL}/quote/intraday",
            params={"code": "600519.SH"},
            headers=HEADERS,
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Got {data.get('count')} points, pre_close={data.get('pre_close')}")
        if data.get('count'):
            print("First point:", data['points'][0])
            print("Last point:", data['points'][-1])
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {repr(e)}")
        return False

def test_account_positions():
    print("\n=== Testing /account/positions ===")
    try:
        resp = requests.get(f"{BASE_URL}/account/positions", headers=HEADERS, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 503:
            # Acceptable when no account is configured on this machine yet.
            print("Account not configured or trading session not connected:", resp.json())
            return True
        data = resp.json()
        print(f"Got {data.get('count')} positions")
        if data.get("count"):
            print("First position:", data["positions"][0])
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {repr(e)}")
        return False

def test_account_asset():
    print("\n=== Testing /account/asset ===")
    try:
        resp = requests.get(f"{BASE_URL}/account/asset", headers=HEADERS, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 503:
            # Acceptable when no account is configured on this machine yet.
            print("Account not configured or trading session not connected:", resp.json())
            return True
        data = resp.json()
        print("Asset:", data.get("asset"))
        return resp.status_code == 200
    except Exception as e:
        print(f"ERROR: {repr(e)}")
        return False

def test_no_token_rejected():
    print("\n=== Testing no-token request is rejected ===")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {resp.status_code} (expect 401)")
        return resp.status_code == 401
    except Exception as e:
        print(f"ERROR: {repr(e)}")
        return False

def main():
    print("QMT Gateway Test Suite")
    print(f"Base URL: {BASE_URL}")
    print("Ensure gateway is running: python gateway.py")

    time.sleep(1)

    results = {
        "health": test_health(),
        "history": test_history(),
        "tick": test_tick(),
        "intraday": test_intraday(),
        "account_positions": test_account_positions(),
        "account_asset": test_account_asset(),
        "no_token_rejected": test_no_token_rejected()
    }

    print("\n" + "=" * 50)
    print("Test Results:")
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")

    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
