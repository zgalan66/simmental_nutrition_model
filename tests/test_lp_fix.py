import sys, os
sys.path.insert(0, os.getcwd())
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_recommend_with_salt():
    payload = {
        "target_weight": 500,
        "daily_gain": 1.2,
        "candidates": [
            {"name": "玉米", "ratio": 15},
            {"name": "豆粕（43%）", "ratio": 8},
            {"name": "玉米秸秆黄贮", "ratio": 40},
            {"name": "苜蓿（初花期）", "ratio": 16},
            {"name": "小麦秸秆", "ratio": 20},
            {"name": "盐", "ratio": 1}
        ],
        "targets": {
            "cp": {"min": 11.0, "max": 14.0, "slack": 0.5},
            "me": {"min": 10.5, "max": 13.0, "slack": 0.5},
            "ndf": {"min": 35.0, "max": 45.0, "slack": 2.0},
            "ca": {"min": 0.4, "max": 0.8, "slack": 0.1},
            "p": {"min": 0.25, "max": 0.6, "slack": 0.1}
        }
    }
    resp = client.post("/api/v1/recommend", json=payload)
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"success={data.get('success')}, status={data.get('data',{}).get('status')}")
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["data"]["status"] == "optimal"
    print("PASS: LP optimal regression test passed!")

if __name__ == "__main__":
    test_recommend_with_salt()