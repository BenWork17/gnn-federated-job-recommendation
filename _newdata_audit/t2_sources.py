"""t2: khao sat metadata cac nguon (B) job corpus va (C) profile qua API JSON."""
import json
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit")
UA = {"User-Agent": "Mozilla/5.0 (compatible; research-audit/1.0)"}


def fetch(url, timeout=60, raw=False):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            if raw:
                return {"ok": True, "status": r.status, "len": len(body), "ct": r.headers.get("Content-Type"), "body": body}
            return {"ok": True, "status": r.status, "json": json.loads(body.decode("utf-8")), "len": len(body)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "err": e.read()[:400].decode("utf-8", "replace")}
    except Exception as e:
        return {"ok": False, "err": f"{type(e).__name__}: {e}"}


report = {}

# ---------- Kaggle: file list for the two datasets ----------
K = {
    "asaniczka_linkedin": "asaniczka/1-3m-linkedin-jobs-and-skills-2024",
    "ravindra_jd": "ravindrasinghrana/job-description-dataset",
}
for key, ref in K.items():
    a = fetch(f"https://www.kaggle.com/api/v1/datasets/view/{ref}")
    b = fetch(f"https://www.kaggle.com/api/v1/datasets/data-list/{ref}")
    d = {}
    if a.get("ok"):
        j = a["json"]
        d["title"] = j.get("titleNullable")
        d["license"] = j.get("licenseNameNullable")
        d["totalBytes"] = j.get("totalBytesNullable")
        d["lastUpdated"] = j.get("lastUpdated")
        d["subtitle"] = j.get("subtitleNullable")
        d["voteCount"] = j.get("voteCount")
        d["downloadCount"] = j.get("downloadCount")
        d["usabilityRating"] = j.get("usabilityRating")
    else:
        d["view_err"] = a.get("status", a.get("err"))
    if b.get("ok"):
        j = b["json"]
        files = j.get("datasetFiles", j.get("files", []))
        d["n_files"] = len(files)
        d["files"] = [{"name": f.get("name"), "bytes": f.get("totalBytes") or f.get("totalBytesNullable"),
                       "cols": f.get("columns")} for f in files]
        d["raw_keys"] = list(j.keys())[:20]
    else:
        d["datalist_err"] = b.get("status", b.get("err"))
    report[key] = d

# ---------- HuggingFace datasets ----------
HF = {
    "jobhop": "aida-ugent/JobHop",
    "resume_fit": "cnamuangtoun/resume-job-description-fit",
}
for key, ref in HF.items():
    a = fetch(f"https://huggingface.co/api/datasets/{ref}?full=true")
    d = {}
    if a.get("ok"):
        j = a["json"]
        d["id"] = j.get("id")
        d["license"] = [t for t in (j.get("tags") or []) if t.startswith("license")]
        d["cardData"] = j.get("cardData")
        d["downloads"] = j.get("downloads")
        d["lastModified"] = j.get("lastModified")
        sibs = j.get("siblings") or []
        d["n_siblings"] = len(sibs)
        d["siblings_sample"] = [s.get("rfilename") for s in sibs[:25]]
    else:
        d["err"] = a.get("status", a.get("err"))
    b = fetch(f"https://datasets-server.huggingface.co/info?dataset={ref}")
    d["info_ok"] = b.get("ok")
    if b.get("ok"):
        d["info"] = b["json"]
    else:
        d["info_err"] = b.get("status", b.get("err"))
    report[key] = d

OUT.joinpath("t2_sources_probe.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False)[:6000])
