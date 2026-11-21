"""t2: doc central directory cua ZIP Kaggle bang HTTP Range (KHONG tai 6 GB).
Thu lay danh sach file + kich thuoc tu central directory."""
import io
import json
import struct
import urllib.error
import urllib.request
import zipfile

UA = {"User-Agent": "Mozilla/5.0"}
URL = "https://www.kaggle.com/api/v1/datasets/download/asaniczka/1-3m-linkedin-jobs-and-skills-2024"


def get_range(url, start, end):
    h = dict(UA)
    h["Range"] = f"bytes={start}-{end}"
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status, dict(r.headers), r.read()


try:
    st, hd, body = get_range(URL, 0, 1023)
    print("range status:", st)
    print("headers:")
    for k in ("Content-Length", "Content-Range", "Accept-Ranges", "Content-Type", "Content-Disposition"):
        print("  ", k, "=", hd.get(k))
    print("first 200:", body[:200])
except urllib.error.HTTPError as e:
    print("HTTPError", e.code)
    print(e.headers)
    print(e.read()[:500])
except Exception as e:
    print("ERR", type(e).__name__, e)
