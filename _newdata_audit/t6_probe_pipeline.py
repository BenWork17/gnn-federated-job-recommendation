# Kiem tra pipeline t5/t4 co nhat quan MOT cap SOC khong
import re, pathlib
for p in ["_newdata_audit/t5_graph_design.py","_newdata_audit/t4_onet_coverage.py"]:
    src = pathlib.Path(p).read_text(encoding="utf-8")
    print("===", p)
    for i,l in enumerate(src.splitlines(),1):
        if "[:7]" in l or "setdefault" in l:
            print(" %4d %s" % (i, l.strip()[:110]))
