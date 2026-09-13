import pandas as pd

df = pd.read_excel('data/原料含量.xlsx', header=1)

# 重命名重复列
cols = list(df.columns)
seen = {}
new_cols = []
for c in cols:
    c = str(c).strip()
    if c in seen:
        seen[c] += 1
        new_cols.append(f"{c}__dup{seen[c]}")
    else:
        seen[c] = 0
        new_cols.append(c)
df.columns = new_cols

# 找出所有跟价格相关的列
print("=== 所有含 价/元 的列 ===")
for i, c in enumerate(df.columns):
    if '价' in str(c) or '元' in str(c):
        print(f"  [{i}] {c!r}")

# 定位价格列
price_col = None
for c in df.columns:
    if '单价' in str(c):
        price_col = c
        break

print(f"\n=== 价格列名：{price_col!r} ===")
if price_col:
    print("逐行打印价格列的值（最后 30 行）：")
    for i in range(max(0, len(df) - 30), len(df)):
        name = df.iloc[i, 0]
        price = df.iloc[i][price_col]
        print(f"  [{i+2}] {name} => {price!r}  ({type(price).__name__})")

# 检查列数
print(f"\n总列数: {len(df.columns)}, 总行数: {len(df)}")