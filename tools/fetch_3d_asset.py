"""Tải bundle `3d-force-graph` vào app/assets/ (chạy MỘT lần, cần mạng).

Vì sao cần script riêng thay vì tải trong lúc chạy app: app phải hoạt động
offline khi bảo vệ (yêu cầu trong README). Nên file JS được tải sẵn một lần
rồi commit vào repo.

Vì sao dùng urllib chứ không phải PowerShell `Invoke-WebRequest`: trên máy
phát triển, `Invoke-WebRequest` hỏng TLS với jsdelivr, còn `urllib` thì được.
Ghi lại để người chạy lại không mất thời gian dò.

Chạy:  python tools/fetch_3d_asset.py
"""

from __future__ import annotations

import hashlib
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "app" / "assets" / "3d-force-graph.min.js"

VERSION = "1.73.4"
URLS = [
    f"https://cdn.jsdelivr.net/npm/3d-force-graph@{VERSION}/dist/3d-force-graph.min.js",
    f"https://unpkg.com/3d-force-graph@{VERSION}/dist/3d-force-graph.min.js",
]


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)

    if DEST.exists():
        size = DEST.stat().st_size
        print(f"đã có: {DEST.relative_to(ROOT)} ({size/1024:.0f} KB) — bỏ qua")
        return 0

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    last_err: Exception | None = None
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=90, context=ctx).read()
        except Exception as e:          # noqa: BLE001 — thử URL kế tiếp
            last_err = e
            print(f"lỗi khi tải {url}: {type(e).__name__}: {e}")
            continue

        if len(data) < 200_000:
            last_err = ValueError(f"tải được nhưng quá nhỏ ({len(data)} byte)")
            print(f"nghi ngờ: {url} chỉ trả {len(data)} byte")
            continue

        DEST.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()[:16]
        print(f"OK: {DEST.relative_to(ROOT)}")
        print(f"    {len(data)/1024:.0f} KB · sha256:{digest}… · từ {url}")
        return 0

    print(f"THẤT BẠI: không tải được bundle. Lỗi cuối: {last_err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
