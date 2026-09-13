import asyncio
from database import AsyncSessionLocal
from models.feed_models import Feed
from sqlalchemy import select

CHECK = ["玉米", "大麦（Barley）", "麦麸", "白玉米（White Corn）", "喷浆玉米皮", "豆油", "石粉", "盐（氯化钠）"]

async def main():
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Feed).where(Feed.name.in_(CHECK)))
        result = {f.name: f.price_yuan_kg for f in r.scalars().all()}
        print("=" * 50)
        for name in CHECK:
            print(f"{name:20s} => {result.get(name, '(数据库里没这条)')}")
        print("=" * 50)
        
        # 统计
        total = (await db.execute(select(Feed))).scalars().all()
        with_price = sum(1 for f in total if f.price_yuan_kg is not None)
        print(f"共 {len(total)} 条原料，有价格的 {with_price} 条，无价格的 {len(total) - with_price} 条")
        
        # 打印所有价格为 null 的原料
        null_prices = [f.name for f in total if f.price_yuan_kg is None]
        if null_prices:
            print("\n价格为 null 的原料：")
            for n in null_prices:
                print(f"  - {n}")

if __name__ == "__main__":
    asyncio.run(main())