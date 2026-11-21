# -*- coding: utf-8 -*-
"""t2: kiem chung moi con so trong bao cao deu truy nguon duoc tu T2_EVIDENCE.json.

So sanh theo GIA TRI so (bo dau phan cach), khong theo chuoi tho.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
DOC = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\docs\KHAO_SAT_NGUONG_KY_NANG.md")
DOC = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\docs\KHAO_SAT_NGUON_KY_NANG_VA_NGANH.md")

ev = json.loads((A / "T2_EVIDENCE.json").read_text(encoding="utf-8"))
blob = json.dumps(ev, ensure_ascii=False)
doc = DOC.read_text(encoding="utf-8")

NUM = re.compile(r"\d[\d.,]*\d|\d")


def values(text):
    out = set()
    for m in NUM.findall(text):
        s = m.strip(".,")
        cands = set()
        # doc kieu VN: 1.234.567,89 ; va kieu EN: 1,234,567.89
        for s2 in {s, s.replace(".", "").replace(",", "."), s.replace(",", "").replace(".", ".")}:
            try:
                cands.add(round(float(s2), 4))
            except ValueError:
                pass
        out |= cands
    return out


doc_vals = values(doc)
ev_vals = values(blob)

untraced = sorted(v for v in doc_vals if v not in ev_vals and v >= 1)
print("so gia tri so trong bao cao:", len(doc_vals))
print("khong truy nguon duoc (>=1):", len(untraced))
print(untraced[:40])
small = sorted(v for v in doc_vals if v not in ev_vals and v < 1)
print("\nso le <1 khong truy nguon duoc:", small[:30])

# khang dinh cam ky
BAD = ["chặn toàn bộ HTTPS", "mạng bị chặn", "ESCO có tiếng Việt", "đã tải asaniczka"]
print("\nkhang dinh cam ky:", [(b, b in doc) for b in BAD])
print("dong:", doc.count("\n") + 1, "| byte:", DOC.stat().st_size)
