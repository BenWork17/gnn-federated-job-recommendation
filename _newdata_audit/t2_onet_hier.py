"""t2: chi tiet cac file phan cap cua O*NET (DWA/IWA) + SOC taxonomy."""
import csv
import json
from pathlib import Path

B = Path(r"E:\2026\DUT\DSS\SauGK\CuoiKi\_newdata_audit\t2_data\onet\db_29_3_text")


def head(name, n=3, delim="\t"):
    p = B / name
    if not p.exists():
        return {"file": name, "exists": False}
    with p.open(encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f, delimiter=delim, quoting=csv.QUOTE_NONE)
        rows = []
        for i, row in enumerate(r):
            rows.append(row)
            if i >= n:
                break
    txt = p.read_text(encoding="utf-8", errors="replace")
    return {"file": name, "exists": True, "bytes": p.stat().st_size,
            "lines": txt.count("\n"), "rows": rows}


for f in ["DWA Reference.txt", "IWA Reference.txt", "Content Model Reference.txt",
          "Skills to Work Activities.txt", "Education, Training, and Experience Categories.txt"]:
    print(json.dumps(head(f), indent=2, ensure_ascii=False))

# SOC taxonomy: Occupation Data codes -> major group prefix
occ = []
with (B / "Occupation Data.txt").open(encoding="utf-8", errors="replace", newline="") as f:
    r = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
    for row in r:
        occ.append(row["O*NET-SOC Code"].strip())

from collections import Counter
maj = Counter(c.split("-")[0] for c in occ)
print("major groups:", dict(sorted(maj.items())))
