\
#!/usr/bin/env python3
import asyncio
import aiohttp

API_BASE = "http://localhost:8000/api/v1/dashboard"

async def demo():
    async with aiohttp.ClientSession() as session:
        print("📊 数据看板演示")
        print("=" * 50)

        print("\n[1] 获取总览...")
        async with session.get(f"{API_BASE}/overview") as resp:
            d = await resp.json()
            print(f"  → {d.get('data', {}).get('message', 'OK')}")

        print("\n[2] 价格趋势...")
        async with session.get(f"{API_BASE}/price-trend") as resp:
            d = await resp.json()
            print(f"  → {d.get('data', {}).get('message', 'OK')}")

        print("\n[3] 营养分析...")
        async with session.get(f"{API_BASE}/nutrition-analysis") as resp:
            d = await resp.json()
            print(f"  → {d.get('data', {}).get('message', 'OK')}")

        print("\n✅ 演示完成")

if __name__ == "__main__":
    asyncio.run(demo())
