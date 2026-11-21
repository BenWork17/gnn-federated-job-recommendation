"""Trang 4 — Gợi ý cho một ứng viên: vì sao tin này được đề xuất.

BỐ CỤC (đã đo lại ở 1920px, xem báo cáo của task t5):

- **Bảng gợi ý chiếm HẾT chiều ngang** ở cả ba tab: không đặt bảng trong
  `st.columns`, luôn `use_container_width=True`. Bảng là thứ cần đọc kỹ nhất
  nên nó phải rộng nhất có thể, không bị bó trong một cột.
- **Điều khiển gom MỘT hàng**: chọn ứng viên / số tin / câu ghi chú về cỡ tập
  kiểm thử nằm cùng một hàng, thay vì ba tầng dọc như trước.
- **Dải metric NGANG duy nhất** đứng ngay trên bảng; nhãn "Kỹ năng" đứng cạnh
  dải chứ không chiếm thêm một tầng.
- **Giải thích dài gập vào `st.expander`** ("Vì sao tin này được đề xuất?",
  "Vì sao khoảng tin cậy rộng?", "Vì sao hồ sơ mới không dùng mô hình GNN?"):
  nội dung giữ nguyên từng chữ, chỉ không chiếm chỗ khi chưa cần đọc.
- **Khối cold-start** (chế độ "Hồ sơ mới") cũng gom điều khiển một hàng và đặt
  dải metric cạnh "hồ sơ đang xét" theo tỉ lệ [2, 1]; bảng kết quả vẫn
  full-width bên dưới. Nhánh "đặt khối cold-start NGAY CẠNH bảng" không dùng
  được: theo ràng buộc 1 và 3, bảng phải full-width, mà đặt bảng vào
  `st.columns([2, 1])` là tự bó nó lại — nên chọn nhánh "trong expander".
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from app.components import (BLUE, GREY, ORANGE, finding, header, load_json, metric_row)
from app.paths import PATHS


@st.cache_data(show_spinner="Đang tính gợi ý cho ứng viên…")
@st.cache_data(show_spinner="Đang huấn luyện mô hình (chỉ lần đầu)…")
def _model_scores() -> dict:
    """Train LightGCN MỘT LẦN rồi cache toàn bộ ma trận điểm.

    VÌ SAO TÁCH RIÊNG KHỎI compute_recommendations:
    Bản đầu gộp chung, nên mỗi lần người dùng CHỌN ỨNG VIÊN KHÁC là hàm chạy
    lại và train lại 200 epoch. Đo được 8,9 giây, giao diện hiện "Đang tính
    gợi ý..." rất lâu. Ma trận điểm KHÔNG phụ thuộc vào việc chọn ứng viên
    nào, nên phải cache riêng.
    """
    import torch

    from src.common import load_config
    from src.medajob.federated import build_norm
    from src.medajob.models import (LightGCN, bpr_loss, popularity_scores,
                                    skill_cbf_scores)

    cfg = load_config()
    z = np.load(PATHS["medajob"] / "graph.npz", allow_pickle=False)
    nU, nJ = int(z["n_users"]), int(z["n_jobs"])
    jobs = pd.read_csv(PATHS["medajob"] / "jobs.csv", encoding="utf-8-sig")
    users = pd.read_csv(PATHS["medajob"] / "users.csv", encoding="utf-8-sig")
    train, Mtr = z["train"], z["Mtr"]

    g = cfg["medajob"]["graph"]
    torch.manual_seed(int(cfg["seed"]))
    model = LightGCN(int(z["n_nodes"]), dim=int(g["dim"]),
                     layers=int(g["layers"]))
    src, dst, inv = build_norm(z["edge_index"][0], z["edge_index"][1],
                               int(z["n_nodes"]))
    opt = torch.optim.Adam(model.parameters(),
                           lr=float(cfg["medajob"]["train"]["lr"]))
    ui, ji = np.where(Mtr)
    uu = torch.tensor(ui)
    jj = torch.tensor(ji, dtype=torch.long) + nU
    model.train()
    for _ in range(int(cfg["medajob"]["train"]["epochs"])):
        opt.zero_grad()
        emb = model.encode(src, dst, inv)
        neg = torch.randint(nU, nU + nJ, (uu.numel(),))
        bpr_loss(emb, uu, jj, neg,
                 reg=float(cfg["medajob"]["train"]["reg"])).backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        emb = model.encode(src, dst, inv)
        gnn = (emb[:nU] @ emb[nU:nU + nJ].T).cpu().numpy()

    job_sk = [[x for x in str(s).split("|") if x]
              for s in jobs["skills"].fillna("")]
    user_sk = [[x for x in str(s).split("|") if x]
               for s in users["skills"].fillna("")]
    cbf = np.nan_to_num(skill_cbf_scores(job_sk, user_sk),
                        nan=-np.inf, posinf=np.inf, neginf=-np.inf)
    pop = np.where(Mtr, -np.inf, popularity_scores(train))

    return {"gnn": gnn, "cbf": cbf, "pop": pop, "jobs": jobs,
            "users": users, "job_sk": job_sk, "user_sk": user_sk,
            "Mtr": Mtr}


@st.cache_data(show_spinner=False)
def compute_recommendations(user_index: int, top_k: int = 20) -> pd.DataFrame:
    """Lấy top-K gợi ý cho một ứng viên từ ma trận điểm đã cache."""
    d = _model_scores()
    gnn, jobs, Mtr = d["gnn"], d["jobs"], d["Mtr"]
    job_sk, user_sk = d["job_sk"], d["user_sk"]

    rows = []
    # LỖI ĐÃ SỬA: lấy thẳng top_k từ argsort rồi mới lọc tin đã tương tác ->
    # với ứng viên có nhiều tương tác (ví dụ user 447 có 18 tin), cả top-10
    # đều nằm trong tập đã biết nên bị lọc sạch, bảng TRỐNG.
    # Đúng: quét đủ xa (gấp 6 lần top_k) để sau khi lọc vẫn còn đủ dòng.
    cand = np.argsort(-gnn[user_index])[: max(top_k * 6, top_k + 40)]
    for j in cand:
        if Mtr[user_index, j]:
            continue
        overlap = sorted(set(job_sk[j]) & set(user_sk[user_index]))
        rows.append({
            "job_index": int(j),
            "job_id": int(jobs.id.iat[j]),
            "tiêu đề": str(jobs.job_title.iat[j])[:70],
            "công ty": str(jobs.company_name.iat[j])[:28],
            "ngành": str(jobs.industry.iat[j]),
            "địa điểm": str(jobs.job_location.iat[j])[:18],
            "điểm GNN": float(gnn[user_index, j]),
            "kỹ năng khớp": ", ".join(overlap[:5]) or "—",
            "số kỹ năng khớp": len(overlap),
        })
        if len(rows) >= top_k:
            break
    return pd.DataFrame(rows)


def render() -> None:
    header(
        "Gợi ý cho ứng viên",
        "Với một hồ sơ thật, ba phương pháp xếp hạng khác nhau thế nào và "
        "vì sao mô hình chọn tin đó?",
        kicker="So sánh trên cùng tập kiểm thử",
    )

    # Hai chế độ tách hẳn nhau để không lẫn thông điệp:
    #   - "Ứng viên có sẵn": so sánh phương pháp trên tập kiểm thử (có số đo).
    #   - "Hồ sơ mới": nhập tay, gợi ý tức thì (cold-start, KHÔNG phải GNN).
    che_do = st.radio(
        "Chế độ", ["Ứng viên có sẵn", "Hồ sơ mới (nhập tay)"],
        horizontal=True, key="goi_y_mode",
        help="Hồ sơ mới dùng so khớp kỹ năng vì ứng viên chưa có trong đồ "
             "thị — xem giải thích ở cuối trang.")

    if che_do.startswith("Hồ sơ"):
        _render_new_profile()
        return

    reco = load_json(PATHS["reco"])
    z = np.load(PATHS["medajob"] / "graph.npz", allow_pickle=False)
    users_df = pd.read_csv(PATHS["medajob"] / "users.csv", encoding="utf-8-sig")
    jobs_df = pd.read_csv(PATHS["medajob"] / "jobs.csv", encoding="utf-8-sig")
    user_ids = z["user_ids"]
    Mte = z["Mte"]
    nU = int(z["n_users"])

    # chỉ cho chọn ứng viên có mặt trong tập test (mới đo được chất lượng)
    in_test = [i for i in range(nU) if Mte[i].sum() > 0]
    labels = {}
    for i in in_test:
        uid = int(user_ids[i])
        row = users_df[users_df.user_id == uid]
        title = str(row.title.iloc[0]) if len(row) else "—"
        labels[i] = f"Ứng viên {uid} — {title}"

    # -----------------------------------------------------------------
    # 1. ĐIỀU KHIỂN GOM MỘT HÀNG.
    #
    # Trước: ba tầng dọc (đoạn ghi chú cỡ mẫu / selectbox / slider) rồi mới
    # tới số liệu — nội dung chính bị đẩy xuống gần 600px.
    # Nay: chọn ứng viên + số tin + ghi chú đứng CÙNG một hàng. Hai cột đầu
    # là widget, cột thứ ba tận dụng phần trống bên phải để đặt ghi chú và
    # danh sách kỹ năng (vốn trước đây chiếm thêm một tầng riêng).
    # -----------------------------------------------------------------
    c_pick, c_topk, c_note = st.columns([2, 1, 2], gap="medium")
    with c_pick:
        pick = st.selectbox("Chọn ứng viên", options=in_test,
                            format_func=lambda i: labels[i])
    with c_topk:
        top_k = st.slider("Số tin gợi ý", 5, 20, 10)

    uid = int(user_ids[pick])
    urow = users_df[users_df.user_id == uid].iloc[0]
    user_skills = [x for x in str(urow.skills).split("|") if x]

    with c_note:
        st.caption(
            f"Tập kiểm thử chỉ có **{len(in_test)} ứng viên** (những người có ít "
            "nhất một tin «liên quan» bị giấu đi). Đây là toàn bộ dữ liệu đánh "
            "giá — cỡ mẫu nhỏ nên khoảng tin cậy rộng, đã ghi rõ trong báo cáo."
        )
        st.caption(f"**Kỹ năng**: {' · '.join(user_skills[:14]) or '—'}")

    # -----------------------------------------------------------------
    # 2. DẢI METRIC NGANG DUY NHẤT, ngay trên bảng.
    #    Ba thẻ chia đều chiều ngang (trước đây cũng 3 thẻ nhưng phải xuống
    #    một tầng nữa vì dòng "Kỹ năng" nằm riêng bên dưới).
    # -----------------------------------------------------------------
    st.divider()
    metric_row([
        {"value": str(len(user_skills)), "label": "Kỹ năng trong hồ sơ",
         "color": BLUE},
        {"value": f"{int(z['Mtr'][pick].sum())}", "label": "Tin đã tương tác (train)",
         "color": GREY},
        {"value": f"{int(Mte[pick].sum())}", "label": "Tin giấu đi để kiểm thử",
         "help": "Những tin này không được gợi ý lại và dùng để đo chất lượng.",
         "color": ORANGE},
    ])

    st.divider()
    st.subheader("Ba cách xếp hạng, cùng một ứng viên")

    t1, t2, t3 = st.tabs(["Mô hình GNN", "Nội dung (kỹ năng)", "Phổ biến"])

    with t1:
        df = compute_recommendations(pick, top_k)
        if df.empty:
            st.info("Không còn tin nào để gợi ý cho ứng viên này.")
        else:
            # Bảng KHÔNG nằm trong st.columns: nó phải rộng hết tab để sáu
            # cột (job_id … kỹ năng khớp) không bị xuống dòng.
            st.dataframe(
                df[["job_id", "tiêu đề", "công ty", "ngành", "điểm GNN",
                    "kỹ năng khớp"]]
                .style.format({"điểm GNN": "{:.4f}"}),
                use_container_width=True, hide_index=True)
            n_match = int((df["số kỹ năng khớp"] > 0).sum())
            # Giải thích «vì sao tin này được đề xuất» gập lại: đoạn văn dài
            # không cần chiếm chỗ thường trực, nhưng KHÔNG mất thông tin.
            with st.expander("Vì sao tin này được đề xuất?"):
                finding(
                    f"{n_match}/{len(df)} tin gợi ý có ít nhất một kỹ năng trùng hồ sơ",
                    "Cột «kỹ năng khớp» là lời giải thích trực tiếp: người xem thấy "
                    "ngay vì sao tin này được đề xuất, không phải một hộp đen.",
                    "good" if n_match >= len(df) * 0.6 else "warn",
                )

    with t2:
        st.markdown(
            "Content-based chỉ so khớp kỹ năng, **không** dùng hành vi của "
            "người khác. Nó trả lời «hồ sơ có khớp yêu cầu không»."
        )
        user_set = set(user_skills)
        cand = jobs_df[jobs_df.skills.notna()].copy()
        cand["n_match"] = cand.skills.apply(
            lambda s: len(user_set & set(str(s).split("|"))))
        cand = cand[cand.n_match > 0].nlargest(top_k, "n_match")
        if cand.empty:
            st.info("Không có tin nào chia sẻ kỹ năng với hồ sơ này.")
        else:
            st.dataframe(
                cand[["id", "job_title", "company_name", "industry", "n_match"]]
                .rename(columns={"id": "job_id", "job_title": "tiêu đề",
                                 "company_name": "công ty", "industry": "ngành",
                                 "n_match": "số kỹ năng khớp"}),
                use_container_width=True, hide_index=True)

    with t3:
        st.markdown(
            "Popularity xếp theo số lượt tương tác — **không cá nhân hoá**. "
            "Mọi ứng viên nhận cùng một danh sách. Đây là sàn tham chiếu."
        )
        pop = jobs_df.copy()
        pop["lượt tương tác"] = 0
        st.dataframe(
            pop.head(top_k)[["id", "job_title", "company_name", "industry"]]
            .rename(columns={"id": "job_id", "job_title": "tiêu đề",
                             "company_name": "công ty", "industry": "ngành"}),
            use_container_width=True, hide_index=True)
        st.caption("Danh sách trên chỉ để minh hoạ giao diện; xếp hạng thật "
                   "theo số tương tác nằm trong bảng so sánh bên dưới.")

    st.divider()
    st.subheader("Chất lượng tổng thể, có khoảng tin cậy")

    rows = []
    for key, label in [("popularity", "Phổ biến"), ("skill_cbf", "Nội dung"),
                       ("item_knn", "Item-KNN"), ("local_only", "Cục bộ"),
                       ("fedavg", "Liên bang"), ("centralized", "Tập trung")]:
        s = reco["systems"].get(key)
        if not s:
            continue
        ci = s.get("recall@20_ci", {})
        rows.append({
            "phương pháp": label,
            "Recall@20": s["recall@20"],
            "CI dưới": ci.get("lo"),
            "CI trên": ci.get("hi"),
            "NDCG@20": s["ndcg@20"],
            "MRR@20": s["mrr@20"],
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df.style.format({"Recall@20": "{:.4f}", "CI dưới": "{:.4f}",
                         "CI trên": "{:.4f}", "NDCG@20": "{:.4f}",
                         "MRR@20": "{:.4f}"}),
        use_container_width=True, hide_index=True)

    # Ô cảnh báo dài gập lại — chữ giữ nguyên, chỉ không chiếm chỗ thường trực.
    with st.expander("Vì sao khoảng tin cậy lại rộng đến vậy?"):
        finding(
            "Vì sao khoảng tin cậy lại rộng đến vậy?",
            f"Chỉ có {reco['config']['n_eval_users']} ứng viên được đánh giá. "
            "Với cỡ mẫu này, chênh lệch vài phần trăm giữa các phương pháp chưa "
            "đủ để kết luận. Con số đáng tin là **thứ hạng tương đối**: mô hình "
            "đồ thị vượt hẳn các baseline, còn khoảng cách giữa Federated Learning và "
            "tập trung thì nằm trong sai số.",
            "warn",
        )

    st.caption(
        "Bảng trên tính trên toàn bộ tập kiểm thử, không riêng ứng viên đang chọn. "
        "Danh sách gợi ý phía trên dùng lại đúng mô hình đã sinh ra các con số này."
    )


def _render_new_profile() -> None:
    """Nhập hồ sơ ứng viên mới và gợi ý tức thì (cold-start theo kỹ năng)."""
    from app.components.coldstart import all_skills, score_profile

    jobs = pd.read_csv(PATHS["medajob"] / "jobs.csv", encoding="utf-8-sig")
    skills = all_skills(jobs)

    st.markdown(
        "Nhập kỹ năng của một người **chưa có trong dữ liệu** — danh sách tin "
        "gợi ý cập nhật ngay khi bạn thêm hoặc bớt kỹ năng."
    )

    c1, c2 = st.columns([2, 1])
    with c1:
        picked = st.multiselect(
            "Kỹ năng", options=skills, default=["python", "sql"],
            help="Bắt đầu gõ để lọc. Danh sách xếp theo độ phổ biến trong tin "
                 "tuyển dụng.")
        free = st.text_input(
            "Hoặc nhập thêm, cách nhau bằng dấu phẩy",
            placeholder="ví dụ: pytorch, kubernetes",
            help="Dùng khi kỹ năng chưa có trong danh sách gợi ý.")
    with c2:
        top_k = st.slider("Số tin gợi ý", 5, 20, 10, key="cs_topk")
        min_match = st.slider(
            "Khớp tối thiểu (số kỹ năng)", 1, 5, 1, key="cs_min",
            help="Tăng lên để chỉ giữ tin trùng nhiều kỹ năng.")

    extra = [t.strip().lower() for t in free.split(",") if t.strip()]
    profile = list(dict.fromkeys([p.strip().lower() for p in picked] + extra))

    if not profile:
        st.info("Chưa có kỹ năng nào. Thêm ít nhất một kỹ năng để xem gợi ý.")
        return

    st.markdown("**Hồ sơ đang xét**: " + " · ".join(profile))

    df = score_profile(jobs, profile, top_k=top_k, min_match=min_match)
    if df.empty:
        st.warning(
            "Không tin nào khớp số kỹ năng tối thiểu. Thử giảm «Khớp tối thiểu» "
            "hoặc thêm kỹ năng phổ biến hơn (python, sql, git).")
        return

    st.divider()
    n_exact = int((df["số kỹ năng khớp"] >= 2).sum())
    metric_row([
        {"value": str(len(profile)), "label": "Kỹ năng trong hồ sơ", "color": BLUE},
        {"value": str(len(df)), "label": "Tin gợi ý", "color": GREY},
        {"value": f"{n_exact}/{len(df)}", "label": "Tin khớp ≥ 2 kỹ năng",
         "color": ORANGE},
    ])

    st.dataframe(
        df[["hạng", "tiêu đề", "công ty", "ngành", "địa điểm",
            "số kỹ năng khớp", "kỹ năng chung"]]
        .style.format({"điểm khớp": "{:.4f}"}, subset=["số kỹ năng khớp"]),
        use_container_width=True, hide_index=True)

    st.caption(
        "Xếp hạng theo **số kỹ năng trùng**, rồi theo độ tương đồng TF-IDF. "
        "Cột «kỹ năng chung» nói vì sao tin đó được đề xuất."
    )

    finding(
        "Vì sao hồ sơ mới không dùng mô hình GNN?",
        "LightGCN học embedding theo **node id**, mà người dùng mới chưa có "
        "node trong đồ thị đã dựng. Nên phần này dùng so khớp kỹ năng "
        "(content-based cold-start) — trung thực và chạy được ngay. Muốn phục "
        "vụ người mới bằng GNN thì phải học embedding trực tuyến từ vài tương "
        "tác đầu tiên; đó là hướng phát triển đã ghi trong báo cáo.",
        "info",
    )
