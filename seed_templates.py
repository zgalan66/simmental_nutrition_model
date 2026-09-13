"""初始化西门塔尔公牛各阶段的标准约束模板"""
import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal, engine
from models.base import Base
from models.template_models import ConstraintTemplate


TEMPLATES = [
    {
        "name": "架子牛期",
        "category": "架子牛",
        "description": "300-400kg 生长期，日增重 0.8-1.0kg，注重骨架发育",
        "targets": {
            "cp_pct": {"min": 12.0, "max": 14.5},
            "me_mj_kg": {"min": 9.5, "max": 11.0},
            "ndf_pct": {"min": 35.0, "max": 50.0},
            "ca_pct": {"min": 0.4, "max": 0.7},
            "p_pct": {"min": 0.25, "max": 0.4},
        },
        "candidates": [
            {"name": "玉米", "min_ratio": 0, "max_ratio": 40},
            {"name": "麦麸", "min_ratio": 0, "max_ratio": 25},
            {"name": "豆粕（43%）", "min_ratio": 0, "max_ratio": 12},
            {"name": "苜蓿（初花期）", "min_ratio": 10, "max_ratio": 40},
            {"name": "玉米秸秆青贮（无籽粒）", "min_ratio": 0, "max_ratio": 40},
            {"name": "石粉（碳酸钙）", "min_ratio": 0, "max_ratio": 2},
            {"name": "磷酸氢钙", "min_ratio": 0, "max_ratio": 1},
        ],
        "is_default": True,
    },
    {
        "name": "育肥前期",
        "category": "育肥期",
        "description": "400-500kg，日增重 1.0-1.2kg，快速增重阶段",
        "targets": {
            "cp_pct": {"min": 12.0, "max": 14.5},
            "me_mj_kg": {"min": 10.0, "max": 11.5},
            "ndf_pct": {"min": 25.0, "max": 40.0},
            "ca_pct": {"min": 0.5, "max": 0.8},
            "p_pct": {"min": 0.3, "max": 0.5},
        },
        "candidates": [
            {"name": "玉米", "min_ratio": 0, "max_ratio": 55},
            {"name": "麦麸", "min_ratio": 0, "max_ratio": 20},
            {"name": "豆粕（43%）", "min_ratio": 0, "max_ratio": 15},
            {"name": "苜蓿（初花期）", "min_ratio": 0, "max_ratio": 30},
            {"name": "全株玉米青贮（30% DM）", "min_ratio": 0, "max_ratio": 35},
            {"name": "石粉（碳酸钙）", "min_ratio": 0, "max_ratio": 2},
            {"name": "磷酸氢钙", "min_ratio": 0, "max_ratio": 1},
        ],
        "is_default": True,
    },
    {
        "name": "育肥后期",
        "category": "育肥期",
        "description": "500kg 以上，日增重 1.2-1.4kg，冲刺出栏",
        "targets": {
            "cp_pct": {"min": 11.0, "max": 13.0},
            "me_mj_kg": {"min": 11.0, "max": 12.0},
            "ndf_pct": {"min": 20.0, "max": 35.0},
            "ca_pct": {"min": 0.5, "max": 0.8},
            "p_pct": {"min": 0.3, "max": 0.5},
        },
        "candidates": [
            {"name": "玉米", "min_ratio": 20, "max_ratio": 65},
            {"name": "麦麸", "min_ratio": 0, "max_ratio": 15},
            {"name": "豆粕（43%）", "min_ratio": 0, "max_ratio": 12},
            {"name": "苜蓿（初花期）", "min_ratio": 0, "max_ratio": 20},
            {"name": "石粉（碳酸钙）", "min_ratio": 0, "max_ratio": 2},
            {"name": "磷酸氢钙", "min_ratio": 0, "max_ratio": 1},
        ],
        "is_default": True,
    },
    {
        "name": "妊娠期母牛",
        "category": "母牛",
        "description": "妊娠中期至后期，控制膘情，保证胎儿发育",
        "targets": {
            "cp_pct": {"min": 11.0, "max": 13.0},
            "me_mj_kg": {"min": 9.0, "max": 11.0},
            "ndf_pct": {"min": 35.0, "max": 55.0},
            "ca_pct": {"min": 0.4, "max": 0.8},
            "p_pct": {"min": 0.25, "max": 0.4},
        },
        "candidates": [
            {"name": "玉米", "min_ratio": 0, "max_ratio": 30},
            {"name": "麦麸", "min_ratio": 0, "max_ratio": 20},
            {"name": "豆粕（43%）", "min_ratio": 0, "max_ratio": 10},
            {"name": "苜蓿（初花期）", "min_ratio": 15, "max_ratio": 50},
            {"name": "玉米秸秆青贮（无籽粒）", "min_ratio": 0, "max_ratio": 50},
            {"name": "石粉（碳酸钙）", "min_ratio": 0, "max_ratio": 2},
            {"name": "磷酸氢钙", "min_ratio": 0, "max_ratio": 1},
        ],
        "is_default": True,
    },
    {
        "name": "泌乳期母牛",
        "category": "母牛",
        "description": "哺乳期，日产奶 8-12kg，高能量高蛋白",
        "targets": {
            "cp_pct": {"min": 13.0, "max": 16.0},
            "me_mj_kg": {"min": 10.0, "max": 12.0},
            "ndf_pct": {"min": 28.0, "max": 45.0},
            "ca_pct": {"min": 0.6, "max": 1.0},
            "p_pct": {"min": 0.35, "max": 0.55},
        },
        "candidates": [
            {"name": "玉米", "min_ratio": 0, "max_ratio": 50},
            {"name": "麦麸", "min_ratio": 0, "max_ratio": 25},
            {"name": "豆粕（43%）", "min_ratio": 5, "max_ratio": 20},
            {"name": "苜蓿（初花期）", "min_ratio": 0, "max_ratio": 35},
            {"name": "全株玉米青贮（30% DM）", "min_ratio": 0, "max_ratio": 35},
            {"name": "石粉（碳酸钙）", "min_ratio": 0, "max_ratio": 2},
            {"name": "磷酸氢钙", "min_ratio": 0, "max_ratio": 1.5},
        ],
        "is_default": True,
    },
]


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    created = 0
    async with AsyncSessionLocal() as db:
        for td in TEMPLATES:
            existing = await db.execute(select(ConstraintTemplate).where(ConstraintTemplate.name == td["name"]))
            if existing.scalar_one_or_none():
                print(f"  跳过（已存在）: {td['name']}")
                continue
            db.add(ConstraintTemplate(**td))
            print(f"  新增: {td['name']}")
            created += 1
        await db.commit()

    print(f"OK 共创建 {created} 个模板")


if __name__ == "__main__":
    asyncio.run(main())
