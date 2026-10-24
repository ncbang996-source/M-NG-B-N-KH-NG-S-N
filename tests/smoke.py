"""Kiểm tra nhanh: đọc Excel mẫu, dựng 2 tờ, xuất PDF + DXF, so khối lượng với bản vẽ mẫu."""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from mongban import export, model  # noqa: E402

p, warn = model.read_excel(os.path.join(ROOT, "samples", "MONG_COT_D411-25.xlsx"))
res = export.build(p, os.path.join(ROOT, "assets", "frames", "KT-A3.dxf"))
total = sum(c[2] for c in res.geo.klc)
assert abs(total - 2145.22) < 0.05, total
assert abs(model.vol_mong(p) - 25.36) < 0.01
assert abs(model.vol_cat(p) - 21.70) < 0.01 and abs(model.area_vai(p) - 85.79) < 0.01
d = tempfile.mkdtemp()
export.save_dxf(res, os.path.join(d, "t.dxf"))
data = export.pdf_bytes(res)
assert data[:4] == b"%PDF" and len(res.origins) == 2
print("OK - thep", round(total, 2), "kg; PDF", len(data), "bytes")

from mongban import kl_excel  # noqa: E402
kl_excel.export(p, res.geo, os.path.join(d, "kl.xlsx"))
print("OK - Excel khoi luong")
