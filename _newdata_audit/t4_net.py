"""t4: probe network reachability of the candidate sources (HTTP status only)."""
import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
URLS = [
    ("esco_api_search", "https://ec.europa.eu/esco/api/search?type=skill&limit=20&language=en"),
    ("esco_api_resource", "https://ec.europa.eu/esco/api/resource/occupation?uri=http://data.europa.eu/esco/occupation/001e2b46-1b8b-4a35-9a1e-1ba2bfa8a6cf&language=en"),
    ("onet_zip", "https://www.onetcenter.org/dl_files/database/db_29_3_text.zip"),
    ("hf_datasets_server_info_lukebarousse",
     "https://datasets-server.huggingface.co/info?dataset=lukebarousse/data_jobs"),
    ("hf_resolve_lukebarousse",
     "https://huggingface.co/datasets/lukebarousse/data_jobs/resolve/main/data_jobs.csv"),
    ("xing2017_root", "https://recsys.xing.com/"),
    ("xing2017_data", "https://recsys.xing.com/data"),
    ("xing2016_root", "http://2016.recsyschallenge.com/"),
    ("tianchi31623", "https://tianchi.aliyun.com/dataset/31623"),
    ("hf_search_arshkon", "https://huggingface.co/api/datasets?search=linkedin-job-postings&limit=20"),
]

out = {}
for name, url in URLS:
    rec = {"url": url}
    try:
        req = urllib.request.Request(url, headers=UA, method="GET")
        with urllib.request.urlopen(req, timeout=45) as r:
            rec["status"] = r.status
            rec["final_url"] = r.geturl()
            rec["content_type"] = r.headers.get("Content-Type")
            rec["content_length"] = r.headers.get("Content-Length")
            body = r.read(4000)
            rec["bytes_read"] = len(body)
            rec["sniff"] = body[:300].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        rec["status"] = e.code
        rec["error"] = "HTTPError"
        try:
            rec["sniff"] = e.read(600).decode("utf-8", "replace")
        except Exception:
            pass
    except Exception as e:
        rec["status"] = None
        rec["error"] = type(e).__name__ + ": " + str(e)[:200]
    out[name] = rec
    print(name, rec.get("status"), rec.get("error", ""), (rec.get("content_type") or "")[:40],
          (rec.get("content_length") or ""))

# HEAD probes for XING download endpoints mentioned in the official docs
HEADS = [
    ("xing2016_interactions", "https://recsys.xing.com/data/interactions.csv"),
    ("xing2017_datasets_zip", "https://recsys.xing.com/datasets/recsys2017.zip"),
]
for name, url in HEADS:
    rec = {"url": url}
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            rec["status"] = r.status
            rec["content_length"] = r.headers.get("Content-Length")
    except urllib.error.HTTPError as e:
        rec["status"] = e.code
    except Exception as e:
        rec["status"] = None
        rec["error"] = type(e).__name__ + ": " + str(e)[:160]
    out[name] = rec
    print(name, rec.get("status"), rec.get("error", ""))

with open(r"_newdata_audit/t4_net.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("wrote _newdata_audit/t4_net.json")
