"""t2: tim cot that cua asaniczka dataset qua DuckDuckGo HTML + GitHub search."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"}


def fetch(u, timeout=60):
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


print("== DuckDuckGo HTML ==")
q = "asaniczka 1.3M linkedin jobs and skills job_skills column"
html = fetch("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q))
print("len", len(html))
links = re.findall(r'href="(//duckduckgo\.com/l/\?uddg=[^"]+)"', html)
print("n result links:", len(links))
for l in links[:10]:
    m = re.search(r"uddg=([^&]+)", l)
    if m:
        print("  ", urllib.parse.unquote(m.group(1)))

print()
print("== GitHub code search (unauth, may 401) ==")
g = fetch("https://api.github.com/search/code?q=job_skills+got_summary+in:file")
print(g[:300])

print()
print("== GitHub repo search ==")
g2 = fetch("https://api.github.com/search/repositories?q=linkedin+jobs+skills+asaniczka")
try:
    j = json.loads(g2)
    for it in (j.get("items") or [])[:10]:
        print("  ", it["full_name"], "|", (it.get("description") or "")[:100])
except Exception:
    print(g2[:300])
