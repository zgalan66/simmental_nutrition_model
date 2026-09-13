\
#!/usr/bin/env python3
import asyncio
import aiohttp

API_BASE = "http://localhost:8000/api/v1/alerts"

async def demo():
    async with aiohttp.ClientSession() as session:
        print("=" * 70)
        print("🚨 预警系统完整演示")
        print("=" * 70)

        print("\n[1] 初始化默认规则...")
        async with session.post(f"{API_BASE}/init-defaults") as resp:
            d = await resp.json()
            print(f"  → {d.get('message', d)}")

        print("\n[2] 查看预警规则...")
        async with session.get(f"{API_BASE}/rules") as resp:
            d = await resp.json()
            for r in d.get("data", []):
                print(f"  [{r['alert_type']}] {r['name']} ({r['severity']})")

        print("\n[3] 触发价格异常检测...")
        async with session.post(f"{API_BASE}/check/price", json={}) as resp:
            d = await resp.json()
            print(f"  → {d.get('data', {}).get('count', 0)} 条预警触发")

        print("\n[4] 触发营养不达标检测...")
        async with session.post(f"{API_BASE}/check/nutrition", json={}) as resp:
            d = await resp.json()
            print(f"  → {d.get('data', {}).get('count', 0)} 条预警触发")

        print("\n[5] 查看活跃预警...")
        async with session.get(f"{API_BASE}/active") as resp:
            d = await resp.json()
            total = d.get("data", {}).get("total", 0)
            print(f"  → 共 {total} 条活跃预警")

        print("\n[6] 预警汇总...")
        async with session.get(f"{API_BASE}/summary") as resp:
            d = await resp.json()
            s = d.get("data", {})
            print(f"  总: {s.get('total', 0)} | 活跃: {s.get('active', 0)}")

        print("\n" + "=" * 70)
        print("✅ 演示完成")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(demo())
