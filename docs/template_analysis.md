# Template Specification: `BaoCaoPBL7.docx` & `BaoCaoPBL7_DinhDangChuan.pdf`

**Executive Summary**: `BaoCaoPBL7.docx` (modified `2026-06-11 11:07`) is an earlier Pandoc-generated draft, whereas `BaoCaoPBL7_DinhDangChuan.pdf` (exported `2026-06-12 10:29` from Microsoft Word 365 by Phạm Bá Thành) is the **authoritative standard format** (*Định Dạng Chuẩn*). Where the two differ (page margins, line spacing, first-line indent, footer page-number prefix, List of Figures / List of Tables front matter, caption numbering & figure caption placement), **follow `BaoCaoPBL7_DinhDangChuan.pdf`** while reusing the clean official university/faculty logos (`word/media/image1.png` and `word/media/image2.png`) embedded in `BaoCaoPBL7.docx`.

---

## 1. Page Setup & Sections

| Property | `BaoCaoPBL7_DinhDangChuan.pdf` (Authoritative) | `BaoCaoPBL7.docx` (Pandoc Draft) | Recommended FedGraph `.docx` |
|---|---|---|---|
| **Paper Size** | A4 Portrait (`595.32 × 841.92 pt` = `21.00 × 29.70 cm`) | A4 Portrait (`11906 × 16838 twips` = `21.00 × 29.70 cm`) | A4 Portrait (`21.0 × 29.7 cm`) |
| **Top Margin** | `2.50 cm` (`70.74 pt`) | `2.00 cm` (`1134 twips`) | **`2.5 cm`** (`Inches` / `Cm(2.5)`) |
| **Bottom Margin** | `2.50 cm` (`771.02 pt` max y1 → `2.50 cm`) | `2.00 cm` (`1134 twips`) | **`2.5 cm`** |
| **Left Margin** | `3.50 cm` (`99.26 pt`) | `2.00 cm` (`1134 twips`) | **`3.5 cm`** |
| **Right Margin** | `2.00 cm` (`538.78 pt` table right edge → `2.00 cm`) | `2.00 cm` (`1134 twips`) | **`2.0 cm`** |
| **Usable Text Width** | **`15.50 cm`** (`439.5 pt`) | `17.00 cm` | **`15.5 cm`** |
| **Gutter** | `0 cm` | `0 cm` | `0 cm` |
| **Header / Footer Dist** | Header `y=[33.8, 48.2] pt` (~`1.20–1.27 cm`); Footer `y=[780.5, 794.9] pt` (~`1.66 cm` from bottom) | `1.27 cm` (`720 twips`) | `1.27 cm` |
| **Page Borders** | **None** (`w:pgBorders` absent; Page 1 drawings are table borders only) | **None** | **None** |
| **Section Breaks** | Single logical flow with `different_first_page_header_footer = True` (`<w:titlePg/>`), Page 1 = Cover (no header/footer), Page 2 (`MỤC LỤC`) starts at Arabic page `1` through `113` | Single `<w:sectPr>` (`<w:titlePg/>`), manual `<w:br w:type="page"/>` after Cover | **2 Sections** (Next-Page break after Cover): Section 0 (Cover, no header/footer) → Section 1 (Front matter + Body, `pgNumType start=1`, Arabic `1, 2, 3...`). *Alternative*: Roman `i, ii, iii` for front matter if desired, though `BaoCaoPBL7_DinhDangChuan.pdf` uses Arabic `1..7` for front matter and `8..113` for body. |

### Header & Footer Specification
- **Cover Page (Page 1)**: Suppress header and footer (`different_first_page_header_footer = True` or unlinked Section 0).
- **Header (Pages 2+)**:
  - Text: Course/Report title, e.g., `Báo Cáo Đồ Án Cuối Kỳ — DSS` (in template: `Báo Cáo PBL7 : Dự Án Chuyên Ngành 2`).
  - Style: Times New Roman, `10 pt` (`9.96 pt` in PDF, `sz=20`), *Italic*, black (`000000`), left-aligned (note: template PDF has `x=127.6 pt` from stray `1 cm` indent; aligning cleanly to left margin `3.5 cm` or keeping uniform is fine — left margin `3.5 cm` is cleaner).
- **Footer (Pages 2+)**:
  - Left side: Student names separated by dashes, e.g., `Phan Gia Bảo – Nguyễn Văn Chương`.
  - Right side: Bare Arabic `{PAGE}` field (no `"Page "` word! Notice `BaoCaoPBL7.docx` had `"Page 1"` with spaces, which was fixed to bare `"1"` in `BaoCaoPBL7_DinhDangChuan.pdf`).
  - Style: Times New Roman, `10 pt` (`sz=20`), *Italic*, black (`000000`). Use a **right-aligned tab stop at `15.5 cm`** (instead of 44 spaces as in `footer1.xml`) so page numbers align crisply at the right margin.

---

## 2. Cover Page Structure

`BaoCaoPBL7` uses a **single Cover Page** (no separate inner cover, no page frame/border). Structure top-to-bottom:

1. **University & Faculty Header Table** (3 columns, borderless, centered):
   - In `BaoCaoPBL7.docx`, total width was `17.0 cm` (`[3.0, 11.0, 3.0] cm`). For `15.5 cm` usable width, scale cleanly to **`[2.75, 10.0, 2.75] cm`**.
   - **Left cell**: Official DUT emblem (`word/media/image1.png` inside `BaoCaoPBL7.docx`, `176×175 px`, rendered `2.50 × 2.49 cm`).
   - **Center cell** (vertically & horizontally centered):
     - Line 1: `TRƯỜNG ĐẠI HỌC BÁCH KHOA` — Times New Roman, **`18 pt` Bold**, ALL CAPS.
     - Line 2: `KHOA CÔNG NGHỆ THÔNG TIN` — Times New Roman, **`18 pt` Bold**, ALL CAPS.
     - *(Optional sub-line or keep exact two lines; `ORIGINAL_REQUEST.md` specifies `Đại học Bách khoa, Đại học Đà Nẵng (DUT)` — can write `ĐẠI HỌC ĐÀ NẴNG` / `TRƯỜNG ĐẠI HỌC BÁCH KHOA` / `KHOA CÔNG NGHỆ THÔNG TIN` or keep `TRƯỜNG ĐẠI HỌC BÁCH KHOA` + `KHOA CÔNG NGHỆ THÔNG TIN` and mention ĐH Đà Nẵng in footer/metadata; keeping `ĐẠI HỌC ĐÀ NẴNG` small or `TRƯỜNG ĐẠI HỌC BÁCH KHOA - ĐHĐN` / exact 2 lines + `ĐÀ NẴNG, 11/2026` matches the layout cleanly).*
   - **Right cell**: Official IT Faculty logo (`word/media/image2.png` inside `BaoCaoPBL7.docx`, `170×171 px`, rendered `2.40 × 2.41 cm`).
2. **Report Type & Course Title** (centered, Times New Roman Bold):
   - Blank spacing (~2 lines)
   - `BÁO CÁO` — **`20 pt` Bold**, ALL CAPS (`y=199.1 pt` in PDF)
   - `Đồ án cuối kỳ — DSS` (template: `PBL 7: Dự án chuyên ngành 2`) — **`19 pt` Bold** (`18.96 pt` in PDF)
3. **Topic Block** (centered, Times New Roman Bold):
   - Blank spacing (~1–2 lines)
   - `Tên Đề Tài:` — **`16 pt` Bold** (`15.96 pt` in PDF)
   - Topic Title (e.g., `FedGraph: Hệ thống gợi ý việc làm bảo vệ quyền riêng tư sử dụng LightGCN và Học liên kết đa silo (Cross-Silo Federated Learning)`) — **`16 pt` Bold**
4. **Advisor & Student Metadata Block**:
   - Blank spacing (~3–4 lines to push metadata block to lower half)
   - **Advisor line** (`Giảng viên hướng dẫn:`): **YES, explicitly present!**
     - Template text: `Giảng viên hướng dẫn:        TS. Trịnh Công Duy` — **`14 pt` Bold**, centered (`y=481.4 pt` in PDF).
     - For FedGraph: Use explicit placeholder: `Giảng viên hướng dẫn:        [Họ và tên Giảng viên hướng dẫn]` (per `ORIGINAL_REQUEST.md`).
   - **Student Table** (3 columns, centered, total width `15.5 cm` = `[5.17, 5.17, 5.17] cm`, full grid borders `0.5 pt` (`w:sz="4"`) single black, no shading):
     - Header row (`13 pt` **Bold**, centered H & V): `HỌ VÀ TÊN` | `Lớp Học Phần` | `Mã Sinh Viên` (note: `.docx` had `HỌ VÀ TÊN SINH VIÊN`, PDF shortened to `HỌ VÀ TÊN`)
     - Data rows (`13 pt` Regular, centered H & V):
       - `Phan Gia Bảo` | `...` (or explicit class placeholder / omit unknown class) | `102220265`
       - `Nguyễn Văn Chương` | `...` | `102220267`
5. **Location & Date Footer** (centered, near bottom of Cover Page):
   - `ĐÀ NẴNG, 11/2026` (template: `ĐÀ NẴNG, 06/2026`) — **`14 pt` Regular** (`14.04 pt` in PDF).

---

## 3. Front Matter Structure & Order

In `BaoCaoPBL7_DinhDangChuan.pdf`, Pages 2–8 (numbered `1`–`7`) contain **three** front matter sections in this exact order:
1. **`MỤC LỤC`** (Table of Contents, PDF pp. 2–6, report pp. `1–5`):
   - Title: `MỤC LỤC`, centered, Times New Roman `16 pt` Bold, ALL CAPS.
   - Entries: `13 pt` Regular (`CHƯƠNG X. ...` at level 1, `X.Y. ...` indented `~0.46 cm` at level 2) with dot leaders (`...`) and right-aligned page numbers.
   - Note: In `.docx`, use a Word TOC field (`TOC \o "1-3" \h \z \u`) inside `<w:sdt>` or paragraph entries + `<w:settings><w:updateFields w:val="true"/></w:settings>` so Word populates exact page numbers on open (or compute exact page numbers via LibreOffice/Word COM after generation!).
2. **`HÌNH ẢNH`** (or `DANH MỤC HÌNH ẢNH`, List of Figures, PDF p. 7, report p. `6`):
   - Title: `HÌNH ẢNH` (or `DANH MỤC HÌNH ẢNH`), centered, `16 pt` Bold, ALL CAPS.
   - Entries: `Hình 1. <Caption text> .......... <page>`, `13 pt` Regular.
   - Starts on a **new page**.
3. **`BẢNG BIỂU`** (or `DANH MỤC BẢNG BIỂU`, List of Tables, PDF p. 8, report p. `7`):
   - Title: `BẢNG BIỂU` (or `DANH MỤC BẢNG BIỂU`), centered, `16 pt` Bold, ALL CAPS.
   - Entries: `Bảng 1. <Caption text> .......... <page>`, `13 pt` Regular.
   - Starts on a **new page**.

*Note*: `BaoCaoPBL7_DinhDangChuan.pdf` does **not** include `Lời cảm ơn`, `Lời mở đầu / Tóm tắt`, or `Danh mục từ viết tắt` as separate front matter pages (though `Danh mục từ viết tắt` or `Tóm tắt` can be added before `CHƯƠNG 1` if helpful for FedGraph's FL/GNN acronyms, or `Mở đầu` is placed as Section `1.1. Mở đầu` inside `CHƯƠNG 1` just like the template).

---

## 4. Typography & Styles

### Global Defaults & Body Text
- **Font Family**: **`Times New Roman`** everywhere (except multi-line code snippets in `Courier New` `9 pt`).
  - *Crucial warning*: `BaoCaoPBL7.docx` had `Calibri` (`majorFont`) / `Cambria` (`minorFont`) in `theme1.xml` and `Heading1..9` styles, overridden with direct `<w:rFonts w:ascii="Times New Roman" .../>` and `<w:color w:val="000000"/>` on every run! When generating FedGraph `.docx`, set `Times New Roman` and `#000000` directly in `Normal`, `Heading 1..4`, `Caption`, etc., so no Calibri/blue `#4F81BD` leaks through.
- **Body Text**:
  - Font: `Times New Roman`, **`13 pt`** (`sz=26`), Regular, Black (`#000000`).
  - Alignment: **Justified** (`WD_ALIGN_PARAGRAPH.JUSTIFY` / `<w:jc w:val="both"/>`).
  - Line Spacing: **`1.5` lines** (`w:line="360" w:lineRule="auto"`, verified by `22.44 pt` line step in PDF vs `14.95 pt` single height; draft `.docx` had `1.3` = `312`).
  - First-Line Indent: **`1.0 cm`** (`567 twips` = `28.35 pt`, verified by `127.6 - 99.26 = 28.34 pt` in PDF).
  - Paragraph Spacing: `0 pt` before, **`6 pt` after** (`120 twips`, verified by `28.4 pt - 22.4 pt = 6.0 pt` inter-paragraph gap in PDF).
- **Inline Code / Technical Identifiers** (optional): `Times New Roman 11 pt` (used for file paths / function names like `best_v1.pt`, `get_vehicle_model()`) or `13 pt` regular; multi-line code/JSON blocks use **`Courier New 9 pt`**, left-aligned, single/compact spacing (`1.15` lines), no first-line indent.
- **Bullet Lists**: `•` bullet (`13 pt` Times New Roman), hanging indent, `1.5` line spacing.

### Heading Hierarchy & Numbering
| Level | Example Format | Font & Size | Weight / Case / Color | Alignment & Indent | Spacing & Flow |
|---|---|---|---|---|---|
| **Heading 1** | `CHƯƠNG 1. GIỚI THIỆU BÀI TOÁN VÀ MỤC TIÊU NGHIÊN CỨU` | `Times New Roman`, **`16 pt`** (`sz=32`) | **Bold**, **ALL CAPS**, Black (`#000000`) | Left-aligned (`0 cm` indent; note PDF had `1.0 cm` first-line indent quirk from `Ctrl+A`, `0 cm` is cleaner) | Before `12 pt`, After `6 pt`, Line spacing `1.5`, `keep_with_next=True`, `keep_together=True`. *(Chapters flow continuously or start on new page — PDF had 6/12 chapters mid-page and 6/12 at page top; starting each major `CHƯƠNG` on a new page or keeping continuous are both acceptable, though new page per chapter is standard academic polish).* |
| **Heading 2** | `1.1. Mở đầu` | `Times New Roman`, **`14 pt`** (`sz=28`) | **Bold**, Title/Sentence case, Black (`#000000`) | Left-aligned (`0 cm` or `1.0 cm` first-line indent; PDF used `1.0 cm` indent `x=127.6 pt`) | Before `12 pt`, After `6 pt`, Line spacing `1.5`, `keep_with_next=True`. |
| **Heading 3** *(not in PBL7 sample, recommended if needed)* | `1.1.1. Chi tiết ...` | `Times New Roman`, **`13 pt`** (`sz=26`) | **Bold** (or **Bold Italic**), Black (`#000000`) | Left-aligned (`0 cm` or `1.0 cm`) | Before `6–10 pt`, After `4–6 pt`, Line spacing `1.5`, `keep_with_next=True`. |
| **Heading 4** *(avoid if possible; if needed)* | `1.1.1.1. ...` | `Times New Roman`, **`13 pt`** | *Italic* or **Bold Italic**, Black | Left-aligned | Before `6 pt`, After `4 pt`, `keep_with_next=True`. |

---

## 5. Captioning, Tables, Equations & References

- **Figure Captions**:
  - Format: **`Hình 1. <Tiêu đề hình>`** (sequential `1, 2, 3...` across the entire report with a period `.` in `BaoCaoPBL7_DinhDangChuan.pdf`; note draft `.docx` used `Hình 1.1:` above image, which was corrected in `_DinhDangChuan.pdf` to `Hình 1.` **BELOW** the image!).
  - Placement: **Centered BELOW the image** (no first-line indent so it centers strictly within the `15.5 cm` text area).
  - Style: `Times New Roman`, **`13 pt` Bold Italic**, Black (`#000000`), `0 pt` before / `6–12 pt` after. Image paragraph itself should be centered with `keep_with_next = True` and `0 cm` indent.
- **Table Captions**:
  - Format: **`Bảng 1. <Tiêu đề bảng>`** (sequential `1, 2, 3...` across the entire report with a period `.` in `_DinhDangChuan.pdf`; draft `.docx` had `Bảng 1.1:`).
  - Placement: **Centered ABOVE the table**.
  - Style: `Times New Roman`, **`13 pt` Bold Italic**, Black (`#000000`), `keep_with_next = True`.
- **Table Styling**:
  - Borders: Thin solid black grid borders (`0.5 pt` = `w:sz="4"`, `top`, `bottom`, `left`, `right`, `insideH`, `insideV`).
  - Shading: **None** (white/transparent background, even on header row in `_DinhDangChuan.pdf`).
  - Header Row: **Bold**, centered horizontally and vertically, `13 pt` (or `12 pt` for 5+ column wide tables), `<w:tblHeader/>` repeat header across page breaks + `<w:cantSplit/>` on rows.
  - Body Cells: Regular `Times New Roman`, **`13 pt`** (standard 2–4 column tables) or **`11–12 pt`** (dense/wide tables, e.g., Table 3 & Table 23 in PDF), `1.15–1.3` line spacing inside cells, `0 cm` first-line indent, cell margins `top/bottom ~60–80 twips`, `left/right ~108 twips`.
- **Equations**:
  - `BaoCaoPBL7` contains **0 equations** (`oMath count = 0`). For FedGraph (which has LightGCN propagation, BPR loss, FedAvg/FedProx objective, DP-SGD noise, Recall@K/NDCG@K/MRR@K), use a **borderless 2-column (or 3-column) table** (centered equation in col 1 via OMML or Unicode math / Cambria Math, right-aligned number `(1.1)` or `(3.1)` in col 2, `13 pt`).
- **Citations & References (`TÀI LIỆU THAM KHẢO`)**:
  - Format: **IEEE-style numbered references `[1]`, `[2]`, ...**
  - Template Reference List (`CHƯƠNG 11. TÀI LIỆU THAM KHẢO`, PDF p. 108):
    - Grouped or flat numbered list `[1] Author(s). "Title." Venue/Source, Year. URL/DOI`.
    - Font: `Times New Roman 13 pt` Regular, left-aligned (`0 cm` indent, or hanging indent `0.8 cm`), black text (avoid raw Pandoc blue `#4F81BD` hyperlink color if printing/formal academic submission; or use dark/black hyperlink styling).
    - In-text citations: `[1]`, `[2, 3]` (note: PBL7 lacked in-text `[N]` citations in body prose, so FedGraph should improve on it by actually citing `[1]`, `[2]` inline!).

---

## 6. Practical Generation Strategy & Pitfalls

### Strategy Recommendation: **Build Cleanly from Scratch (or Minimal Styled Base) in `python-docx` + Extract Logos from `BaoCaoPBL7.docx`**
**Do NOT blindly clear & reuse `BaoCaoPBL7.docx`'s body**, because `BaoCaoPBL7.docx` is an un-updated Pandoc draft that has the **wrong margins** (`2.0 cm` instead of `3.5 / 2.0 / 2.5 / 2.5 cm`), **wrong line spacing** (`1.3` instead of `1.5`), **Calibri/Cambria + blue `#4F81BD` theme defaults** in `styles.xml`, **missing `HÌNH ẢNH` / `BẢNG BIỂU` lists**, and `"Page 1"` in `footer1.xml`.

Instead:
1. **Extract the two official logos directly in-memory** from `maubaocao/BaoCaoPBL7.docx` (`word/media/image1.png` = DUT logo `176×175 px`, `word/media/image2.png` = IT Faculty logo `170×171 px`) via `zipfile.ZipFile` so we don't copy binary assets into `.agents/teamwork/` or modify `maubaocao/`.
2. **Build the `.docx` programmatically with `python-docx`** using the exact verified specifications from `BaoCaoPBL7_DinhDangChuan.pdf` above:
   - Section 0 (Cover Page): `2.5 / 2.5 / 3.5 / 2.0 cm` margins, no header/footer.
   - Section 1 (Front Matter + Chapters): `Next Page` section break, `pgNumType start=1`, Arabic page numbers, Header `10 pt Italic`, Footer `10 pt Italic` with right tab stop at `15.5 cm` and bare `{PAGE}` field.
   - Explicit `Times New Roman` (`w:ascii`, `w:hAnsi`, `w:cs`, `w:eastAsia`) and `#000000` on `Normal`, `Heading 1`, `Heading 2`, `Heading 3`, `Caption`, and runs.
   - Explicit `keep_with_next` on Headings, Table Captions (above tables), and Figure Paragraphs (above Figure Captions).
   - Enable `<w:updateFields w:val="true"/>` in `word/settings.xml` AND, if LibreOffice (`soffice`) or Microsoft Word is available, convert `.docx` → `.pdf` to visually verify page breaks, TOC/List of Figures/Tables page numbers, table wrapping, and zero overlaps!

### Specific Pitfalls to Watch Out For
1. **Pandoc `Calibri` / `#4F81BD` trap**: If cloning `BaoCaoPBL7.docx`, `Heading1..4` in `styles.xml` still point to `majorHAnsi` (`Calibri`) and `#4F81BD` blue! Always explicitly set `rFonts` (`Times New Roman`) and `color` (`000000`) on style definitions AND runs.
2. **Centering + `first_line_indent` trap**: In `BaoCaoPBL7_DinhDangChuan.pdf`, centered captions (`Hình 2`, `Bảng 1`) were shifted slightly right (`+0.5 cm`) because `first_line_indent = 1.0 cm` remained active! Always explicitly set `first_line_indent = Cm(0)` on Headings, Captions, Figures, Table cells, Headers/Footers, Code blocks, and List items.
3. **Footer `"Page "` trap**: `BaoCaoPBL7.docx` `footer1.xml` contains literal `" Page "` before `{PAGE}` and 47 spaces for alignment. Use a single right-aligned tab stop at `15.5 cm` and bare `{PAGE}`.
4. **Vietnamese Font Fallback**: Always set `rFonts` for `ascii`, `hAnsi`, `eastAsia`, and `cs` to `Times New Roman` so Vietnamese diacritics (`ă, â, đ, ê, ô, ơ, ư`, tone marks) never fall back to a mismatched font.
5. **TOC / List of Figures / List of Tables**: `python-docx` cannot compute dynamic page numbers by itself. Either insert standard Word fields (`TOC \o "1-3"`, `TOC \h \z \c "Hình"`, `TOC \h \z \c "Bảng"`) with `updateFields=true` AND update fields via Word COM / LibreOffice macro before final delivery, OR verify actual page numbers from rendered PDF and populate static/hybrid TOC entries accurately.
