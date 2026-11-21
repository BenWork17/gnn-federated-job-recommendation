# -*- coding: utf-8 -*-
"""t2: tai mot phan parquet cua lof223/job_description de do cot 'skills' that."""
import io
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pandas as pd

UA = {"User-Agent": "Mozilla/5.0"}


def head_bytes(u, n, timeout=120):
    req = urllib.request.Request(u, headers=dict(UA, Range=f"bytes=0-{n-1}"))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("Content-Range"), r.read()


# tim ten file parquet
import urllib.parse
req = urllib.request.Request("https://huggingface.co/api/datasets/lof223/job_description/tree/main?recursive=true",
                             headers=UA)
with urllib.request.urlopen(req, timeout=60) as r:
    tree = json.loads(r.read().decode())
for it in tree:
    print(it.get("type"), it.get("path"), it.get("size"))
