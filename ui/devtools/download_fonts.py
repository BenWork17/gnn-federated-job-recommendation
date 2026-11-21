import urllib.request, re, os
ua = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0 Safari/537.36"}
url = "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
req = urllib.request.Request(url, headers=ua)
css = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
outdir = r"E:\2026\DUT\DSS\SauGK\CuoiKi\ui\vendor\fonts"
os.makedirs(outdir, exist_ok=True)
# split blocks by font-family group
blocks = re.findall(r"/\*\s*([a-z0-9-]+)\s*\*/\s*@font-face\s*\{(.*?)\}", css, re.S)
count = 0
for subset, body in blocks:
    if subset != "latin":
        continue
    fam = re.search(r"font-family:\s*'([^']+)'", body).group(1)
    wght = re.search(r"font-weight:\s*(\d+)", body).group(1)
    style = re.search(r"font-style:\s*(\w+)", body).group(1)
    src = re.search(r"url\((https://[^)]+)\)", body).group(1)
    name = f"{fam.replace(' ','')}-{wght}-{style}.woff2"
    with open(os.path.join(outdir, name), "wb") as f:
        f.write(urllib.request.urlopen(urllib.request.Request(src, headers=ua), timeout=30).read())
    count += 1
    print(name)
print("downloaded", count)
