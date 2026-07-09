import sys
import requests
import json
import time

BASE_URL = "http://localhost:8888"

def test_health():
    print("\n=== Testing /health ===")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
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

def main():
    print("QMT Gateway Test Suite")
    print(f"Base URL: {BASE_URL}")
    print("Ensure gateway is running: python gateway.py")

    time.sleep(1)

    results = {
        "health": test_health(),
        "history": test_history(),
        "tick": test_tick()
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
