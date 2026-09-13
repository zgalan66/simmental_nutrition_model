"""
verify_e2e.py — 端到端验证：复现你之前跑通的配方
目标：CP14-18, ME9-12, Ca0.6-1.2
候选：玉米/豆粕/麦麸/苜蓿/石粉
预期：能求出可行解，配比和=100%，约束全达标
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from services.recommendation_engine import optimize_formula


class Feed:
    def __init__(self, name, **kw):
        self.name = name
        for k, v in kw.items():
            setattr(self, k, v)


# 对标你 Excel 的真实数据（%DM 基准营养值）
feeds = {
    "玉米": Feed("玉米", cp_pct=8.5, ndf_pct=9.5, adf_pct=3.5, me_mj_kg=13.8,
                 tdn_pct=88.0, ca_pct=0.02, p_pct=0.27, dm_pct=87.0, price_yuan_kg=2.6),
    "豆粕（43%）": Feed("豆粕（43%）", cp_pct=44.0, ndf_pct=12.0, adf_pct=5.0, me_mj_kg=12.5,
                 tdn_pct=90.0, ca_pct=0.3, p_pct=0.7, dm_pct=89.0, price_yuan_kg=3.8),
    "麦麸": Feed("麦麸", cp_pct=15.5, ndf_pct=40.0, adf_pct=12.0, me_mj_kg=10.5,
                 tdn_pct=80.0, ca_pct=0.1, p_pct=1.2, dm_pct=88.0, price_yuan_kg=1.94),
    "苜蓿（初花期）": Feed("苜蓿（初花期）", cp_pct=17.0, ndf_pct=45.0, adf_pct=33.0, me_mj_kg=8.5,
                 tdn_pct=65.0, ca_pct=1.4, p_pct=0.24, dm_pct=89.0, price_yuan_kg=2.2),
    "石粉（碳酸钙）": Feed("石粉（碳酸钙）", cp_pct=0, ndf_pct=0, adf_pct=0, me_mj_kg=0,
                 tdn_pct=0, ca_pct=38.0, p_pct=0, dm_pct=99.0, price_yuan_kg=0.4),
}

targets = {
    "cp_pct": {"min": 14, "max": 18},      # 下限严格 → 引擎必须加豆粕满足
    "me_mj_kg": {"min": 9, "max": 12},
    "ca_pct": {"min": 0.6, "max": 1.2},    # 上限加松弛，允许轻微贴边
}
candidates = [
    {"name": "玉米", "max_ratio": 60},
    {"name": "豆粕（43%）", "max_ratio": 30},
    {"name": "麦麸", "max_ratio": 30},
    {"name": "苜蓿（初花期）", "max_ratio": 40},
    {"name": "石粉（碳酸钙）", "max_ratio": 3},
]

result = optimize_formula(targets, candidates, feeds, total_weight=100)

print("status:", result['status'])
if result['status'] == 'infeasible':
    print("诊断:", result.get('diagnosis'))
    sys.exit(1)

print("\n配方:")
for f in result['formula']:
    print(f"  {f['name']:<14s} {f['ratio_pct']:>6.2f}%  ({f['ratio']:.3f} kg)")
total_pct = sum(f['ratio_pct'] for f in result['formula'])
print(f"\n配比总和: {total_pct:.2f}% (应=100)")
print(f"总成本: {result['total_cost']:.2f} 元 / 100kg")

nr = result['nutrition_result']
print(f"\n营养结果（模型A复核）:")
print(f"  CP={nr['cp_pct']}%  ME={nr['me_mj_kg']}  NDF={nr['ndf_pct']}%  Ca={nr['ca_pct']}%  P={nr['p_pct']}%")

print(f"\n约束检查:")
all_ok = True
for cs in result['constraint_status']:
    print(f"  {cs['field']}: 实际{cs['actual']} [{cs['min']},{cs['max']}] → {cs['status']}")
    if cs['status'] != 'ok':
        all_ok = False

binding = [s for s in result['shadow_prices'] if s['binding']]
print(f"\n紧约束(影子价格≠0): {[s['constraint'] for s in binding]}")

assert abs(total_pct - 100) < 0.1, "配比和应为100%"
assert all_ok, "所有约束应达标"
print("\n🎉 端到端验证通过 —— 配方可行、约束全达标、配比和=100%")
print("   （注：钙上限设为2.0%更符合育肥牛实际；若坚持1.2%需减少石粉或选低钙原料）")
