"""t2: tai O*NET database text (13 MB) va do so nghe / so ky nang / ma tran nghe-ky nang."""
import io
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_data")
ROOT.mkdir(parents=True, exist_ok=True)
URL = "https://www.onetcenter.org/dl_files/database/db_29_3_text.zip"
zpath = ROOT / "db_29_3_text.zip"

if not zpath.exists() or zpath.stat().st_size < 1_000_000:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    zpath.write_bytes(data)
    print("downloaded bytes:", len(data))

z = zipfile.ZipFile(zpath)
names = z.namelist()
print("entries:", len(names))
out = ROOT / "onet"
out.mkdir(exist_ok=True)
for n in names:
    if not n.endswith("/"):
        z.extract(n, out)
print("extracted to", out)

base = out / "db_29_3_text"
for f in ["Skills.txt", "Occupation Data.txt", "Technology Skills.txt", "Tools Used.txt",
          "Knowledge.txt", "Abilities.txt", "Work Activities.txt", "Alternate Titles.txt",
          "Sample of Reported Titles.txt", "Task Statements.txt", "Emerging Tasks.txt",
          "Education, Training, and Experience.txt", "Work Context.txt",
          "Interests.txt", "Work Styles.txt", "Basic Interests.txt",
          "Survey Booklet Locations.txt", "Level Scale Anchors.txt", "Content Model Reference.txt",
          "Occupation Level Metadata.txt"]:
    p = base / f
    if p.exists():
        raw = p.read_bytes()
        txt = raw.decode("utf-8", "replace")
        lines = txt.count("\n")
        head = txt.split("\n")[0]
        print(f"{f}: {p.stat().st_size} bytes, {lines} lines | header: {head[:200]}")
    else:
        print(f"{f}: MISSING")
