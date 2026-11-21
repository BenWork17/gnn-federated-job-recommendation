"""t4: thu tim mirror THAT cua RecSys Challenge 2017 (XING) va kiem trang 2017.

Khong tai du lieu lon; chi probe status + content-length + sniff.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def probe(url, method="GET", nbytes=1500):
    rec = {"url": url, "method": method}
    try:
        req = urllib.request.Request(url, headers=UA, method=method)
        with urllib.request.urlopen(req, timeout=60) as r:
            rec["status"] = r.status
            rec["ct"] = r.headers.get("Content-Type")
            rec["len"] = r.headers.get("Content-Length")
            rec["final"] = r.geturl()
            if method == "GET":
                rec["sniff"] = r.read(nbytes).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        rec["status"] = e.code
        rec["reason"] = str(e.reason)[:120]
        try:
            rec["sniff"] = e.read(400).decode("utf-8", "replace")
        except Exception:
            pass
    except Exception as e:
        rec["status"] = None
        rec["err"] = type(e).__name__ + ": " + str(e)[:160]
    return rec


out = {}

# 1) Trang challenge 2017 + dataset page chinh thuc
for name, url in [
    ("c2017_home", "http://www.recsyschallenge.com/2017/"),
    ("c2017_https", "https://recsyschallenge.com/2017/"),
    ("xing_data", "https://recsys.xing.com/data"),
    ("xing_root", "https://recsys.xing.com/"),
    ("c2016_dataset_md", "https://raw.githubusercontent.com/recsyschallenge/2016/master/TrainingDataset.md"),
    ("c2017_repo_readme", "https://raw.githubusercontent.com/recsyschallenge/2017/master/README.md"),
]:
    out[name] = probe(url)
    print(name, out[name].get("status"), (out[name].get("len") or ""), out[name].get("err", ""))

# 2) Tim mirror tren HuggingFace
hf = {}
for q in ["xing", "recsys-challenge-2017", "recsys2017", "xing2017"]:
    url = f"https://huggingface.co/api/datasets?search={urllib.parse.quote(q)}&limit=50"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            data = json.load(r)
        hf[q] = [d.get("id") for d in data]
    except Exception as e:
        hf[q] = {"err": str(e)[:120]}
    print("HF", q, "->", str(hf[q])[:300])
out["hf_search"] = hf

# 3) RecoHut / repo mirror
for name, url in [
    ("recohut_xing_readme", "https://cdn.jsdelivr.net/gh/RecoHut-Datasets/xing@main/README.md"),
    ("recohut_xing_tree", "https://data.jsdelivr.com/v1/packages/gh/RecoHut-Datasets/xing@main?structure=flat"),
]:
    out[name] = probe(url)
    print(name, out[name].get("status"), (out[name].get("sniff") or "")[:200].replace("\n", " "))

with open(r"_newdata_audit/t4_verify/t4_xing_probe.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("done")
