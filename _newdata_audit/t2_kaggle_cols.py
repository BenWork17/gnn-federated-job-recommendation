"""t2: lay danh sach cot dataset Kaggle qua cac duong khac (jina proxy, HF mirror)."""
import json
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}


def fetch(u, timeout=90, want_json=False):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read()
        if want_json:
            return {"ok": True, "json": json.loads(b.decode("utf-8"))}
        return {"ok": True, "text": b.decode("utf-8", "replace"), "len": len(b)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code}
    except Exception as e:
        return {"ok": False, "err": f"{type(e).__name__}: {e}"}


print("=== jina proxy on kaggle dataset page ===")
r = fetch("https://r.jina.ai/https://www.kaggle.com/datasets/asaniczka/1-3m-linkedin-jobs-and-skills-2024")
if r["ok"]:
    t = r["text"]
    print("len", r["len"])
    idx = t.find("job_skills")
    print("has job_skills:", idx >= 0)
    if idx > 0:
        print(t[max(0, idx - 1500):idx + 1500])
    else:
        print(t[:3000])
else:
    print("jina failed", r)

print()
print("=== HF listing search linkedin (limit 100) ===")
r = fetch("https://huggingface.co/api/datasets?search=linkedin&limit=100", want_json=True)
if r["ok"]:
    for d in r["json"]:
        print("  ", d.get("id"), d.get("downloads"))
else:
    print("fail", r)
