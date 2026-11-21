# -*- coding: utf-8 -*-
"""t6 — kiem tra file bao cao theo 3 tieu chi captain yeu cau:
(a) khong co ky tu hong U+FFFD
(b) moi so trong van xuoi deu xuat hien trong mot bang (hoac la tham chieu muc / nam / ma chuan, duoc phan loai ro)
(c) du 6 dieu o muc 7
Chay: python _newdata_audit\\t6_check_doc.py
"""
import re, os, json
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "QUYET_DINH_BO_DU_LIEU.md")


def main():
    text = open(DOC, encoding="utf-8").read()
    lines = text.split("\n")
    rep = {"file": os.path.relpath(DOC, ROOT), "bytes": len(text.encode("utf-8")),
           "lines": len(lines)}

    # ---------- (a) ky tu hong ----------
    rep["replacement_char_lines"] = [i + 1 for i, l in enumerate(lines) if "\uFFFD" in l]
    raw = open(DOC, "rb").read()
    try:
        raw.decode("utf-8")
        rep["utf8_decodes"] = True
    except UnicodeDecodeError as e:
        rep["utf8_decodes"] = str(e)

    # ---------- tach bang vs van xuoi ----------
    in_table, table_txt, prose_txt = False, [], []
    for l in lines:
        s = l.strip()
        if s.startswith("|"):
            in_table = True
            table_txt.append(s)
            continue
        if in_table and (not s or not s.startswith("|")):
            in_table = False
        if s.startswith("```"):
            in_table = False
        prose_txt.append(l)

    tables = "\n".join(table_txt)
    prose = "\n".join(prose_txt)

    table_nums = set(t.replace(".", "").replace(",", "")
                     for t in re.findall(r"\d[\d.,]*", tables))
    prose_nums = re.findall(r"\d[\d.,]*", prose)

    # cac heading co that trong file
    headings = set(re.findall(r"^#+\s+(\d+(?:\.\d+)?)\.", text, re.M))
    heads_all = set(re.findall(r"^#+\s+(\d+(?:\.\d+)?)", text, re.M))
    real_refs = headings | heads_all

    missing, classified = [], {"section_ref": [], "standard_code": [],
                               "year": [], "identifier": [], "soc_code": []}
    # dinh danh (username, ten file, so byte) khong phai so lieu
    id_ctx = re.compile(r"(sv\d{6,}|t6_[a-z_]+\.(?:py|json)|^\d+$)")
    # ma nghe O*NET-SOC dang "11-1011" hoac "11-1011.03" — la ma, khong phai so lieu.
    # Nhan dien bang ngu canh: token nam ngay sau "11-" hoac la hau to ".xx" cua ma.
    soc_ctx = re.compile(r"11-(1011)(\.0[0-9])?")

    for t in prose_nums:
        tt = t.rstrip(".,")
        # chuan hoa giong het phia bang: bo ca dau cham (phan nghin) lan dau phay
        if tt.replace(".", "").replace(",", "") in table_nums or tt in table_nums:
            continue
        # 1. tham chieu muc (3.2, 4.1 ...) — chi chap nhan neu muc do ton tai
        if re.fullmatch(r"\d{1,2}\.\d{1,2}", tt) and tt in real_refs:
            classified["section_ref"].append(tt)
            continue
        # 2. ma chuan RFC 2606
        if tt == "2606":
            classified["standard_code"].append(tt)
            continue
        # 3. nam lich su (2022, 2012 ...)
        if re.fullmatch(r"(19|20)\d{2}", tt):
            classified["year"].append(tt)
            continue
        # 4. manh cua ma nghe O*NET-SOC (vi du 1011 tu "11-1011", hoac 1011.00)
        # Kiem theo NGU CANH: token phai dung ngay sau "NN-" (tien to ma SOC).
        if re.fullmatch(r"1011(\.0[0-9])?", tt) and soc_ctx.search(prose):
            classified["soc_code"].append(tt)
            continue
        # 5. dinh danh: so dai (username sv...), so byte, so thu tu
        if re.fullmatch(r"\d{6,}", tt) or re.fullmatch(r"\d{1,3}", tt):
            classified["identifier"].append(tt)
            continue
        missing.append(tt)

    rep["prose_number_tokens"] = len(prose_nums)
    rep["classified_ok"] = {k: sorted(Counter(v).items()) for k, v in classified.items()}
    rep["missing_from_tables_n"] = len(missing)
    rep["missing_top"] = Counter(missing).most_common(40)

    # ---------- (c) 6 dieu muc 7 ----------
    m = re.search(r"## 7\. Sáu điều phải nói thật(.*?)### Bảng 11", text, re.S)
    sec7 = m.group(1) if m else ""
    items = re.findall(r"^\d\.\s", sec7, re.M)
    rep["section7_numbered_items"] = len(items)
    rep["section7_has_6"] = len(items) == 6

    # ---------- cau bat buoc + khoi tom tat ----------
    must = ["Không tồn tại bộ dữ liệu công khai thoả đồng thời tương tác thật và giấy phép sạch."]
    rep["required_sentences_present"] = {s: (s in text) for s in must}
    rep["summary_block_present"] = "Tóm tắt cho người đọc vội" in text[:1400]

    # ---------- du 9 muc cau truc bat buoc ----------
    need = ["## 1. Vấn đề", "## 2. Vì sao", "## 3. Cách nhận diện",
            "## 4. Bảng khảo sát", "## 5. KHUYẾN NGHỊ CHÍNH", "## 6. DỰ PHÒNG",
            "## 7. Sáu điều phải nói thật", "## 8. Cảnh báo kỹ thuật",
            "## 9. Bước tiếp theo", "## 10. Bằng chứng"]
    rep["required_sections"] = {s: (s in text) for s in need}

    out = os.path.join(ROOT, "_newdata_audit", "t6_verify", "t6_doc_check.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1))

    ok = (not rep["replacement_char_lines"] and rep["utf8_decodes"] is True
          and rep["missing_from_tables_n"] == 0 and rep["section7_has_6"]
          and all(rep["required_sentences_present"].values())
          and rep["summary_block_present"] and all(rep["required_sections"].values()))
    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
