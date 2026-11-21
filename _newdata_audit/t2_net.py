"""t2: kiem tra kha nang tai du lieu that (mang + dung luong) tren may dich."""
import ssl
import sys
import urllib.request

print(sys.version)
print(ssl.OPENSSL_VERSION)

URLS = [
    "https://www.onetcenter.org/dl_files/database/db_29_3_text.zip",
    "https://esco.ec.europa.eu/sites/default/files/esco_dataset/1.2.0/ESCO%20dataset%20-%20v1.2.0%20-%20classification%20-%20en%2Cfr%2Cde%2Cit%2Ces.csv.zip",
    "https://ec.europa.eu/esco/api/resource/taxonomy?uri=http://data.europa.eu/esco/concept-scheme/skills&language=en",
]

for u in URLS:
    try:
        req = urllib.request.Request(u, method="GET", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=40) as r:
            cl = r.headers.get("Content-Length")
            chunk = r.read(2048)
            print("OK", r.status, "len=", cl, "type=", r.headers.get("Content-Type"), "|", u)
            print("   first bytes:", chunk[:120])
    except Exception as e:
        print("ERR", type(e).__name__, e, "|", u)
