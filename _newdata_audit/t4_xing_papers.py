"""t4: kiem chung so lieu XING 2017 tu NGUON CONG KHAI (arXiv/OpenAlex/DOI), khong tin tri nho.

Thu:
  1. arXiv API: tim 'RecSys Challenge 2017 Offline and Online Evaluation'
  2. OpenAlex: tim theo DOI 10.1145/3109859.3109954 -> lay abstract + PDF url
  3. Neu co PDF/abstract, grep cac con so (impressions, interactions, users, items)
"""
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
out = {}


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


# 1) arXiv
q = 'all:"RecSys Challenge 2017"'
url = "http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q) + "&max_results=20"
try:
    x = get(url)
    titles = re.findall(r"<title>(.*?)</title>", x, re.S)
    ids = re.findall(r"<id>(.*?)</id>", x, re.S)
    out["arxiv"] = {"titles": [t.strip()[:160] for t in titles[1:]], "ids": ids[1:]}
    print("arXiv titles:", out["arxiv"]["titles"][:10])
except Exception as e:
    out["arxiv"] = {"err": str(e)[:150]}
    print("arXiv err", e)

# 2) OpenAlex by DOI
try:
    w = json.loads(get("https://api.openalex.org/works/doi:10.1145/3109859.3109954"))
    out["openalex"] = {
        "title": w.get("title"),
        "year": w.get("publication_year"),
        "cited_by": w.get("cited_by_count"),
        "oa": (w.get("open_access") or {}).get("oa_url"),
        "pdf": w.get("best_oa_location"),
        "abstract": (w.get("abstract_inverted_index") and "HAS_ABSTRACT") or None,
    }
    inv = w.get("abstract_inverted_index") or {}
    if inv:
        pos = {}
        for word, idxs in inv.items():
            for i in idxs:
                pos[i] = word
        abstract = " ".join(pos[i] for i in sorted(pos))
        out["openalex"]["abstract_text"] = abstract
        print("title:", w.get("title"))
        print("abstract:", abstract[:1200])
except Exception as e:
    out["openalex"] = {"err": str(e)[:200]}
    print("openalex err", str(e)[:200])

# 3) Thu tai PDF overview neu co tren mang
for name, u in [
    ("abel_pdf_2017", "http://www.recsyschallenge.com/2017/RecSysChallenge17.pdf"),
    ("ceur", "https://ceur-ws.org/Vol-1892/"),
    ("github2017_readme", "https://raw.githubusercontent.com/recsyschallenge/2017/master/README.md"),
]:
    try:
        r = get(u, timeout=45)
        out[name] = {"n_chars": len(r), "head": r[:600]}
        print("==", name, len(r))
        print(r[:400].replace("\n", " ")[:400])
    except Exception as e:
        out[name] = {"err": type(e).__name__ + ":" + str(e)[:120]}
        print("==", name, "ERR", str(e)[:120])

with open(r"_newdata_audit/t4_verify/t4_xing_papers.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("done")
