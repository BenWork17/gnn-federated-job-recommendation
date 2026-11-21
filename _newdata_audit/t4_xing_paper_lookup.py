"""t4: thu lay PAER PDF/Table 1 cua RecSys Challenge 2017 de doi chieu so lieu XING.

Cac duong: arXiv search ten tac gia, semantic scholar API, CEUR (bo qua SSL), ACM DL (khong auth).
Neu khong lay duoc -> ket luan: so lieu XING chi o muc B (tai lieu), KHONG do duoc.
"""
import json
import re
import ssl
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
out = {}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


QUERIES = [
    'all:"RecSys Challenge 2017"',
    'ti:"Offline and Online Evaluation" AND all:XING',
    'all:"job recommendations" AND all:XING AND all:challenge',
]
out["arxiv"] = {}
for q in QUERIES:
    url = ("http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q)
           + "&max_results=10")
    try:
        x = get(url)
        entries = re.findall(r"<entry>(.*?)</entry>", x, re.S)
        recs = []
        for e in entries:
            t = re.search(r"<title>(.*?)</title>", e, re.S)
            i = re.search(r"<id>(.*?)</id>", e, re.S)
            recs.append({"title": (t.group(1).strip()[:160] if t else None),
                         "id": (i.group(1).strip() if i else None)})
        out["arxiv"][q] = recs
        print("Q:", q, "->", len(recs))
        for r in recs:
            print("   ", r["id"], r["title"][:110])
    except Exception as e:
        out["arxiv"][q] = {"err": str(e)[:120]}
        print("Q:", q, "ERR", str(e)[:120])

# Semantic Scholar
for name, url in [
    ("s2_doi", "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3109859.3109954?fields=title,year,openAccessPdf,externalIds,abstract"),
]:
    try:
        d = json.loads(get(url))
        out[name] = d
        print("==", name, d.get("title"), d.get("openAccessPdf"))
    except Exception as e:
        out[name] = {"err": type(e).__name__ + ":" + str(e)[:150]}
        print("==", name, "ERR", str(e)[:150])

# CEUR (bo qua verify)
for name, url in [
    ("ceur_1892", "https://ceur-ws.org/Vol-1892/"),
]:
    try:
        r = get(url)
        out[name] = {"n_chars": len(r), "head": r[:1500]}
        print("==", name, len(r))
        for m in re.findall(r'href="([^"]+\.pdf)"', r)[:20]:
            print("   pdf:", m)
    except Exception as e:
        out[name] = {"err": type(e).__name__ + ":" + str(e)[:150]}
        print("==", name, "ERR", str(e)[:150])

with open(r"_newdata_audit/t4_verify/t4_xing_paper_lookup.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("done")
