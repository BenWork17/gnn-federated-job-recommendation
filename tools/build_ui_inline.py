"""build_ui_inline.py — sinh bản "inline" của ui/index.html để nhúng vào Streamlit.

VÌ SAO CẦN:
    `ui/index.html` nạp CSS/JS bằng đường dẫn TƯƠNG ĐỐI:

        <link rel="stylesheet" href="assets/app.css">
        <script src="vendor/chart.umd.min.js"></script>
        <script src="assets/app.js"></script>

    Nhúng thẳng file đó vào `streamlit.components.v1.html()` thì iframe dùng
    `srcdoc` (URL là `about:srcdoc`), nên mọi đường dẫn tương đối đều trỏ vào
    chỗ không tồn tại → mất CSS, không có JS. Vì vậy phải thay từng tham chiếu
    bằng NỘI DUNG của file tương ứng, ra một chuỗi HTML duy nhất.

NGUYÊN TẮC:
    * KHÔNG sửa file gốc trong `ui/` — chỉ ĐỌC. Bản sinh ra nằm ở
      `ui/_inline/index_inline.html` và ghi rõ "KHÔNG SỬA TAY".
    * Idempotent: chạy lại nhiều lần cho ra đúng cùng một chuỗi byte
      (không timestamp, không thứ tự phụ thuộc hệ điều hành).
    * Bền với thay đổi của `ui/`: không hard-code đúng 3 thẻ như hiện tại mà
      inline MỌI `<link rel="stylesheet">` / `<script src="...">` trỏ tới file
      nội bộ. Thêm file CSS/JS mới trong `ui/` là tự động được nhúng.
    * Font trong `app.css` (`url('../vendor/fonts/*.woff2')`) cũng được nhúng
      base64, nếu không thì trong iframe srcdoc font rơi về font hệ thống.

CÁCH DÙNG:
    python tools/build_ui_inline.py            # sinh (chỉ ghi khi nội dung đổi)
    python tools/build_ui_inline.py --force    # luôn ghi lại
    python tools/build_ui_inline.py --check    # exit 1 nếu bản sinh đã cũ
    python tools/build_ui_inline.py --no-fonts # không nhúng base64 font

API cho app/views/giam_sat_node.py:
    from tools.build_ui_inline import ensure_inline, PLACEHOLDER
    info = ensure_inline()          # -> {"path": Path, "size": int, ...}
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"
SRC_HTML = UI_DIR / "index.html"
OUT_DIR = UI_DIR / "_inline"
OUT_HTML = OUT_DIR / "index_inline.html"

# Streamlit thay token này bằng API base thật (xem app/views/giam_sat_node.py).
# Để nguyên token khi mở file trực tiếp bằng trình duyệt → app.js dùng mặc định
# http://127.0.0.1:8000.
PLACEHOLDER = "__FL_API_BASE__"

# Trần kích thước cho một asset nhúng base64 (tránh phình file vô ích).
MAX_ASSET_BYTES = 2 * 1024 * 1024

_MIME = {
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}

_SHIM = """<script id="fl-api-shim">
/* ---------------------------------------------------------------
   Bản inline: iframe của components.html dùng srcdoc nên KHÔNG có
   query string. app.js đọc API base bằng
       new URLSearchParams(location.search).get('api') || 'http://127.0.0.1:8000'
   nên ở đây bơm giá trị ?api= tương đương (Streamlit thay token bên dưới).
   Để nguyên token = chạy trực tiếp bằng file:// → dùng mặc định 8000.
   --------------------------------------------------------------- */
(function () {
  var api = "__FL_API_BASE__";
  if (!api || api.indexOf("__FL") === 0) return;      // chưa được chèn
  document.documentElement.classList.add('is-embed');
  document.addEventListener('DOMContentLoaded', function () {
    var p = document.getElementById('ncWhatPanel');
    if (p) p.removeAttribute('open');
  });
  var Native = window.URLSearchParams;
  function Patched(init) {
    var inst = new Native(init);
    var orig = inst.get.bind(inst);
    inst.get = function (k) {
      var v = orig(k);
      if (v !== null && v !== "") return v;
      return k === "api" ? api : null;
    };
    return inst;
  }
  Patched.prototype = Native.prototype;
  window.URLSearchParams = Patched;
})();
</script>"""


# --------------------------------------------------------------------- tiện ích
def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _read_text(path: Path) -> str:
    # utf-8-sig: chịu được BOM nếu ai đó lưu file bằng Notepad
    return path.read_text(encoding="utf-8-sig")


def _is_local_ref(ref: str) -> bool:
    ref = ref.strip()
    return bool(ref) and not ref.startswith(
        ("http://", "https://", "//", "data:", "blob:", "#", "about:"))


def _mime_of(path: Path) -> str:
    return _MIME.get(path.suffix.lower(), "application/octet-stream")


def _inline_css_urls(css: str, css_path: Path, *, fonts: bool) -> tuple[str, list[str]]:
    """Nhúng base64 các `url(...)` trỏ tới file nội bộ trong CSS."""
    skipped: list[str] = []

    def repl(m: re.Match[str]) -> str:
        quote, ref = m.group(1), m.group(2).strip()
        if not _is_local_ref(ref):
            return m.group(0)
        target = (css_path.parent / ref).resolve()
        if not target.is_file():
            skipped.append(f"{css_path.name}: thiếu {ref}")
            return m.group(0)
        if not fonts and target.suffix.lower() in (".woff", ".woff2", ".ttf", ".otf"):
            skipped.append(f"{css_path.name}: bỏ qua font {ref} (--no-fonts)")
            return m.group(0)
        if target.stat().st_size > MAX_ASSET_BYTES:
            skipped.append(f"{css_path.name}: {ref} > 2 MB, giữ nguyên url")
            return m.group(0)
        payload = base64.b64encode(target.read_bytes()).decode("ascii")
        return f"url({quote}data:{_mime_of(target)};base64,{payload}{quote})"

    return re.sub(r"url\(\s*(['\"]?)([^'\")]+?)\1\s*\)", repl, css), skipped


def _guard_script(js: str) -> str:
    """`</script>` trong nguồn JS sẽ đóng thẻ sớm → escape (tương đương trong JS)."""
    return re.sub(r"</(script)", r"<\\/\1", js, flags=re.IGNORECASE)


def _guard_style(css: str) -> str:
    """`</style>` trong CSS đóng thẻ sớm → escape (CSS hiểu `\\/` là `/`)."""
    return re.sub(r"</(style)", r"<\\/\1", css, flags=re.IGNORECASE)


# --------------------------------------------------------------------- nhúng
def _inline_stylesheets(html: str, base: Path, *, fonts: bool,
                        used: list[str], skipped: list[str]) -> str:
    def repl_link(m: re.Match[str]) -> str:
        tag = m.group(0)
        if "stylesheet" not in tag.lower():
            return tag
        href_m = re.search(r'href\s*=\s*["\']([^"\']+)["\']', tag, re.IGNORECASE)
        if not href_m:
            return tag
        href = href_m.group(1).strip()
        if not _is_local_ref(href):
            return tag
        path = (base / href).resolve()
        if not path.is_file():
            skipped.append(f"thiếu {href}")
            return tag
        css, sub_skipped = _inline_css_urls(_read_text(path), path, fonts=fonts)
        skipped.extend(sub_skipped)
        used.append(f"{path.relative_to(ROOT).as_posix()}")
        rel = path.relative_to(ROOT).as_posix()
        return (f"<style data-inline-from=\"{rel}\">\n"
                f"{_guard_style(css)}\n</style>")

    return re.sub(r"<link\b[^>]*>", repl_link, html, flags=re.IGNORECASE)


def _inline_scripts(html: str, base: Path, *, used: list[str],
                    skipped: list[str]) -> str:
    pattern = re.compile(r"<script\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)[\"'][^>]*>\s*</script>",
                         re.IGNORECASE)

    def repl_script(m: re.Match[str]) -> str:
        src = m.group(1).strip()
        if not _is_local_ref(src):
            return m.group(0)
        path = (base / src).resolve()
        if not path.is_file():
            skipped.append(f"thiếu {src}")
            return m.group(0)
        used.append(path.relative_to(ROOT).as_posix())
        rel = path.relative_to(ROOT).as_posix()
        return (f"<script data-inline-from=\"{rel}\">\n"
                f"{_guard_script(_read_text(path))}\n</script>")

    return pattern.sub(repl_script, html)


def _insert_shim(html: str) -> str:
    """Chèn shim ?api= ngay sau <body> — chạy trước mọi <script> ở cuối trang."""
    m = re.search(r"<body\b[^>]*>", html, re.IGNORECASE)
    if not m:
        # không có <body> (file lạ) → gắn trước </head> để vẫn chạy trước app.js
        idx = re.search(r"</head>", html, re.IGNORECASE)
        return html[:idx.start()] + _SHIM + "\n" + html[idx.start():] if idx \
            else _SHIM + "\n" + html
    return html[:m.end()] + "\n" + _SHIM + html[m.end():]


def _insert_banner(html: str, sources: list[tuple[str, str]]) -> str:
    """Ghi chú 'KHÔNG SỬA TAY' ngay sau <!DOCTYPE html> (không đặt trước doctype)."""
    lines = [
        "<!-- ============================================================",
        "     FILE SINH TỰ ĐỘNG — KHÔNG SỬA TAY.",
        "     Sinh bởi: python tools/build_ui_inline.py",
        "     Nguồn: ui/index.html + CSS/JS/font trong ui/ (đã nhúng inline).",
        "     Sửa giao diện ở ui/ rồi chạy lại lệnh trên; file này sẽ bị ghi đè.",
    ]
    for name, digest in sources:
        lines.append(f"       {name} sha256:{digest}")
    lines += ["     ============================================================ -->"]
    banner = "\n".join(lines)
    m = re.search(r"<!DOCTYPE[^>]*>", html, re.IGNORECASE)
    if m:
        return html[:m.end()] + "\n" + banner + html[m.end():]
    return banner + "\n" + html


# --------------------------------------------------------------------- render
def render(*, fonts: bool = True) -> tuple[str, dict]:
    """Trả về (chuỗi HTML inline, thông tin chẩn đoán)."""
    if not SRC_HTML.is_file():
        raise FileNotFoundError(f"không thấy {SRC_HTML}")

    src = _read_text(SRC_HTML)
    base = SRC_HTML.parent
    used: list[str] = []
    skipped: list[str] = []

    html = _inline_stylesheets(src, base, fonts=fonts, used=used, skipped=skipped)
    html = _inline_scripts(html, base, used=used, skipped=skipped)
    html = _insert_shim(html)

    sources = [("ui/index.html", _sha(src))]
    for rel in used:
        sources.append((rel, _sha(_read_text(ROOT / rel))))

    html = _insert_banner(html, sources)

    # Còn tham chiếu tương đối nào chưa xử lý? (chẩn đoán, không làm hỏng build)
    leftovers = sorted({
        ref for ref in re.findall(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', html)
        if _is_local_ref(ref) and not ref.startswith(("assets/", "__"))
        and re.search(r"\.(css|js)$", ref, re.IGNORECASE)
    })
    info = {
        "path": OUT_HTML,
        "size": len(html.encode("utf-8")),
        "sources": [name for name, _ in sources],
        "skipped": skipped,
        "leftovers": leftovers,
        "fonts": fonts,
        "placeholder": PLACEHOLDER,
    }
    return html, info


def write(html: str, *, force: bool = False) -> bool:
    """Ghi ra ui/_inline/index_inline.html. Trả True nếu file đổi."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = html.encode("utf-8")
    if not force and OUT_HTML.is_file() and OUT_HTML.read_bytes() == data:
        return False
    tmp = OUT_HTML.with_suffix(".html.tmp")
    tmp.write_bytes(data)
    tmp.replace(OUT_HTML)          # ghi nguyên tử: không để lại file dở dang
    return True


def build(*, force: bool = False, fonts: bool = True) -> dict:
    html, info = render(fonts=fonts)
    changed = write(html, force=force)
    info["changed"] = changed
    return info


def is_stale(*, fonts: bool = True) -> bool:
    """Bản sinh đã cũ so với ui/ chưa (so khớp byte tuyệt đối)?  False nếu thiếu file."""
    if not OUT_HTML.is_file():
        return True
    try:
        html, _ = render(fonts=fonts)
    except Exception:
        return True
    return OUT_HTML.read_bytes() != html.encode("utf-8")


def ensure_inline(*, fonts: bool = True) -> dict:
    """Bảo đảm có bản inline mới. Dùng từ app/views/giam_sat_node.py lúc import."""
    if is_stale(fonts=fonts):
        return build(fonts=fonts)
    return {"path": OUT_HTML, "changed": False,
            "size": OUT_HTML.stat().st_size, "sources": [], "skipped": [],
            "leftovers": [], "fonts": fonts, "placeholder": PLACEHOLDER}


# --------------------------------------------------------------------- CLI
def _utf8_stdout() -> None:
    """Console Windows mặc định cp1252 → in tiếng Việt sẽ ném UnicodeEncodeError.

    Không ép được code page của terminal, nhưng ép được encoding của luồng in.
    `errors="replace"` để không bao giờ chết vì một ký tự lạ.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):   # stream bị thay bằng StringIO (pytest)
            pass


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    ap = argparse.ArgumentParser(
        description="Nhúng CSS/JS/font của ui/ vào một file HTML duy nhất.")
    ap.add_argument("--force", action="store_true", help="ghi lại dù nội dung không đổi")
    ap.add_argument("--check", action="store_true",
                    help="không ghi; exit 1 nếu bản sinh đã cũ")
    ap.add_argument("--no-fonts", action="store_true",
                    help="không nhúng base64 font (file nhỏ hơn, font rơi về mặc định)")
    args = ap.parse_args(argv)

    fonts = not args.no_fonts
    if args.check:
        if not OUT_HTML.is_file():
            print(f"[check] THIẾU {OUT_HTML.relative_to(ROOT).as_posix()}", file=sys.stderr)
            return 1
        stale = is_stale(fonts=fonts)
        print(f"[check] {OUT_HTML.relative_to(ROOT).as_posix()} "
              f"{'ĐÃ CŨ — chạy lại build' if stale else 'mới nhất'}")
        return 1 if stale else 0

    info = build(force=args.force, fonts=fonts)
    rel_out = info["path"].relative_to(ROOT).as_posix()
    print(f"[ok] {rel_out} — {info['size']:,} byte "
          f"({info['size'] / 1024:.1f} KB)")
    print(f"     thay đổi: {'có' if info['changed'] else 'không (đã mới nhất)'}")
    print(f"     nhúng font base64: {'có' if info['fonts'] else 'không'}")
    print(f"     nguồn đã nhúng ({len(info['sources'])}): " + ", ".join(info["sources"]))
    for note in info["skipped"]:
        print(f"     [bỏ qua] {note}")
    for note in info["leftovers"]:
        print(f"     [cảnh báo] còn tham chiếu tương đối chưa nhúng: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
