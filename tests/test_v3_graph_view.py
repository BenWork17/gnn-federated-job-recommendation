"""Automated tests for V3 full-graph engine, ID-based renderer wiring, and upgraded UI."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / ".mplcache"))
sys.path.insert(0, str(ROOT))

from app.components import _graph_payload_2d
from app.components.graph3d import _payload as _payload_3d, graph_html_3d
from app.components.v3_graph import (
    EDGE_PRIVATE,
    EDGE_PUBLIC,
    KIND_JOB,
    KIND_OCC,
    KIND_SKILL,
    KIND_USER,
    _load_onet_occ_titles,
    extract_ego_subgraph,
    extract_silo_subgraph,
    layout_subgraph_to_dfs,
    load_v3_index,
    search_all_nodes,
)


@pytest.fixture(scope="module")
def v3_index():
    return load_v3_index()


@pytest.fixture(scope="module")
def v3_raw():
    v3_dir = ROOT / "artifacts" / "v3"
    z = np.load(v3_dir / "graph.npz", allow_pickle=False)
    clients = json.loads((v3_dir / "clients.json").read_text(encoding="utf-8"))
    job_titles = json.loads((v3_dir / "job_titles.json").read_text(encoding="utf-8"))
    user_titles = json.loads((v3_dir / "user_titles.json").read_text(encoding="utf-8"))
    return z, clients, job_titles, user_titles


# =====================================================================
# AC1 — Engine & Silo Nhà tuyển dụng
# =====================================================================
def test_v3_index_loads_full_corpus(v3_index, v3_raw) -> None:
    z, clients, job_titles, user_titles = v3_raw
    assert v3_index.n_nodes == int(z["n_nodes"]) == 264_995
    assert v3_index.n_users == 171_807
    assert v3_index.n_jobs == 84_845
    assert v3_index.n_occupations == 583
    assert v3_index.n_skills == 7_760
    assert len(v3_index.clients) == len(clients) == 9_116
    assert len(v3_index.job_meta) == len(job_titles) == 84_845
    assert len(v3_index.user_meta) == len(user_titles) == 156_189
    assert len(v3_index.search_texts) == 264_995
    # Optional O*NET zip fallback check
    assert _load_onet_occ_titles(ROOT / "nonexistent_onet.zip") == {}


def test_extract_silo_randstad_and_allmedstaffing(v3_index, v3_raw) -> None:
    z, clients, job_titles, user_titles = v3_raw
    client_of_job = z["client_of_job"]

    # randstad (cid=0) & allmedstaffing.com (cid=1)
    for cid, expected_name in [(0, "randstad"), (1, "allmedstaffing.com")]:
        c_info = clients[cid]
        assert c_info["employer_name"] == expected_name

        sub = extract_silo_subgraph(v3_index, cid)
        stats = sub["stats"]
        assert stats["n_jobs"] == c_info["n_jobs"]
        assert stats["n_users"] == c_info["n_users"]
        assert stats["n_apps"] == c_info["n_apps"]
        assert stats["n_private"] == stats["n_apps"]
        assert stats["n_public"] > 0

        # Mọi nút Tin tuyển dụng đều phải thuộc đúng client_of_job == cid
        job_nodes = [n for n in sub["nodes"] if n["kind"] == KIND_JOB]
        assert len(job_nodes) == c_info["n_jobs"]
        for jn in job_nodes:
            j_local = jn["nid"] - v3_index.off_job
            assert int(client_of_job[j_local]) == cid
            j_info = job_titles[jn["raw_id"]]
            assert j_info["employer"] == expected_name
            assert j_info["title"][:30] in jn["label"]

        # Kiểm tra nhãn Ứng viên khớp user_titles.json (hoặc fallback hợp lệ)
        user_nodes = [n for n in sub["nodes"] if n["kind"] == KIND_USER]
        assert len(user_nodes) == c_info["n_users"]
        for un in user_nodes[:100]:
            uid = un["raw_id"]
            if uid in user_titles and user_titles[uid].get("title"):
                assert user_titles[uid]["title"][:25] in un["label"]
            else:
                assert un["label"] == f"Ứng viên #{uid}"

        # Kiểm tra cạnh Silo chỉ gồm et in {0, 1, 2} và phân loại Công khai / Riêng tư
        for u, v, et_val, kind_str in sub["edges"]:
            assert et_val in (0, 1, 2)
            assert kind_str == (EDGE_PUBLIC if et_val in (1, 2) else EDGE_PRIVATE)


def test_extract_silo_zero_occupation_handled_cleanly(v3_index) -> None:
    # Silo cid=2 (webhrdept.com) có 0 nghề O*NET và 0 kỹ năng
    sub = extract_silo_subgraph(v3_index, 2)
    stats = sub["stats"]
    assert stats["client"]["employer_name"] == "webhrdept.com"
    assert stats["n_jobs"] == 104
    assert stats["n_users"] == 1364
    assert stats["n_occs"] == 0
    assert stats["n_skills"] == 0
    assert stats["n_public"] == 0
    assert stats["n_private"] == 1531

    # Lọc sang Nghề O*NET trên silo 0 nghề phải trả DataFrame rỗng không lỗi
    ndf, edf, meta = layout_subgraph_to_dfs(sub, dim=2, kind_filter=KIND_OCC)
    assert ndf.empty and edf.empty
    assert meta["n_nodes_rendered"] == 0


# =====================================================================
# AC2 — Tìm kiếm 264.995 nút (5 loại) & Ego-graph 1–2 hop
# =====================================================================
def test_search_all_nodes_five_query_types(v3_index, v3_raw) -> None:
    z, _, job_titles, user_titles = v3_raw

    # 1. Nghề O*NET (theo mã SOC và tên nghề nếu có zip)
    occ_code_hits = search_all_nodes(v3_index, "13-1199", kind_filter=KIND_OCC)
    assert occ_code_hits and occ_code_hits[0]["raw_id"] == "13-1199"
    if v3_index.occ_titles:
        occ_name_hits = search_all_nodes(v3_index, "Chief Executives", kind_filter=KIND_OCC)
        assert any(h["raw_id"] == "11-1011" for h in occ_name_hits)

    # 2. Kỹ năng
    sk_hits = search_all_nodes(v3_index, "Python", kind_filter=KIND_SKILL)
    assert sk_hits and sk_hits[0]["raw_id"] == "Python"

    # 3. Tiêu đề việc làm / Job ID
    jid_hits = search_all_nodes(v3_index, "40", kind_filter=KIND_JOB)
    assert any(h["raw_id"] == "40" for h in jid_hits)
    jtitle_hits = search_all_nodes(v3_index, "Administrative Assistant", kind_filter=KIND_JOB)
    assert len(jtitle_hits) > 0
    assert any("Administrative Assistant" in job_titles[h["raw_id"]]["title"] for h in jtitle_hits)

    # 4. Nhà tuyển dụng
    emp_hits = search_all_nodes(v3_index, "allmedstaffing.com", limit=20)
    assert len(emp_hits) > 0
    assert any(h["client_id"] == 1 for h in emp_hits)

    # 5. ID ứng viên (cả có trong user_titles.json và thiếu trong user_titles.json)
    mapped_hits = search_all_nodes(v3_index, "47", kind_filter=KIND_USER)
    assert any(h["raw_id"] == "47" and "Passenger Screener" in h["label"] for h in mapped_hits)

    missing_uid = next(str(u) for u in z["user_ids"] if str(u) not in user_titles)
    unmapped_hits = search_all_nodes(v3_index, missing_uid, kind_filter=KIND_USER)
    assert unmapped_hits and unmapped_hits[0]["raw_id"] == missing_uid
    assert unmapped_hits[0]["label"] == f"Ứng viên #{missing_uid}"


def test_extract_ego_subgraph_1_and_2_hop_and_expand(v3_index, v3_raw) -> None:
    z, _, _, _ = v3_raw
    ei = z["edge_index"]
    et = z["edge_type"]
    edge_lookup: dict[tuple[int, int], int] = {}
    for a, b, t in zip(ei[0].tolist(), ei[1].tolist(), et.tolist()):
        key = (a, b) if a < b else (b, a)
        edge_lookup[key] = int(t)

    # Job 17361: 1-hop = 209 nodes, 2-hop = 600 nodes (vừa đủ test uncapped chính xác)
    job_nid = v3_index.jid_to_node["17361"]
    ego1 = extract_ego_subgraph(v3_index, job_nid, hops=1, max_nodes=None)
    assert ego1["stats"]["n_nodes"] == int(v3_index.deg[job_nid]) + 1
    assert all(n["hop"] <= 1 for n in ego1["nodes"])

    ego2 = extract_ego_subgraph(v3_index, job_nid, hops=2, max_nodes=None)
    assert ego2["stats"]["n_nodes"] >= ego1["stats"]["n_nodes"]
    assert all(n["hop"] <= 2 for n in ego2["nodes"])

    # Mọi cạnh trả về phải tồn tại thật trong graph.npz với nhãn Công khai/Riêng tư chuẩn
    for u, v, et_val, kind_str in ego2["edges"]:
        key = (u, v) if u < v else (v, u)
        assert edge_lookup.get(key) == et_val
        assert kind_str == (EDGE_PUBLIC if et_val in (1, 2) else EDGE_PRIVATE)

    # Mở rộng láng giềng (extra_nids) quanh 1 nút láng giềng của Python
    py_nid = v3_index.skill_to_node["python"]
    py_ego1 = extract_ego_subgraph(v3_index, py_nid, hops=1, max_nodes=None)
    neighbor_nid = next(n["nid"] for n in py_ego1["nodes"] if n["nid"] != py_nid)
    py_expanded = extract_ego_subgraph(
        v3_index, py_nid, hops=1, extra_nids=[neighbor_nid], max_nodes=None,
    )
    assert py_expanded["stats"]["n_nodes"] >= py_ego1["stats"]["n_nodes"]

    # Hub cap check trên Microsoft Excel 2-hop (168.675 nút nếu không giới hạn)
    excel_nid = v3_index.skill_to_node["microsoft excel"]
    excel_capped = extract_ego_subgraph(v3_index, excel_nid, hops=2, max_nodes=300)
    assert excel_capped["truncated"] is True
    assert excel_capped["stats"]["n_nodes"] == 300
    assert excel_capped["total_unfiltered_nodes"] > 100_000


def test_extract_ego_hub_extra_nids_adds_neighbors_under_cap(v3_index) -> None:
    """Mở rộng láng giềng trên nút hub (deg >= max_nodes) vẫn phải thêm nút mới."""
    excel_nid = v3_index.skill_to_node["microsoft excel"]
    for hops in (1, 2):
        base = extract_ego_subgraph(v3_index, excel_nid, hops=hops, max_nodes=250)
        base_nids = {n["nid"] for n in base["nodes"]}
        assert len(base_nids) == 250

        # Chọn một láng giềng 1-hop có thêm láng giềng bên ngoài đồ thị cơ sở
        nbr = next(
            n["nid"]
            for n in base["nodes"]
            if n["nid"] != excel_nid
            and any(
                int(v) not in base_nids
                for v in v3_index.nbrs[v3_index.starts[n["nid"]] : v3_index.starts[n["nid"] + 1]]
            )
        )
        expanded = extract_ego_subgraph(
            v3_index, excel_nid, hops=hops, extra_nids=[nbr], max_nodes=250,
        )
        expanded_nids = {n["nid"] for n in expanded["nodes"]}
        added = expanded_nids - base_nids
        assert len(expanded_nids) == 250
        assert nbr in expanded_nids
        assert len(added) > 0, f"extra_nids trên hub Microsoft Excel ({hops}-hop) không thêm được nút nào"


def test_layout_vis_degree_matches_rendered_edges_and_3d_empty_edges(v3_index) -> None:
    """`nodes_df['degree']` phải bằng đúng số láng giềng đang vẽ và 3D hiển thị được khi edges rỗng."""
    from app.views.do_thi_viec_lam import _index_graph

    sub_randstad = extract_silo_subgraph(v3_index, 0)
    ndf_cap, edf_cap, meta_cap = layout_subgraph_to_dfs(sub_randstad, dim=2, max_render_nodes=400)
    assert meta_cap["truncated_render"] is True
    nbrs_cap = _index_graph(ndf_cap, edf_cap)
    for i, row in ndf_cap.iterrows():
        assert int(row["degree"]) == len(nbrs_cap[i]), (
            f"node {row['nid']} degree={row['degree']} != rendered_neighbors={len(nbrs_cap[i])}"
        )

    # Lọc đơn loại -> không có cạnh nội loại, truncated_render=False khi không vượt cap
    for kind_only in (KIND_JOB, KIND_SKILL):
        ndf_k, edf_k, meta_k = layout_subgraph_to_dfs(
            sub_randstad, dim=3, max_render_nodes=5000, kind_filter=kind_only,
        )
        assert not ndf_k.empty
        assert edf_k.empty
        assert meta_k["truncated_render"] is False
        nbrs_k = _index_graph(ndf_k, edf_k)
        assert all(int(row["degree"]) == len(nbrs_k[i]) == 0 for i, row in ndf_k.iterrows())

        html_3d = graph_html_3d(ndf_k, edf_k)
        assert "var minDeg = 0;" in html_3d
        p3 = _payload_3d(ndf_k, edf_k)
        assert len(p3["nodes"]) == len(ndf_k)
        assert p3["links"] == []


def test_layout_and_renderer_id_wiring_no_broken_links(v3_index) -> None:
    # Kiểm tra cả layout nhỏ (spring <= 400) và layout O(N) lớn (randstad 6.918 nút)
    sub_large = extract_silo_subgraph(v3_index, 0)
    ndf2, edf2, meta2 = layout_subgraph_to_dfs(sub_large, dim=2, max_render_nodes=None)
    assert len(ndf2) == 6918
    assert meta2["layout_algo"] == "radial_o_n"
    assert np.isfinite(ndf2[["x", "y"]].to_numpy()).all()

    p2 = _graph_payload_2d(ndf2, edf2)
    ids2 = {n["id"] for n in p2["nodes"]}
    assert len(ids2) == len(ndf2)
    assert len(p2["links"]) == len(edf2)
    assert all(lk["source"] in ids2 and lk["target"] in ids2 for lk in p2["links"])

    ndf3, edf3, _ = layout_subgraph_to_dfs(sub_large, dim=3, max_render_nodes=500)
    p3 = _payload_3d(ndf3, edf3)
    ids3 = {n["id"] for n in p3["nodes"]}
    assert len(ids3) == len(ndf3)
    assert len(p3["links"]) == len(edf3)
    assert all(lk["source"] in ids3 and lk["target"] in ids3 for lk in p3["links"])
    assert all("fx" not in n and "fy" not in n and "fz" not in n for n in p3["nodes"][:20])
    assert "ForceGraph3D" in graph_html_3d(ndf3, edf3)


# =====================================================================
# AC3 — Giao diện Streamlit AppTest cho cả 2 chế độ & R3
# =====================================================================
def test_app_view_silo_and_global_modes_end_to_end() -> None:
    from streamlit.testing.v1 import AppTest

    os.environ["DSH_VIEW"] = "do_thi_viec_lam"
    at = AppTest.from_file(str(ROOT / "tests" / "_view_runner.py"), default_timeout=180)
    at.run()
    assert not at.exception, [e.value for e in at.exception]

    # AC1a: Mặc định là Silo Nhà tuyển dụng và nạp đủ 9.116 silo
    mode_radio = at.radio(key="gx-mode")
    assert mode_radio.value == "Silo Nhà tuyển dụng"

    silo_sb = at.selectbox(key="gx-silo")
    assert len(silo_sb.options) == 9116
    assert any(opt.startswith("randstad · ") for opt in silo_sb.options[:5])
    assert any(opt.startswith("allmedstaffing.com · ") for opt in silo_sb.options[:5])

    # Kiểm tra 4 thẻ số liệu (.gx-mini-card) có mặt trong markdown
    md_text = "\n".join(m.value for m in at.markdown)
    assert md_text.count("gx-mini-card") == 4

    # Chọn silo allmedstaffing.com (cid=1), tìm trong silo và mở panel chi tiết
    silo_sb.set_value(1).run()
    assert not at.exception
    at.text_input(key="gx-q").set_value("Nurse").run()
    assert not at.exception
    hit_btns = [b for b in at.button if b.key and b.key.startswith("gx-hit-")]
    assert len(hit_btns) > 0
    hit_btns[0].click().run()
    assert not at.exception
    assert any(b.key == "gx-close" for b in at.button)

    # Đóng chi tiết, thử lọc loại nút (R3) và bật 3D (R3)
    at.button(key="gx-close").click().run()
    at.selectbox(key="gx-kind").set_value("Tin tuyển dụng").run()
    assert not at.exception
    at.selectbox(key="gx-kind").set_value("Tất cả").run()
    at.radio(key="gx-dim-radio").set_value("3D").run()
    assert not at.exception

    # Kiểm tra silo 0 nghề (cid=2: webhrdept.com) với bộ lọc Nghề O*NET không crash
    at.selectbox(key="gx-silo").set_value(2).run()
    at.selectbox(key="gx-kind").set_value("Nghề O*NET").run()
    assert not at.exception

    # Chuyển sang Hướng 2: Tìm kiếm toàn bộ (264.995 nút) + Ego-graph
    at.selectbox(key="gx-kind").set_value("Tất cả").run()
    at.radio(key="gx-mode").set_value("Tìm kiếm toàn bộ (264.995 nút)").run()
    assert not at.exception

    at.text_input(key="gx-global-q").set_value("allmedstaffing.com").run()
    assert not at.exception
    global_hits = [b for b in at.button if b.key and b.key.startswith("gx-global-hit-")]
    assert len(global_hits) > 0
    global_hits[0].click().run()
    assert not at.exception

    # Trên nút tâm không hiện nút mở rộng vô nghĩa; chọn một láng giềng qua quick-select để mở rộng
    assert not [b for b in at.button if b.key and b.key.startswith("gx-expand-")]
    nbr_btns = [b for b in at.button if b.key and b.key.startswith("gx-nbr-")]
    assert len(nbr_btns) > 0
    nbr_btns[0].click().run()
    assert not at.exception

    # Chuyển 2-hop + mở rộng láng giềng + quay lại 2D
    at.selectbox(key="gx-ego-hops").set_value(2).run()
    assert not at.exception
    expand_btns = [b for b in at.button if b.key and b.key.startswith("gx-expand-")]
    if not expand_btns:
        # Nếu nút đang chọn đã hết láng giềng mới ở 2-hop, chọn nút khác trong gx-ego-pick
        pick_sb = at.selectbox(key="gx-ego-pick")
        for idx_opt, opt in enumerate(pick_sb.options):
            if idx_opt == 0 or str(opt).startswith("[Tâm] "):
                continue
            at.selectbox(key="gx-ego-pick").select_index(idx_opt).run()
            expand_btns = [b for b in at.button if b.key and b.key.startswith("gx-expand-")]
            if expand_btns or idx_opt >= 8:
                break
    assert len(expand_btns) > 0
    expand_btns[0].click().run()
    assert not at.exception

    at.radio(key="gx-dim-radio").set_value("2D").run()
    assert not at.exception
    assert len(at.expander) >= 2
    md_text_global = "\n".join(m.value for m in at.markdown)
    assert md_text_global.count("gx-mini-card") == 4


def test_app_global_ego_select_neighbor_and_expand_increases_nodes() -> None:
    """Trong chế độ Toàn bộ (AppTest), chọn láng giềng và bấm Mở rộng láng giềng phải tăng số nút."""
    import re
    from streamlit.testing.v1 import AppTest

    os.environ["DSH_VIEW"] = "do_thi_viec_lam"
    at = AppTest.from_file(str(ROOT / "tests" / "_view_runner.py"), default_timeout=180)
    at.run()
    assert not at.exception, [e.value for e in at.exception]

    at.radio(key="gx-mode").set_value("Tìm kiếm toàn bộ (264.995 nút)").run()
    assert not at.exception

    # Tìm Ứng viên #47 (Ego 1-hop nhỏ, dễ kiểm đếm tăng số nút)
    at.text_input(key="gx-global-q").set_value("47").run()
    hit_47 = [b for b in at.button if b.key == "gx-global-hit-46" or (b.key and b.key.startswith("gx-global-hit-") and "Passenger Screener" in b.label)]
    assert hit_47, [b.label for b in at.button if b.key and b.key.startswith("gx-global-hit-")]
    hit_47[0].click().run()
    assert not at.exception

    # Trên nút tâm không có nút gx-expand-* vô nghĩa
    assert not [b for b in at.button if b.key and b.key.startswith("gx-expand-")]

    def _rendered_counts() -> tuple[int, int]:
        cap_txt = "\n".join(c.value for c in at.caption)
        m = re.search(r"\*\*([\d,]+)\*\*\s*nút,\s*\*\*([\d,]+)\*\*\s*cạnh", cap_txt)
        assert m, f"Không đọc được số nút/cạnh từ caption: {cap_txt}"
        return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))

    n_before, _ = _rendered_counts()

    # Chọn một nút láng giềng qua gx-ego-pick
    pick_sb = at.selectbox(key="gx-ego-pick")
    non_center_idxs = [
        idx_opt
        for idx_opt, opt in enumerate(pick_sb.options)
        if idx_opt > 0 and not str(opt).startswith("[Tâm] ")
    ]
    assert non_center_idxs
    pick_sb.select_index(non_center_idxs[0]).run()
    assert not at.exception

    expand_btns = [b for b in at.button if b.key and b.key.startswith("gx-expand-")]
    assert len(expand_btns) == 1
    expand_btns[0].click().run()
    assert not at.exception

    n_after, _ = _rendered_counts()
    assert n_after > n_before, f"Sau mở rộng số nút phải tăng ({n_before} -> {n_after})"

    # Đổi chế độ sang Silo phải reset gx-sel-nid và gx-ego-extra
    at.radio(key="gx-mode").set_value("Silo Nhà tuyển dụng").run()
    assert not at.exception
    assert not [b for b in at.button if b.key == "gx-close"]
