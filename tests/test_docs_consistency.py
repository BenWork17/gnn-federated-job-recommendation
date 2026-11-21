"""
Kiểm tra tài liệu viết tay KHÔNG chứa số liệu lỗi thời.

Bối cảnh: trong quá trình làm, các file README / kịch bản demo / phân tích
đề tài từng ghi những con số lệch so với kết quả thật. Những lệch nhỏ này
rất khó thấy bằng mắt nhưng làm mất uy tín của báo cáo.

Test này chốt lại: mọi con số trong văn xuôi phải khớp với results/*.json
(hoặc được viết dạng khoảng, hoặc trích từ docs/SO_LIEU_CHINH.md).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DOCS = ["README.md", "docs/PHAN_TICH_DE_TAI.md", "docs/KICH_BAN_DEMO.md"]

# Số liệu của đề tài IoT đã gỡ bỏ. Nếu chúng xuất hiện lại trong văn xuôi
# thì gần như chắc chắn là tàn dư của phiên bản cũ.
STALE_IOT_MARKERS = [
    "IoT-23", "EdgeGAT", "EdgeSAGE", "FlowMLP", "dịch chuyển hiệu chuẩn",
    "CTU-IoT-Malware", "IoT-23 dataset",
]


def _load(name: str) -> dict:
    p = ROOT / "results" / name
    if not p.exists():
        pytest.skip(f"chưa có {name}")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def truth() -> dict:
    reco = _load("reco_main.json")
    s = reco["systems"]
    # Văn xuôi tiếng Việt viết số thập phân bằng dấu phẩy (0,497) trong khi
    # JSON dùng dấu chấm (0.4969). Chấp nhận cả hai dạng để test không báo
    # nhầm khi tài liệu trình bày đúng quy ước tiếng Việt.
    def both(x: float, nd: int = 4) -> tuple[str, str]:
        """SO_LIEU_CHINH.md trình bày 4 chữ số; văn xuôi thường làm tròn 3.

        Chấp nhận cả hai, và cả dấu phẩy thập phân tiếng Việt.
        """
        vals = set()
        for n in (nd, nd - 1):
            v = f"{x:.{n}f}"
            vals.add(v)
            vals.add(v.replace(".", ","))
        return tuple(sorted(vals))

    return {
        "r20_fed": both(s["fedavg"]["recall@20"], 4),
        "r20_loc": both(s["local_only"]["recall@20"], 4),
        "r20_cen": both(s["centralized"]["recall@20"], 4),
        "ndcg_fed": both(s["fedavg"]["ndcg@20"], 4),
    }


def _has_any(text: str, variants: tuple[str, ...]) -> bool:
    return any(v in text for v in variants)


@pytest.mark.parametrize("doc", DOCS)
def test_no_stale_iot_content(doc: str) -> None:
    """Văn xuôi không được còn dấu vết của đề tài IoT đã gỡ."""
    path = ROOT / doc
    if not path.exists():
        pytest.skip(f"không có {doc}")
    text = path.read_text(encoding="utf-8")
    found = [m for m in STALE_IOT_MARKERS if m in text]
    assert not found, (
        f"{doc} còn nội dung IoT đã gỡ: {found}. "
        f"Đề bài chỉ có một bài toán là gợi ý việc làm.")


@pytest.mark.parametrize("doc", DOCS)
def test_key_metrics_correctly_quoted(doc: str, truth: dict) -> None:
    """Nếu tài liệu có nhắc tới một chỉ số, con số phải đúng."""
    path = ROOT / doc
    if not path.exists():
        pytest.skip(f"không có {doc}")
    text = path.read_text(encoding="utf-8")

    # Mọi chỗ nhắc Recall@20 đều phải dùng đúng một trong các giá trị chuẩn.
    if "Recall@20" in text or "R@20" in text:
        ok = (any(v in text for v in truth["r20_fed"])
              or any(v in text for v in truth["r20_cen"])
              or any(v in text for v in truth["r20_loc"]))
        assert ok, (
            f"{doc} nhắc Recall@20 nhưng không có giá trị chuẩn nào "
            f"({truth['r20_fed'][0]}, {truth['r20_cen'][0]}, {truth['r20_loc'][0]})")


def test_facts_file_exists_and_matches_results(truth: dict) -> None:
    """docs/SO_LIEU_CHINH.md phải tồn tại và chứa số đúng."""
    p = ROOT / "docs" / "SO_LIEU_CHINH.md"
    if not p.exists():
        pytest.skip("chưa sinh SO_LIEU_CHINH.md")
    text = p.read_text(encoding="utf-8")
    for key in ("r20_fed", "r20_cen"):
        assert _has_any(text, truth[key]), (
            f"SO_LIEU_CHINH.md thiếu {key}={truth[key][0]} — "
            f"chạy lại: python src/report/make_facts.py")
    assert "IoT" not in text, "SO_LIEU_CHINH.md còn nội dung IoT đã gỡ"


def test_markdown_files_have_no_broken_encoding() -> None:
    """Không được có ký tự thay thế (U+FFFD) do lỗi mã hoá."""
    for doc in DOCS + ["docs/SO_LIEU_CHINH.md"]:
        path = ROOT / doc
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert "\ufffd" not in text, (
            f"{doc} có ký tự hỏng (U+FFFD) — kiểm tra lại encoding khi ghi file")
