"""t4: kiem chung GIAY PHEP bang van ban that (khong tin tri nho).

Nguon:
  - HF card lukebarousse/data_jobs  -> cardData.license + README text
  - HF card lang-uk 2 repo          -> cardData.license
  - Kaggle CareerBuilder rules .docx (uu tien file local neu co, khong thi tai)
  - ESCO legal notice / decision 2011/833/EU
  - O*NET license page
In ra: license string, URL, va cac cau trich dan chinh.
"""
import json
import re
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"_newdata_audit/t4_verify")
OUT.mkdir(parents=True, exist_ok=True)


def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_text(url, timeout=90):
    return get(url, timeout).decode("utf-8", "replace")


res = {}

# ---- 1. HF cards ----
for repo in ["lukebarousse/data_jobs",
             "lang-uk/recruitment-dataset-job-descriptions-english",
             "lang-uk/recruitment-dataset-candidate-profiles-english"]:
    info = json.loads(get_text(f"https://huggingface.co/api/datasets/{repo}"))
    card = info.get("cardData") or {}
    readme = ""
    try:
        readme = get_text(f"https://huggingface.co/datasets/{repo}/raw/main/README.md")
    except Exception as e:
        readme = "ERR " + str(e)[:100]
    (OUT / (repo.replace("/", "__") + "_README.md")).write_text(readme, encoding="utf-8")
    res[repo] = {
        "license": card.get("license"),
        "license_name": card.get("license_name"),
        "license_link": card.get("license_link"),
        "tags": info.get("tags"),
        "gated": info.get("gated"),
        "private": info.get("private"),
        "lastModified": info.get("lastModified"),
        "readme_first_1200": readme[:1200],
    }
    print("==", repo, "license:", card.get("license"), "gated:", info.get("gated"))

# ---- 2. CareerBuilder rules docx ----
CB_URLS = [
    "https://storage.googleapis.com/kaggle-media/competitions/kaggle/3046/media/CB%20Kaggle%20Competition%20Official%20Rules%207%2012%202012.docx",
    "https://storage.googleapis.com/kaggle-media/competitions/kaggle/3046/media/CB Kaggle Competition Official Rules 7 12 2012.docx",
]
cb = {"tried": []}
docx_bytes = None
for u in CB_URLS:
    try:
        b = get(u, timeout=120)
        cb["tried"].append({"url": u, "bytes": len(b), "ok": True})
        docx_bytes = b
        break
    except urllib.error.HTTPError as e:
        cb["tried"].append({"url": u, "status": e.code})
    except Exception as e:
        cb["tried"].append({"url": u, "err": type(e).__name__ + ":" + str(e)[:120]})
print("CB rules tries:", cb["tried"])

if docx_bytes:
    p = OUT / "cb_rules.docx"
    p.write_bytes(docx_bytes)
    with zipfile.ZipFile(p) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    txt = re.sub(r"<w:p[ >]", "\n<w:p ", xml)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = re.sub(r"\n{2,}", "\n", txt)
    (OUT / "cb_rules.txt").write_text(txt, encoding="utf-8")
    cb["n_chars"] = len(txt)
    kw = re.compile(r"(erase|destroy|cease|competition ends|Data\b|licen|academic|commercial)", re.I)
    sents = [s.strip() for s in re.split(r"(?<=[.;])\s+", txt) if kw.search(s)]
    cb["key_sentences"] = sents[:25]
    print("CB rules chars:", len(txt), "key sentences:", len(sents))
    for s in cb["key_sentences"][:12]:
        print("  *", s[:300].encode("ascii", "replace").decode("ascii"))
res["careerbuilder_rules"] = cb

# ---- 3. ESCO legal notice ----
try:
    t = get_text("https://esco.ec.europa.eu/en/about-esco/legal-notice", timeout=60)
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S | re.I)
    body = re.sub(r"<[^>]+>", "\n", txt)
    body = "\n".join(l.strip() for l in body.split("\n") if l.strip())
    (OUT / "esco_legal_notice.txt").write_text(body, encoding="utf-8")
    kw = re.compile(r"(2011/833|reuse|re-use|Decision|free of charge|acknowledge|commercial)", re.I)
    sents = [s for s in body.split("\n") if kw.search(s)]
    res["esco_legal"] = {"n_lines": len(body.split("\n")), "key": sents[:20]}
    print("ESCO legal lines:", len(body.split("\n")))
    for s in sents[:10]:
        print("  #", s[:300].encode("ascii", "replace").decode("ascii"))
except Exception as e:
    res["esco_legal"] = {"err": type(e).__name__ + ":" + str(e)[:120]}
    print("ESCO legal ERR", str(e)[:150])

with open(OUT / "t4_licenses.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print("done")
