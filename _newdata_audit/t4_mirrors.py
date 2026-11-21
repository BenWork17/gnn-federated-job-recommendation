"""t4: tim mirror cong khai cho cac ung vien chua tai duoc (asaniczka, arshkon, XING 2017).

In ra JSON: ung vien -> danh sach URL da thu + status + content-length (khong tai noi dung lon).
"""
import json
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def probe(url, method="GET", nbytes=800):
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
    except Exception as e:
        rec["status"] = None
        rec["err"] = type(e).__name__ + ": " + str(e)[:160]
    return rec


out = {}

# 1) Tim mirror tren HuggingFace
hf_queries = [
    "linkedin-jobs-and-skills",
    "asaniczka",
    "linkedin_job_postings",
    "1-3m-linkedin",
    "linkedin-job-postings",
]
out["hf_search"] = {}
for q in hf_queries:
    url = f"https://huggingface.co/api/datasets?search={urllib.parse.quote(q)}&limit=50"
    r = probe(url)
    try:
        data = json.loads(r.get("sniff", "") + "")  # sniff cut -> refetch small
        out["hf_search"][q] = [d.get("id") for d in data]
    except Exception:
        # refetch full small json
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as rr:
                data = json.load(rr)
            out["hf_search"][q] = [{"id": d.get("id"), "downloads": d.get("downloads")} for d in data]
        except Exception as e:
            out["hf_search"][q] = {"err": str(e)[:120]}
    print("HF search", q, "->", str(out["hf_search"][q])[:400])

# 2) Kaggle endpoints khong auth
out["kaggle"] = {}
for name, url in [
    ("asaniczka_list", "https://www.kaggle.com/api/v1/datasets/list?search=1-3m-linkedin-jobs-and-skills-2024"),
    ("asaniczka_view", "https://www.kaggle.com/api/v1/datasets/view/asaniczka/1-3m-linkedin-jobs-and-skills-2024"),
    ("asaniczka_files", "https://www.kaggle.com/api/v1/datasets/list/asaniczka/1-3m-linkedin-jobs-and-skills-2024"),
    ("asaniczka_dl", "https://www.kaggle.com/api/v1/datasets/download/asaniczka/1-3m-linkedin-jobs-and-skills-2024"),
    ("arshkon_view", "https://www.kaggle.com/api/v1/datasets/view/arshkon/linkedin-job-postings"),
    ("arshkon_dl", "https://www.kaggle.com/api/v1/datasets/download/arshkon/linkedin-job-postings"),
]:
    out["kaggle"][name] = probe(url)
    print("kaggle", name, out["kaggle"][name].get("status"), out["kaggle"][name].get("len"),
          (out["kaggle"][name].get("sniff") or "")[:150].replace("\n", " "))

with open(r"_newdata_audit/t4_mirrors.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("done")
