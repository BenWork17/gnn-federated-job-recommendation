"""t4: tai overview.pdf (CEUR Vol-1892, RecSys Challenge 2017) va DOC THAT Table 1.

Neu doc duoc bảng số liệu -> nang XING 2017 tu muc B len muc B+/A- va co so lieu goc.
In ra moi dong chua so lon / tu khoa.
"""
import json
import re
import ssl
import urllib.request

import fitz  # PyMuPDF

UA = {"User-Agent": "Mozilla/5.0"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
OUT = r"_newdata_audit/t4_verify"

url = "https://ceur-ws.org/Vol-1892/overview.pdf"
req = urllib.request.Request(url, headers=UA)
with urllib.request.urlopen(req, timeout=120, context=CTX) as r, open(OUT + r"\xing2017_overview.pdf", "wb") as f:
    f.write(r.read())
print("pdf bytes:", __import__("os").path.getsize(OUT + r"\xing2017_overview.pdf"))

doc = fitz.open(OUT + r"\xing2017_overview.pdf")
print("pages:", doc.page_count)
full = []
for i, page in enumerate(doc):
    t = page.get_text()
    full.append(t)
    print(f"--- page {i} chars {len(t)} ---")
text = "\n".join(full)
open(OUT + r"\xing2017_overview.txt", "w", encoding="utf-8").write(text)

# tim cac dong co so lieu
lines = [l.strip() for l in text.split("\n") if l.strip()]
num = re.compile(r"\d[\d.,]{2,}")
hits = [l for l in lines if num.search(l)]
print("=== lines with numbers (first 90) ===")
for l in hits[:90]:
    print("|", l.encode("ascii", "replace").decode("ascii")[:200])

kw = re.compile(r"impression|interaction|dataset|users|items|million|recruiter|Table", re.I)
print("=== lines with keywords (first 80) ===")
for l in lines:
    if kw.search(l) and len(l) < 400:
        print("*", l.encode("ascii", "replace").decode("ascii")[:220])
