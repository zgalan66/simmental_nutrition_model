from openpyxl import load_workbook

wb = load_workbook('data/原料含量.xlsx', data_only=True)
ws = wb.active

print("=== 表头行（第 2 行）所有列 ===")
price_col = None
for c in range(1, ws.max_column + 1):
    header = ws.cell(2, c).value
    if header is None:
        continue
    marker = ""
    if "单价" in str(header) or "价格" in str(header) or "元" in str(header):
        price_col = c
        marker = "  ★★★ 找到价格列"
    print(f"  第 {c} 列 ({ws.cell(2, c).coordinate}): {header!r}{marker}")

print()
if price_col:
    print(f"=== 价格列在第 {price_col} 列，逐行检查前 10 行 ===")
    for r in range(3, 13):
        name = ws.cell(r, 1).value
        price = ws.cell(r, price_col).value
        print(f"  行{r}: {name} => {price!r}")
else:
    print("没找到含'单价'/'价格'/'元'的列，请检查 Excel 表头")

print()
print("=== 第 3 行所有有值的列（看价格到底在哪）===")
for c in range(1, ws.max_column + 1):
    v = ws.cell(3, c).value
    if v is not None and c > 45:
        print(f"  第 {c} 列 ({ws.cell(2, c).coordinate}): 表头={ws.cell(2, c).value!r}, 值={v!r}")