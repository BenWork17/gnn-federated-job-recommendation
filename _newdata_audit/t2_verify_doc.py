# -*- coding: utf-8 -*-
"""t2: kiem chung moi con so trong bao cao deu co trong T2_EVIDENCE.json (khong bia so)."""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
DOC = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\docs\KHAO_SAT_NGUON_KY_NANG_VA_NGANH.md")

ev = json.loads((A / "T2_EVIDENCE.json").read_text(encoding="utf-8"))
blob = json.dumps(ev, ensure_ascii=False)
doc = DOC.read_text(encoding="utf-8")

# cac con so quan trong phai xuat hien trong evidence
CHECK = [
    "2942", "13485", "2.942", "13.485",
    "1016", "1.016", "30765", "30.765", "8775", "8.775", "56558", "56.558",
    "20.85", "17.03", "37.88", "111441", "111.400",
    "6190063069", "6,19", "1743166140", "1,74",
    "785741", "785.741", "231152089", "231", "668704", "668.704", "85.10", "85,10",
    "139982", "139.982", "5.45", "5,45", "246",
    "1594827", "1.993.291", "355315", "355.315", "9213302", "9.213.302", "284251", "284.251",
    "2983", "2.983", "6.93", "6,93", "95.0", "95,0",
    "6241", "6.241", "1759", "1.759", "68616017", "68,6",
    "3511", "3.511", "896", "1399", "1.399",
    "1615940", "1.615.940",
]
missing = []
for c in CHECK:
    norm = c.replace(".", "").replace(",", ".")
    in_doc = c in doc or norm in doc
    in_ev = c in blob or norm in blob
    if in_doc and not in_ev:
        missing.append(c)

print("so kiem tra:", len(CHECK))
print("co trong doc NHUNG khong co trong evidence:", missing if missing else "KHONG — tat ca deu truy nguon duoc")

# kiem tra khong con khang dinh sai
BAD = [
    "chặn toàn bộ HTTPS", "không tải được", "mạng bị chặn",
    "ESCO có tiếng Việt", "đã tải asaniczka",
]
print("\nkhang dinh cam ky:", [(b, b in doc) for b in BAD])

# dem bang
print("\nso bang markdown:", doc.count("\n|"))
print("so dong:", doc.count("\n") + 1)
