"""t4: xac minh cong tai lieu XING con hoat dong hay khong (do redirect chain).

Ghi ro: recsys.xing.com -> ? (redirect) ; 2016 site -> link dataset?
Khong in unicode ra console (tranh loi cp1252) — luu file JSON utf-8.
"""
import json
import re
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url, follow=True):
    rec = {"url": url}
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    try:
        req = urllib.request.Request(url, headers=UA)
        with opener.open(req, timeout=60) as r:
            rec["status"] = r.status
            rec["final"] = r.geturl()
            rec["history"] = [(h.status, h.headers.get("Location")) for h in getattr(r, "history", [])]
            body = r.read(200000).decode("utf-8", "replace")
            rec["n_chars"] = len(body)
            rec["body"] = body
    except urllib.error.HTTPError as e:
        rec["status"] = e.code
        rec["location"] = e.headers.get("Location")
        rec["body"] = ""
        try:
            rec["body"] = e.read(20000).decode("utf-8", "replace")
        except Exception:
            pass
    except Exception as e:
        rec["status"] = None
        rec["err"] = type(e).__name__ + ": " + str(e)[:200]
        rec["body"] = ""
    return rec


TARGETS = [
    ("xing_portal_follow", "https://recsys.xing.com/", True),
    ("xing_portal_noredirect", "https://recsys.xing.com/", False),
    ("c2016_home", "http://2016.recsyschallenge.com/", True),
]
out = {}
for name, url, follow in TARGETS:
    r = fetch(url, follow)
    body = r.pop("body", "")
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", "\n", txt)
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    r["n_lines"] = len(lines)
    r["text_head"] = lines[:30]
    r["links"] = sorted(set(re.findall(r'href="([^"]+)"', body)))[:80]
    out[name] = r
    print("=====", name, r.get("status"), "->", r.get("final") or r.get("location") or r.get("err"))
    print("history:", r.get("history"))
    safe = [l.encode("ascii", "replace").decode("ascii") for l in lines[:18]]
    print("\n".join(safe)[:1200])
    print("links:", [l.encode("ascii", "replace").decode("ascii") for l in r["links"][:25]])

with open(r"_newdata_audit/t4_verify/t4_xing_portal.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("done")
