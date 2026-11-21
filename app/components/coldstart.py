"""Gợi ý cho một hồ sơ ứng viên MỚI, nhập tay ngay trên giao diện.

Vì sao không train lại mô hình cho hồ sơ mới
============================================
LightGCN học embedding theo node id. Một ứng viên mới **không có node** trong
`graph.npz` (đồ thị đã dựng cố định từ dữ liệu huấn luyện), nên không thể lấy
embedding của người đó. Hai lựa chọn đúng:

  1. **Lạnh (cold-start) bằng nội dung** — so khớp kỹ năng bằng TF-IDF cosine,
     đúng như `skill_cbf_scores` đang dùng cho baseline. Chọn cách này.
  2. Học embedding cho người mới từ các tương tác đầu tiên (online learning) —
     cần dữ liệu tương tác thật, không có trong demo.

Nên phần này trung thực ghi rõ: đây là **content-based cold-start**, không
phải GNN. Nó trả lời đúng câu "tôi có kỹ năng này thì nên ứng tuyển đâu",
không phải "mô hình GNN nghĩ gì".

Vì sao vẫn có ích cho đồ án
==========================
- Cho người xem **tự tay** nhập một hồ sơ và thấy kết quả đổi ngay — thuyết
  phục hơn xem danh sách ứng viên dựng sẵn.
- Là bằng chứng cho phần "hướng phát triển": muốn phục vụ người dùng mới thật
  thì cần thêm bước học embedding trực tuyến, đã ghi trong báo cáo.

Lưu ý về hiệu năng: ma trận TF-IDF của 1.014 tin được cache một lần
(`@st.cache_data`), mỗi lần đổi kỹ năng chỉ nhân một vector — vài ms.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from src.medajob.models import skill_cbf_scores


def all_skills(jobs: pd.DataFrame) -> list[str]:
    """Toàn bộ kỹ năng xuất hiện trong tin tuyển dụng, sắp theo độ phổ biến.

    Dùng để gợi ý trong ô multiselect, và để chuẩn hoá chữ thường.
    """
    counts: dict[str, int] = {}
    for s in jobs["skills"].fillna(""):
        for tok in str(s).split("|"):
            tok = tok.strip()
            if tok:
                counts[tok] = counts.get(tok, 0) + 1
    return [k for k, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def _job_skill_lists(jobs: pd.DataFrame) -> list[list[str]]:
    return [[t.strip() for t in str(s).split("|") if t.strip()]
            for s in jobs["skills"].fillna("")]


def score_profile(
    jobs: pd.DataFrame,
    profile_skills: list[str],
    *,
    top_k: int = 10,
    min_match: int = 1,
) -> pd.DataFrame:
    """Xếp hạng tin cho một hồ sơ mới dựa trên kỹ năng.

    Trả về DataFrame với cột: hạng, tiêu đề, công ty, ngành, địa điểm,
    điểm khớp, kỹ năng chung, số kỹ năng khớp.
    """
    profile = [s.strip().lower() for s in profile_skills if s and s.strip()]
    if not profile:
        return pd.DataFrame()

    job_lists = _job_skill_lists(jobs)
    # chuẩn hoá chữ thường để "Python" và "python" là một
    job_lists_lc = [[t.lower() for t in lst] for lst in job_lists]

    # TF-IDF cosine giữa hồ sơ mới và toàn bộ tin — dùng lại hàm của pipeline
    sims = skill_cbf_scores(job_lists_lc, [profile])[0]

    common = [len(set(profile) & set(lst)) for lst in job_lists_lc]

    df = pd.DataFrame({
        "điểm khớp": sims.astype(float),
        "số kỹ năng khớp": common,
        "tiêu đề": jobs["job_title"].astype(str).str.slice(0, 70),
        "công ty": jobs["company_name"].astype(str).str.slice(0, 28),
        "ngành": jobs["industry"].astype(str),
        "địa điểm": jobs["job_location"].astype(str).str.slice(0, 18),
        "kỹ năng chung": [
            ", ".join(sorted(set(profile) & set(lst))[:6]) or "—"
            for lst in job_lists_lc
        ],
    })

    df = df[df["số kỹ năng khớp"] >= max(1, min_match)]
    if df.empty:
        return df

    df = df.sort_values(["số kỹ năng khớp", "điểm khớp"],
                        ascending=False).head(top_k)
    df.insert(0, "hạng", range(1, len(df) + 1))
    return df.reset_index(drop=True)
