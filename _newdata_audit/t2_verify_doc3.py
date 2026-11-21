# -*- coding: utf-8 -*-
"""t2: kiem chung truy nguon so - chap nhan neu BAT KY cach doc nao khop evidence."""
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

NUM = re.compile(r"\d[\d.,]*\d|\d")


def readings(tok):
    """tra ve tap gia tri co the cua 1 token so"""
    s = tok.strip(".,")
    out = set()
    for cand in {s, s.replace(".", "").replace(",", "."), s.replace(",", ""), s.replace(",", ".")}:
        try:
            out.add(round(float(cand), 4))
        except ValueError:
            pass
    return out


ev_vals = set()
for t in NUM.findall(blob):
    ev_vals |= readings(t)

untraced = []
checked = 0
for t in NUM.findall(doc):
    rs = readings(t)
    checked += 1
    if not (rs & ev_vals):
        untraced.append(t)

print(f"token so trong bao cao: {checked}")
print(f"KHONG truy nguon duoc: {len(untraced)}")
print("danh sach:", untraced)

BAD = ["chặn toàn bộ HTTPS", "mạng bị chặn", "ESCO có tiếng Việt", "đã tải toàn bộ asaniczka"]
print("\nkhang dinh cam ky:", [(b, b in doc) for b in BAD])
print("dong:", doc.count("\n") + 1, "| byte:", DOC.stat().st_size)
