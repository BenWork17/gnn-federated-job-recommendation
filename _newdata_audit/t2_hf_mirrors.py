"""t2: kiem tra HF mirrors cua LinkedIn jobs dataset - lay danh sach cot THAT."""
import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def get(u, timeout=90):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


CANDS = [
    "datastax/linkedin_job_listings",
    "ryang2/linkedin-job-scrape",
    "xanderios/linkedin-job-postings",
    "lof223/linkedinjobs",
    "HaiweiHe/linkedin-jobs",
    "MichaelYitzchak/LinkedInJobPostings",
]
for cid in CANDS:
    print("=" * 70)
    print(cid)
    try:
        info = get(f"https://datasets-server.huggingface.co/info?dataset={cid}")
        di = info.get("dataset_info", {})
        for cfg, c in di.items():
            print("  config:", cfg)
            feats = c.get("features") or {}
            print("  n_features:", len(feats))
            print("  columns:", list(feats.keys()))
            for s, sv in (c.get("splits") or {}).items():
                print(f"    split {s}: rows={sv.get('num_examples')} bytes={sv.get('num_bytes')}")
    except Exception as e:
        print("  info ERR", type(e).__name__, e)
    try:
        d = get(f"https://huggingface.co/api/datasets/{cid}?full=true")
        print("  license tags:", [t for t in (d.get("tags") or []) if t.startswith("license")])
        print("  cardData:", json.dumps(d.get("cardData"))[:300])
        print("  files:", [s.get("rfilename") for s in (d.get("siblings") or [])][:15])
    except Exception as e:
        print("  api ERR", e)
