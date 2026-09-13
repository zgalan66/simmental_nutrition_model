import pandas as pd

df = pd.read_excel('data/原料含量.xlsx', header=1)
print(f"总列数: {len(df.columns)}\n")
for i, c in enumerate(df.columns):
    print(f"[{i:2d}] {repr(c)}")