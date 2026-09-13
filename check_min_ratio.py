import re
from pathlib import Path

files = [
    "recommendation_engine.py",
    "services/recommendation_engine.py",
    "api/routers/recommend.py",
]

found = False
for f in files:
    p = Path(f)
    if not p.exists():
        continue
    txt = p.read_text(encoding="utf-8")
    print(f"\n📄 {f}")
    for kw in ["min_ratio", "min_pct", "lower_bound", "bounds", "LpVariable"]:
        hits = [(m.start(), m.group()) for m in re.finditer(kw, txt)]
        if hits:
            found = True
            print(f"  ✅ '{kw}' 出现 {len(hits)} 次")
            # 打印附近上下文
            for pos, _ in hits[:2]:
                start = max(0, pos-80)
                end = min(len(txt), pos+120)
                print(f"     ...{txt[start:end]}...")
        else:
            print(f"  ❌ '{kw}' 未出现")

if not found:
    print("\n⚠️ 未检测到 min_ratio / 下限约束逻辑")
else:
    print("\n✅ 检测到约束相关代码")