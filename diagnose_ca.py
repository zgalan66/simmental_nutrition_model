import asyncio
from database import AsyncSessionLocal
from models.feed_models import Feed
from sqlalchemy import select

async def main():
    names = [
        "玉米", "豆粕（43%）", "麦麸", "带壳花生饼",
        "苜蓿（初花期）", "全株玉米青贮（30% DM）",
        "石粉（碳酸钙）", "磷酸氢钙", "盐（氯化钠）", "小苏打"
    ]
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Feed).where(Feed.name.in_(names)))
        feeds = {f.name: f for f in res.scalars().all()}
        
        print("=== 关键原料的 Ca / P 贡献 ===\n")
        print(f"{'原料':<22} {'Ca%':>6} {'P%':>6} {'DM%':>5}")
        print("-" * 45)
        for n in names:
            f = feeds.get(n)
            if f:
                print(f"{n:<22} {f.ca_pct or 0:>6.3f} {f.p_pct or 0:>6.3f} {f.dm_pct or 0:>5}")
        
        # 模拟：100% 石粉能贡献多少钙
        print("\n=== 钙贡献测算 ===")
        stone = feeds["石粉（碳酸钙）"]
        dcp = feeds["磷酸氢钙"]
        
        print(f"\n石粉 Ca={stone.ca_pct}%, DM={stone.dm_pct}%")
        print(f"磷酸氢钙 Ca={dcp.ca_pct}%, P={dcp.p_pct}%")
        
        # 假设配方：石粉占 x%，其他占 (100-x)%
        # 全价料 Ca = x * (stone.ca_pct/100) * (stone.dm_pct/100) / ...
        # 简化：石粉 DM 99%，钙贡献 ≈ x * 0.39
        for x in [1, 2, 3, 5, 10]:
            ca_contribution = x * (stone.ca_pct / 100) * (stone.dm_pct / 100)
            print(f"  石粉 {x:>4}% → 钙贡献 {ca_contribution*100:.3f}% (即 {ca_contribution*100:.2f} 个百分点)")

asyncio.run(main())