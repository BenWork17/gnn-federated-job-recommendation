import json
d = json.load(open(r"_newdata_audit\t5_verify\t5_esco_and_graph2.json", encoding="utf-8"))
g = d["graph_with_technology_skills"]
print("graph_final nodes_occupation:", g["nodes_occupation"])
print("skills_per_soc BASE groups:", 763, "| tech BASE groups:", 798)
print("=> neu nodes_occupation=832 > 798 thi nut Occupation dang o cap MA DAY DU (.xx),")
print("   trong khi canh skill lai tra cuu o cap MA GOC [:7] -> nhieu nut Occup con chia se cung mot tap skill.")
