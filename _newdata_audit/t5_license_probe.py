"""t5: KIEM LICENSE THAT cua cac bo TUONG TAC thay the, doc tu nguon goc.

Uu tien (theo chi dao cua captain):
  1. OLX jobs-interactions  -> license that la gi?
  2. Zhaopin/Tianchi 31623  -> CC-BY-SA-NC? hoc thuat duoc?
  3. Djinni / lang-uk       -> MIT? co tuong tac khong?
  4. Tim them bo tuong tac license mo (HF search + Kaggle search)

Nguyen tac: chi ghi "SACH" khi doc duoc VAN BAN license/is_licensed/README cua chinh nguon.
Khong suy tu tri nho.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"_newdata_audit/t5_verify")
OUT.mkdir(parents=True, exist_ok=True)
res = {}


def get(url, timeout=60, nbytes=300000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(nbytes).decode("utf-8", "replace")


def try_get(url, **kw):
    try:
        st, body = get(url, **kw)
        return {"status": st, "body": body}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": "", "err": f"HTTP {e.code}"}
    except Exception as e:
        return {"status": None, "body": "", "err": type(e).__name__ + ": " + str(e)[:150]}


def strip_html(h):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "\n", t)
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


# ---------- 1. OLX ----------
olx = {}
for name, url in [
    ("kaggle_api_view", "https://www.kaggle.com/api/v1/datasets/view/olxdatascience/olx-jobs-interactions"),
    ("kaggle_page", "https://www.kaggle.com/datasets/olxdatascience/olx-jobs-interactions"),
    ("kaggle_files", "https://www.kaggle.com/api/v1/datasets/list/olxdatascience/olx-jobs-interactions"),
]:
    r = try_get(url)
    olx[name] = {"status": r["status"], "err": r.get("err")}
    if r["body"]:
        b = r["body"]
        olx[name]["n_chars"] = len(b)
        # tim license trong JSON/page
        for kw in ["license", "licence", "CC0", "CC-BY", "CC BY", "ODC", "commercial",
                   "research", "academic", "Other"]:
            if kw.lower() in b.lower():
                olx[name].setdefault("kw_hits", []).append(kw)
        m = re.search(r'"(?:licenseName|license|licenses?)"\s*:\s*"?([^",}]{1,80})', b, re.I)
        if m:
            olx[name]["license_field"] = m.group(1).strip()
        txt = strip_html(b)
        hits = [l for l in txt.split("\n") if re.search(r"licen|commercial|research|academic|CC0|ODbL|attribution", l, re.I)]
        olx[name]["license_lines"] = hits[:12]
        print("== OLX", name, r["status"])
        for h_ in hits[:8]:
            print("   |", h_[:220].encode("ascii", "replace").decode("ascii"))
res["olx"] = olx

# ---------- 2. Zhaopin / Tianchi ----------
zh = {}
for name, url in [
    ("dataset_page", "https://tianchi.aliyun.com/dataset/31623"),
    ("api_data", "https://tianchi.aliyun.com/api/v1/dataset/31623"),
    ("api_detail", "https://tianchi.aliyun.com/api/dataset/getDatasetDetail?datasetVersion=31623"),
]:
    r = try_get(url)
    zh[name] = {"status": r["status"], "err": r.get("err"), "n_chars": len(r["body"])}
    if r["body"]:
        b = r["body"]
        for kw in ["CC-BY", "CC BY", "BY-SA", "NC", "NonCommercial", "commercial",
                   "license", "许可", "协议", "非商业", "署名"]:
            if kw in b:
                zh[name].setdefault("kw_hits", []).append(kw)
        txt = strip_html(b)
        txt = "".join(ch if ord(ch) < 128 else ch for ch in txt)
        hits = [l for l in txt.split("\n") if re.search(r"CC|licen|许可|协议|商业|署名|BY-SA|NonCommercial", l, re.I)]
        zh[name]["hits"] = hits[:15]
        zh[name]["is_spa_shell"] = len(re.findall(r"<div id=\"?root\"?|<script", b, re.I)) > 3 and len(txt) < 3000
        print("== Zhaopin", name, r["status"], "chars", len(b), "spa?", zh[name]["is_spa_shell"])
        for h_ in hits[:6]:
            print("   |", h_[:200].encode("ascii", "replace").decode("ascii"))
res["zhaopin"] = zh

# ---------- 3. Djinni / lang-uk ----------
dj = {}
for repo in ["lang-uk/recruitment-dataset-job-descriptions-english",
             "lang-uk/recruitment-dataset-candidate-profiles-english"]:
    info = try_get(f"https://huggingface.co/api/datasets/{repo}")
    d = {"status": info["status"]}
    if info["body"]:
        j = json.loads(info["body"])
        card = j.get("cardData") or {}
        d["license"] = card.get("license")
        d["license_name"] = card.get("license_name")
        d["license_link"] = card.get("license_link")
        d["gated"] = j.get("gated")
        d["tags"] = [t for t in (j.get("tags") or []) if "licen" in t or "dataset" in t]
        d["files"] = [s["rfilename"] for s in (j.get("siblings") or [])]
    rd = try_get(f"https://huggingface.co/datasets/{repo}/raw/main/README.md")
    d["readme_status"] = rd["status"]
    if rd["body"]:
        (OUT / (repo.split("/")[-1] + "_README.md")).write_text(rd["body"], encoding="utf-8")
        d["readme_first800"] = rd["body"][:800]
        d["mentions_interaction"] = bool(re.search(r"click|apply|interaction|view", rd["body"], re.I))
    dj[repo] = d
    print("== Djinni", repo, "license:", d.get("license"), "gated:", d.get("gated"))
    for f in d.get("files", []):
        print("   file:", f)
res["djinni"] = dj

# ---------- 4. Tim them bo tuong tac license mo ----------
found = {}
QUERIES_HF = ["job interaction", "recruitment interaction", "job click", "jobs interactions",
              "job application interaction", "job recommendation interaction",
              "advertisement clicks jobs", "job clicks"]
for q in QUERIES_HF:
    url = f"https://huggingface.co/api/datasets?search={urllib.parse.quote(q)}&limit=40"
    r = try_get(url)
    ids = []
    if r["body"]:
        try:
            for d in json.loads(r["body"]):
                ids.append({"id": d.get("id"), "downloads": d.get("downloads")})
        except Exception:
            pass
    found[q] = ids
    print("== HF", q, "->", len(ids))
    for i in ids[:8]:
        print("    ", i["id"], i["downloads"])
res["hf_search"] = found

with open(OUT / "t5_license_probe.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print("\nwrote t5_license_probe.json")
