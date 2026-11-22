"""Four Manim Community (v0.22.1) scenes for the FedGraph presentation deck.

Palette strictly matches E:\\2026\\DUT\\HTTM\\BT1-CK\\BaiBaoCB\\finalslide.pptx
(`Story` editorial academic theme):
- Background:      #F5F1E8  (Warm Cream Paper)
- Card / Surface:  #ECE7DA  (Soft Cream Tint)
- Stroke / Rule:   #C9C2B0  (Warm Hairline)
- Primary Teal:    #0F4C5C  (Deep Petroleum Teal)
- Terracotta:      #A8554E  (Muted Terracotta)
- Title / Ink:     #1A1A1A
- Body Text:       #2B2B2B
- Muted / Meta:    #5C5C5C

No LaTeX is used anywhere; all labels, math expressions, and counters use
Manim `Text(..., font="Cambria")` and Unicode glyphs.
"""

from manim import *
import numpy as np

# ---------------------------------------------------------------------------
# Editorial Palette (finalslide.pptx Story theme)
# ---------------------------------------------------------------------------
BG = "#F5F1E8"
SURF = "#ECE7DA"
RULE = "#C9C2B0"
TEAL = "#0F4C5C"
TEAL_SOFT = "#DDE7E9"
TERRA = "#A8554E"
TERRA_SOFT = "#EFE0DD"
INK = "#1A1A1A"
BODY = "#2B2B2B"
MUTED = "#5C5C5C"
CREAM_WHITE = "#FBF9F4"

FONT = "Cambria"
W = config.frame_width   # 14.222
H = config.frame_height  # 8.0


def init_scene(scene: Scene):
    scene.camera.background_color = BG


def txt(s: str, size: int = 18, color: str = BODY, weight=NORMAL,
        slant=NORMAL, **kw) -> Text:
    return Text(s, font=FONT, font_size=size, color=color,
                weight=weight, slant=slant, **kw)


def add_header(scene: Scene, title_str: str, subtitle_str: str | None = None):
    t = txt(title_str, size=27, color=INK, weight=BOLD)
    if t.width > W - 1.2:
        t.scale_to_fit_width(W - 1.2)
    t.to_edge(UP, buff=0.30)

    # Double editorial hairline under title
    hl1 = Line([-6.5, t.get_bottom()[1] - 0.14, 0],
               [6.5, t.get_bottom()[1] - 0.14, 0],
               color=INK, stroke_width=1.4)
    hl2 = Line([-6.5, t.get_bottom()[1] - 0.19, 0],
               [6.5, t.get_bottom()[1] - 0.19, 0],
               color=RULE, stroke_width=0.9)

    if subtitle_str:
        st = txt(subtitle_str, size=14, color=MUTED, slant=ITALIC)
        st.next_to(hl2, DOWN, buff=0.08)
        scene.play(Write(t), Create(hl1), Create(hl2), FadeIn(st), run_time=0.9)
        return VGroup(t, hl1, hl2, st)

    scene.play(Write(t), Create(hl1), Create(hl2), run_time=0.9)
    return VGroup(t, hl1, hl2)


def add_hud(scene: Scene, claim: str, color: str = BODY):
    bar = Rectangle(width=W, height=0.54, stroke_width=0,
                    fill_color=SURF, fill_opacity=0.96)
    bar.to_edge(DOWN, buff=0)
    top_rule = Line([-W / 2, bar.get_top()[1], 0],
                    [W / 2, bar.get_top()[1], 0],
                    color=RULE, stroke_width=1.0)
    t = txt(claim, size=16, color=color, weight=BOLD)
    if t.width > W - 0.8:
        t.scale_to_fit_width(W - 0.8)
    t.move_to(bar.get_center())
    scene.add(bar, top_rule, t)
    return VGroup(bar, top_rule, t)


def card(w: float, h: float, center, fill=SURF, stroke=RULE,
         stroke_width=1.4, radius=0.08) -> RoundedRectangle:
    r = RoundedRectangle(width=w, height=h, corner_radius=radius,
                         stroke_color=stroke, stroke_width=stroke_width,
                         fill_color=fill, fill_opacity=1.0)
    r.move_to(center)
    return r


# ===========================================================================
# SCENE 1: Public Graph Backbone vs Private Employer Silos (GraphSafe)
# ===========================================================================
class Vid1PublicPrivateBoundary(Scene):
    """GraphSafe boundary: 0 Byte raw user-job edges leave silos; only ΔW/E_local."""

    def construct(self):
        init_scene(self)
        add_header(self, "GraphSafe: Public Graph Backbone vs Private Employer Silos")
        add_hud(self, "0 Byte dữ liệu thô rời silo — chỉ embedding chạm tới (ΔW / E_local) đi qua rào cản tới FedAvg Server.", TEAL)

        # 1. FedAvg Server (top center)
        srv_box = card(5.4, 0.88, [0, 2.38, 0], fill=TEAL, stroke=TEAL, stroke_width=1.5)
        srv_t1 = txt("FedAvg Server (Tổng hợp E_global)", size=19, color=CREAM_WHITE, weight=BOLD)
        srv_t1.move_to([0, 2.52, 0])
        srv_t2 = txt("Chỉ nhận bản cập nhật ΔW / E_local · Không thấy dữ liệu thô",
                     size=13, color="#DCE7EA")
        srv_t2.move_to([0, 2.16, 0])
        server = VGroup(srv_box, srv_t1, srv_t2)

        # 2. Privacy Wall (y = 1.56)
        wall_l = DashedLine([-6.4, 1.56, 0], [-2.15, 1.56, 0],
                            color=TERRA, stroke_width=2.6, dash_length=0.14)
        wall_r = DashedLine([2.15, 1.56, 0], [6.4, 1.56, 0],
                            color=TERRA, stroke_width=2.6, dash_length=0.14)
        wall_pill = card(4.2, 0.40, [0, 1.56, 0], fill=TERRA, stroke=TERRA, radius=0.06)
        wall_txt = txt("RÀO CẢN GraphSafe · 0 Byte raw data", size=14,
                       color=CREAM_WHITE, weight=BOLD).move_to(wall_pill)
        privacy_wall = VGroup(wall_l, wall_r, wall_pill, wall_txt)

        # 3. Public Graph Backbone (y = 0.48)
        pub_box = card(12.2, 1.18, [0, 0.48, 0], fill=TEAL_SOFT, stroke=TEAL, stroke_width=1.8)
        pub_hdr = txt("Public Graph Backbone (Công khai — Mọi Silo dùng chung)",
                      size=16, color=TEAL, weight=BOLD).move_to([0, 0.85, 0])

        occ_pill = card(3.4, 0.52, [-3.9, 0.25, 0], fill=CREAM_WHITE, stroke=TEAL, stroke_width=1.3, radius=0.06)
        occ_txt = txt("583 O*NET Occupations", size=15, color=INK, weight=BOLD).move_to(occ_pill)

        sk_pill = card(3.2, 0.52, [0.0, 0.25, 0], fill=CREAM_WHITE, stroke=TEAL, stroke_width=1.3, radius=0.06)
        sk_txt = txt("7.760 Tech Skills", size=15, color=INK, weight=BOLD).move_to(sk_pill)

        ed_pill = card(3.6, 0.52, [3.95, 0.25, 0], fill=CREAM_WHITE, stroke=TEAL, stroke_width=1.3, radius=0.06)
        ed_txt = txt("52.544 cạnh công khai (6,87%)", size=14, color=TEAL, weight=BOLD).move_to(ed_pill)

        e_os = Line(occ_pill.get_right(), sk_pill.get_left(), color=TEAL, stroke_width=2.0)
        e_se = Line(sk_pill.get_right(), ed_pill.get_left(), color=TEAL, stroke_width=2.0)
        backbone = VGroup(pub_box, pub_hdr, occ_pill, occ_txt, sk_pill, sk_txt,
                          ed_pill, ed_txt, e_os, e_se)

        # 4. Three Private Employer Silos (y = -1.68)
        silo_specs = [
            (-4.25, "Silo 1: randstad (Top 1)",
             ["• 4.745 apps (lớn nhất)", "• user-job & user-occ cục bộ", "• Quyền sở hữu client_of_job[j]"]),
            (0.0, "Silo k: Doanh nghiệp điển hình",
             ["• Median 23 apps (≥10 apps)", "• user-job & user-occ cục bộ", "• Không rò rỉ lịch sử ứng viên"]),
            (4.25, "Tổng thể: 9.116 Silos",
             ["• 436.893 cạnh user-job", "• 274.927 cạnh user-occ", "• 711.820 cạnh tư (93,13%)"]),
        ]
        silos = VGroup()
        silo_boxes = []
        for cx, stitle, bullets in silo_specs:
            bx = card(3.95, 1.92, [cx, -1.68, 0], fill=SURF, stroke=TERRA, stroke_width=1.8)
            hdr_bg = Rectangle(width=3.95, height=0.40, stroke_width=0,
                               fill_color=TERRA, fill_opacity=0.95)
            hdr_bg.move_to([cx, -0.92, 0])
            ht = txt(stitle, size=14, color=CREAM_WHITE, weight=BOLD).move_to(hdr_bg)
            blines = VGroup(*[
                txt(b, size=13, color=BODY).move_to([cx, -1.36 - idx * 0.36, 0])
                for idx, b in enumerate(bullets)
            ])
            # Align bullets neatly inside card
            for b in blines:
                b.align_to(bx.get_left() + RIGHT * 0.18, LEFT)
            g = VGroup(bx, hdr_bg, ht, blines)
            silos.add(g)
            silo_boxes.append(bx)

        # Connectors from silos to Public Backbone
        conn_pub = VGroup(*[
            DashedLine([cx, -0.72, 0], [cx, -0.11, 0], color=TEAL, stroke_width=1.8, dash_length=0.08)
            for cx, _, _ in silo_specs
        ])

        # Animate Sequence
        self.play(LaggedStart(*[FadeIn(s, shift=UP * 0.15) for s in silos], lag_ratio=0.18),
                  run_time=1.3)
        self.play(FadeIn(backbone, shift=UP * 0.12),
                  LaggedStart(*[Create(c) for c in conn_pub], lag_ratio=0.1),
                  run_time=1.3)
        self.play(Create(wall_l), Create(wall_r), FadeIn(wall_pill), FadeIn(wall_txt),
                  run_time=1.0)
        self.play(FadeIn(server, shift=DOWN * 0.12), run_time=0.8)

        # Raw data blocked attempt (red bounce at privacy wall)
        raw_pkt = card(1.55, 0.34, [-2.2, 0.25, 0], fill=TERRA_SOFT, stroke=TERRA, stroke_width=1.4, radius=0.05)
        raw_lbl = txt("raw (u, job)", size=11, color=TERRA, weight=BOLD).move_to(raw_pkt)
        raw_grp = VGroup(raw_pkt, raw_lbl).move_to([-4.25, -0.45, 0])
        self.play(FadeIn(raw_grp), run_time=0.25)
        self.play(raw_grp.animate.move_to([-4.25, 1.32, 0]), run_time=0.55)
        cross1 = Line([-4.45, 1.42, 0], [-4.05, 1.70, 0], color=TERRA, stroke_width=3.0)
        cross2 = Line([-4.45, 1.70, 0], [-4.05, 1.42, 0], color=TERRA, stroke_width=3.0)
        self.play(Create(cross1), Create(cross2), Flash([-4.25, 1.56, 0], color=TERRA, flash_radius=0.25),
                  run_time=0.5)
        self.play(FadeOut(raw_grp), FadeOut(cross1), FadeOut(cross2), run_time=0.35)

        # Approved ΔW / E_local packets traveling from all 3 silos up to FedAvg Server
        packets = VGroup()
        paths = []
        for idx, (cx, _, _) in enumerate(silo_specs):
            p = card(1.55, 0.36, [cx, -0.58, 0], fill=TEAL, stroke=TEAL, radius=0.06)
            pt = txt("ΔW / E_local", size=12, color=CREAM_WHITE, weight=BOLD).move_to(p)
            pkt = VGroup(p, pt)
            packets.add(pkt)
            target_x = -1.6 + idx * 1.6
            path = Line([cx, -0.58, 0], [target_x, 1.92, 0], color=TEAL, stroke_width=1.6)
            paths.append(path)

        self.play(FadeIn(packets), run_time=0.3)
        self.play(*[MoveAlongPath(packets[i], paths[i]) for i in range(3)], run_time=1.5)
        self.play(Circumscribe(server, color=TEAL, buff=0.08), FadeOut(packets), run_time=0.8)
        self.wait(1.0)


# ===========================================================================
# SCENE 2: 2-Hop LightGCN Message Passing via O*NET
# ===========================================================================
class Vid2LightGCN2Hop(Scene):
    """2-hop LightGCN propagation bridging Silo A -> O*NET -> Skill -> Silo B."""

    def construct(self):
        init_scene(self)
        add_header(self, "Lan truyền LightGCN 2-Hop qua Cầu nối O*NET")
        add_hud(self, "Cầu nối O*NET giúp ứng viên ở Silo A khám phá việc làm phù hợp ở Silo B (+9,00 điểm Recall@20).", TEAL)

        # Formula bar
        f_box = card(12.4, 0.56, [0, 2.48, 0], fill=SURF, stroke=RULE, stroke_width=1.2)
        f_txt = txt("e^(l+1) = ∑ ( e^(l) / √(d_u · d_i) )    ·    E_final = ( E^(0) + E^(1) + E^(2) ) / 3",
                    size=17, color=TEAL, weight=BOLD).move_to(f_box)
        self.play(FadeIn(f_box), Write(f_txt), run_time=1.0)

        # Zone headers above node chain
        z_a = card(4.7, 0.38, [-3.82, 1.72, 0], fill=TERRA_SOFT, stroke=TERRA, stroke_width=1.0, radius=0.05)
        z_at = txt("Cục bộ: Silo A", size=13, color=TERRA, weight=BOLD).move_to(z_a)
        z_p = card(4.7, 0.38, [1.28, 1.72, 0], fill=TEAL_SOFT, stroke=TEAL, stroke_width=1.0, radius=0.05)
        z_pt = txt("Public Graph Backbone (O*NET)", size=13, color=TEAL, weight=BOLD).move_to(z_p)
        z_b = card(2.2, 0.38, [5.1, 1.72, 0], fill=TEAL, stroke=TEAL, stroke_width=1.0, radius=0.05)
        z_bt = txt("Silo B (Mục tiêu)", size=13, color=CREAM_WHITE, weight=BOLD).move_to(z_b)
        self.play(FadeIn(z_a, z_at, z_p, z_pt, z_b, z_bt), run_time=0.6)

        # 5-node propagation chain
        node_defs = [
            (-5.10, "Ứng viên\n#76044", "E^(0) Khởi tạo", TERRA, TERRA_SOFT),
            (-2.55, "Job\n(Silo A)", "Cạnh user-job", TERRA, TERRA_SOFT),
            (0.00, "O*NET\nOccupation", "583 mã SOC", TEAL, TEAL_SOFT),
            (2.55, "Tech\nSkill", "7.760 kỹ năng", TEAL, TEAL_SOFT),
            (5.10, "Cross-Silo\nJob (Silo B)", "Gợi ý Top-20", TEAL, TEAL_SOFT),
        ]
        nodes = VGroup()
        boxes = []
        for x, title_s, sub_s, col, fill_c in node_defs:
            b = card(1.96, 1.24, [x, 0.65, 0], fill=fill_c, stroke=col, stroke_width=2.0, radius=0.10)
            t = txt(title_s, size=15, color=INK, weight=BOLD).move_to([x, 0.80, 0])
            sb = txt(sub_s, size=11, color=MUTED).move_to([x, 0.23, 0])
            grp = VGroup(b, t, sb)
            nodes.add(grp)
            boxes.append(b)

        arrows = VGroup()
        for i in range(4):
            a = Arrow(boxes[i].get_right() + RIGHT * 0.03,
                      boxes[i + 1].get_left() + LEFT * 0.03,
                      color=MUTED, stroke_width=2.2, buff=0.02,
                      max_tip_length_to_length_ratio=0.16)
            arrows.add(a)

        self.play(LaggedStart(*[FadeIn(n, shift=UP * 0.12) for n in nodes], lag_ratio=0.12),
                  LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.12),
                  run_time=1.3)

        # Layer Mean panel (bottom-left) & Impact Badge (bottom-right)
        lm_box = card(6.5, 1.38, [-2.95, -1.35, 0], fill=SURF, stroke=RULE, stroke_width=1.4)
        lm_hdr = txt("Tổng hợp đa tầng LightGCN (L = 2)", size=15, color=INK, weight=BOLD).move_to([-2.95, -0.88, 0])
        l0 = card(1.42, 0.56, [-5.10, -1.48, 0], fill=CREAM_WHITE, stroke=TERRA, stroke_width=1.4, radius=0.06)
        l0_t = txt("E^(0) Gốc", size=13, color=TERRA, weight=BOLD).move_to(l0)
        l1 = card(1.52, 0.56, [-3.35, -1.48, 0], fill=CREAM_WHITE, stroke=TEAL, stroke_width=1.4, radius=0.06)
        l1_t = txt("E^(1) 1-Hop", size=13, color=TEAL, weight=BOLD).move_to(l1)
        l2 = card(1.52, 0.56, [-1.55, -1.48, 0], fill=CREAM_WHITE, stroke=TEAL, stroke_width=1.4, radius=0.06)
        l2_t = txt("E^(2) 2-Hop", size=13, color=TEAL, weight=BOLD).move_to(l2)
        lm_panel = VGroup(lm_box, lm_hdr, l0, l0_t, l1, l1_t, l2, l2_t)

        imp_box = card(5.4, 1.38, [3.45, -1.35, 0], fill=TEAL, stroke=TEAL, stroke_width=1.6)
        imp_t1 = txt("+9,00 pts Recall@20", size=24, color=CREAM_WHITE, weight=BOLD).move_to([3.45, -1.12, 0])
        imp_t2 = txt("0,3933 (Bỏ O*NET) → 0,4833 (Đầy đủ)", size=14, color="#DCE7EA", weight=BOLD).move_to([3.45, -1.62, 0])
        imp_badge = VGroup(imp_box, imp_t1, imp_t2)

        self.play(FadeIn(lm_panel), run_time=0.7)

        # Hop 1 animation: User #76044 -> Job (Silo A) -> O*NET Occupation
        pulse1 = Dot(nodes[0].get_center(), color=TERRA, radius=0.13)
        self.play(FadeIn(pulse1, scale=1.4), Indicate(l0, color=TERRA, scale_factor=1.08), run_time=0.5)
        self.play(MoveAlongPath(pulse1, Line(nodes[0].get_center(), nodes[1].get_center())),
                  arrows[0].animate.set_color(TERRA), run_time=0.65)
        self.play(MoveAlongPath(pulse1, Line(nodes[1].get_center(), nodes[2].get_center())),
                  arrows[1].animate.set_color(TEAL),
                  Indicate(l1, color=TEAL, scale_factor=1.08), run_time=0.75)

        # Hop 2 animation: O*NET Occupation -> Tech Skill -> Cross-Silo Job (Silo B)
        pulse1.set_color(TEAL)
        self.play(MoveAlongPath(pulse1, Line(nodes[2].get_center(), nodes[3].get_center())),
                  arrows[2].animate.set_color(TEAL), run_time=0.65)
        self.play(MoveAlongPath(pulse1, Line(nodes[3].get_center(), nodes[4].get_center())),
                  arrows[3].animate.set_color(TEAL),
                  Indicate(l2, color=TEAL, scale_factor=1.08), run_time=0.75)
        self.play(FadeOut(pulse1), Flash(nodes[4], color=TEAL, flash_radius=0.55), run_time=0.55)

        # Reveal verified impact badge
        self.play(GrowFromCenter(imp_badge), run_time=0.8)
        self.play(Circumscribe(imp_badge, color=TERRA, buff=0.10), run_time=0.9)
        self.wait(1.1)


# ===========================================================================
# SCENE 3: Sparse "Touched" FedAvg vs Non-IID Client Drift & FedProx
# ===========================================================================
class Vid3SparseFedAvgDrift(Scene):
    """Left: Sparse touched aggregation; Right: E=1 vs E=5 Client Drift & FedProx."""

    def construct(self):
        init_scene(self)
        add_header(self, "Sparse 'Touched' FedAvg vs Non-IID Client Drift & FedProx")
        add_hud(self, "Chỉ trung bình hóa nút đã chạm (den > 0) đạt 0,4833; tăng E=5 gây Client Drift (0,4565, chậm 4,8×).", TEAL)

        # Two main plates
        left_p = card(6.05, 5.10, [-3.30, 0.08, 0], fill=SURF, stroke=RULE, stroke_width=1.4)
        right_p = card(6.05, 5.10, [3.30, 0.08, 0], fill=SURF, stroke=RULE, stroke_width=1.4)
        self.play(FadeIn(left_p), FadeIn(right_p), run_time=0.6)

        # ---------------- LEFT PANEL: Sparse Touched Aggregation ----------------
        lh = txt("1. Sparse 'Touched' Aggregation", size=18, color=TEAL, weight=BOLD).move_to([-3.30, 2.25, 0])
        ls = txt("82.876 jobs toàn cục · Chỉ cập nhật job có den > 0", size=13, color=MUTED).move_to([-3.30, 1.88, 0])
        self.play(FadeIn(lh, ls), run_time=0.5)

        # 4x8 grid of global job slots
        cw, ch = 0.56, 0.34
        grid = VGroup()
        gx0 = -3.30 - 4 * (cw + 0.08) + (cw + 0.08) / 2
        gy0 = 1.28
        for r in range(4):
            for c in range(8):
                cell = RoundedRectangle(width=cw, height=ch, corner_radius=0.04,
                                        stroke_color=RULE, stroke_width=1.0,
                                        fill_color=CREAM_WHITE, fill_opacity=1.0)
                cell.move_to([gx0 + c * (cw + 0.08), gy0 - r * (ch + 0.08), 0])
                grid.add(cell)

        self.play(LaggedStart(*[FadeIn(c) for c in grid], lag_ratio=0.015), run_time=0.8)

        touched_idx = [2, 5, 11, 14, 19, 25, 29]
        self.play(LaggedStart(*[grid[i].animate.set_fill(TEAL, 1.0).set_stroke(TEAL, 1.4)
                                for i in touched_idx], lag_ratio=0.08), run_time=1.0)

        leg1 = card(0.24, 0.20, [-5.65, -0.38, 0], fill=TEAL, stroke=TEAL, radius=0.03)
        leg1_t = txt("den > 0: Cập nhật ΔW", size=12, color=TEAL, weight=BOLD).next_to(leg1, RIGHT, buff=0.10)
        leg2 = card(0.24, 0.20, [-2.55, -0.38, 0], fill=CREAM_WHITE, stroke=RULE, radius=0.03)
        leg2_t = txt("den = 0: Giữ nguyên", size=12, color=MUTED).next_to(leg2, RIGHT, buff=0.10)
        self.play(FadeIn(leg1, leg1_t, leg2, leg2_t), run_time=0.5)

        # Weighted vs Unweighted comparison bars (strictly proportional to 0.50 scale)
        w_lbl = txt("Weighted (w = n_edges)", size=13, color=INK, weight=BOLD).move_to([-4.65, -0.95, 0])
        w_lbl.align_to(left_p.get_left() + RIGHT * 0.30, LEFT)
        w_bar = Rectangle(width=3.60 * (0.4833 / 0.50), height=0.34, stroke_width=0, fill_color=TEAL, fill_opacity=1.0)
        w_bar.move_to([-3.30, -1.32, 0]).align_to(left_p.get_left() + RIGHT * 0.30, LEFT)
        w_val = txt("0,4833", size=15, color=TEAL, weight=BOLD).next_to(w_bar, RIGHT, buff=0.15)

        u_lbl = txt("Unweighted (w = 1,0)", size=13, color=BODY).move_to([-4.65, -1.78, 0])
        u_lbl.align_to(left_p.get_left() + RIGHT * 0.30, LEFT)
        u_bar = Rectangle(width=3.60 * (0.4716 / 0.50), height=0.34, stroke_width=0, fill_color=MUTED, fill_opacity=0.75)
        u_bar.move_to([-3.30, -2.15, 0]).align_to(left_p.get_left() + RIGHT * 0.30, LEFT)
        u_val = txt("0,4716", size=15, color=MUTED, weight=BOLD).next_to(u_bar, RIGHT, buff=0.15)

        self.play(FadeIn(w_lbl, u_lbl), GrowFromEdge(w_bar, LEFT), GrowFromEdge(u_bar, LEFT),
                  FadeIn(w_val, u_val), run_time=1.2)

        # ---------------- RIGHT PANEL: Client Drift & FedProx ----------------
        rh = txt("2. Non-IID Client Drift & FedProx", size=18, color=TERRA, weight=BOLD).move_to([3.30, 2.25, 0])
        rs = txt("Cùng vũ trụ cố định 4.511 jobs (20 clients, 4 vòng)", size=13, color=MUTED).move_to([3.30, 1.88, 0])
        self.play(FadeIn(rh, rs), run_time=0.5)

        # Vector convergence / drift diagram
        center_pt = np.array([3.25, 0.62, 0])
        opt_ring = Circle(radius=0.46, color=TEAL, stroke_width=1.4, fill_color=TEAL_SOFT, fill_opacity=0.45)
        opt_ring.move_to(center_pt)
        origin_dot = Dot(center_pt, color=INK, radius=0.09)
        origin_lbl = txt("E_global", size=12, color=INK, weight=BOLD).next_to(opt_ring, DOWN, buff=0.10)
        self.play(FadeIn(opt_ring, origin_dot, origin_lbl), run_time=0.5)

        # E=1 tight arrows (stay inside optimal ring)
        e1_dirs = [np.array([0.36, 0.27, 0]), np.array([-0.34, 0.28, 0]), np.array([0.09, -0.34, 0])]
        e1_arrows = VGroup(*[
            Arrow(center_pt, center_pt + d, color=TEAL, stroke_width=2.6, buff=0.06,
                  max_tip_length_to_length_ratio=0.22)
            for d in e1_dirs
        ])
        e1_tag = txt("E = 1: Hội tụ chặt", size=12, color=TEAL, weight=BOLD).move_to([1.60, 1.44, 0])
        self.play(LaggedStart(*[GrowArrow(a) for a in e1_arrows], lag_ratio=0.1),
                  FadeIn(e1_tag), run_time=1.0)

        # E=5 diverging client drift arrows (kept cleanly below label row)
        e5_dirs = [np.array([1.70, 0.34, 0]), np.array([-1.65, 0.32, 0]), np.array([1.40, -0.50, 0])]
        e5_arrows = VGroup(*[
            Arrow(center_pt, center_pt + d, color=TERRA, stroke_width=2.4, buff=0.06,
                  max_tip_length_to_length_ratio=0.14)
            for d in e5_dirs
        ])
        e5_tag = txt("E = 5: Client Drift", size=12, color=TERRA, weight=BOLD).move_to([4.95, 1.44, 0])
        self.play(LaggedStart(*[GrowArrow(a) for a in e5_arrows], lag_ratio=0.1),
                  FadeIn(e5_tag), run_time=1.1)

        # FedProx proximal anchor pulling back (offset below arrow so it never collides with label/shaft)
        pull = DashedLine(center_pt + np.array([1.66, 0.20, 0]),
                          center_pt + np.array([0.68, 0.06, 0]),
                          color=INK, stroke_width=2.0, dash_length=0.08)
        fp_tag = txt("FedProx (μ=0,01): Neo 0,5·μ‖E − E0‖²", size=12, color=BODY, weight=BOLD).move_to([3.30, -0.44, 0])
        self.play(Create(pull), FadeIn(fp_tag), run_time=0.8)

        # 3 Bottom Metric Pills
        pills_data = [
            (1.45, "E = 1 (FedAvg)", "0,4833", "23,2s", TEAL, TEAL_SOFT),
            (3.30, "FedProx μ=0,01", "0,4627", "24,7s", BODY, CREAM_WHITE),
            (5.15, "E = 5 (Drift)", "0,4565", "112,4s (4,8×)", TERRA, TERRA_SOFT),
        ]
        pills = VGroup()
        for px, ptitle, pscore, ptime, pcol, pfill in pills_data:
            pb = card(1.70, 1.25, [px, -1.58, 0], fill=pfill, stroke=pcol, stroke_width=1.6, radius=0.07)
            pt1 = txt(ptitle, size=12, color=INK, weight=BOLD).move_to([px, -1.18, 0])
            pt2 = txt(pscore, size=19, color=pcol, weight=BOLD).move_to([px, -1.58, 0])
            pt3 = txt(ptime, size=11, color=MUTED).move_to([px, -1.96, 0])
            pills.add(VGroup(pb, pt1, pt2, pt3))

        self.play(LaggedStart(*[FadeIn(p, shift=UP * 0.1) for p in pills], lag_ratio=0.15),
                  run_time=1.0)
        self.play(Circumscribe(pills[0], color=TEAL, buff=0.07), run_time=0.8)
        self.wait(1.0)


# ===========================================================================
# SCENE 4: Catalog Gap & Node Monitor Trade-offs
# ===========================================================================
class Vid4CatalogAndTelemetry(Scene):
    """Left: 3 Evaluation Catalog Scopes; Right: CUDA vs CPU Latency & ΔW Compression."""

    def construct(self):
        init_scene(self)
        add_header(self, "Catalog Gap & Đánh đổi Hạ tầng Node Monitor")
        add_hud(self, "Phạm vi Catalog quyết định mức Recall@20; CUDA giảm độ trễ 1,77× và Top-20% tiết kiệm 80% băng thông.", TEAL)

        left_p = card(6.05, 5.10, [-3.30, 0.08, 0], fill=SURF, stroke=RULE, stroke_width=1.4)
        right_p = card(6.05, 5.10, [3.30, 0.08, 0], fill=SURF, stroke=RULE, stroke_width=1.4)
        self.play(FadeIn(left_p), FadeIn(right_p), run_time=0.6)

        # ---------------- LEFT PANEL: 3 Evaluation Scopes ----------------
        lh = txt("1. Khoảng cách Catalog (Recall@20)", size=18, color=TEAL, weight=BOLD).move_to([-3.30, 2.25, 0])
        ls = txt("Đánh giá FedAvg trên 3 phạm vi ứng viên khác nhau", size=13, color=MUTED).move_to([-3.30, 1.88, 0])
        self.play(FadeIn(lh, ls), run_time=0.5)

        scopes = [
            (1.12, "Global Catalog (82.876 jobs · 50N)", 0.0475,
             "~89% job ngoài phạm vi 50 client chưa được huấn luyện", TERRA),
            (-0.18, "FL Catalog (9.058 jobs · 50N)", 0.3905,
             "Đánh giá công bằng trên đúng tập việc làm tham gia FL", BODY),
            (-1.48, "O*NET Catalog (956 jobs có nghề · 20N)", 0.5756,
             "Cầu nối nghề nghiệp & kỹ năng phát huy hiệu quả tối đa", TEAL),
        ]
        max_w = 4.35
        for sy, slabel, sval, snote, scol in scopes:
            lbl = txt(slabel, size=14, color=INK, weight=BOLD).move_to([-3.30, sy + 0.32, 0])
            lbl.align_to(left_p.get_left() + RIGHT * 0.32, LEFT)

            bg_bar = Rectangle(width=max_w, height=0.34, stroke_color=RULE, stroke_width=0.9,
                               fill_color=CREAM_WHITE, fill_opacity=1.0)
            bg_bar.move_to([-3.30, sy - 0.04, 0]).align_to(left_p.get_left() + RIGHT * 0.32, LEFT)

            fg_w = max(0.24, max_w * (sval / 0.65))
            fg_bar = Rectangle(width=fg_w, height=0.34, stroke_width=0,
                               fill_color=scol, fill_opacity=1.0)
            fg_bar.align_to(bg_bar, LEFT).align_to(bg_bar, UP)

            val_t = txt(f"{sval:.4f}".replace(".", ","), size=15, color=scol, weight=BOLD)
            val_t.next_to(bg_bar, RIGHT, buff=0.14)

            note_t = txt(snote, size=11, color=MUTED).move_to([-3.30, sy - 0.36, 0])
            note_t.align_to(left_p.get_left() + RIGHT * 0.32, LEFT)

            self.play(FadeIn(lbl, bg_bar, note_t), GrowFromEdge(fg_bar, LEFT),
                      FadeIn(val_t), run_time=0.95)

        # ---------------- RIGHT PANEL: Latency & Compression ----------------
        rh = txt("2. Độ trễ CUDA vs CPU & Nén ΔW", size=18, color=TEAL, weight=BOLD).move_to([3.30, 2.25, 0])
        rs = txt("300 mẫu đo perf_counter() (50 clients × 6 rounds)", size=13, color=MUTED).move_to([3.30, 1.88, 0])
        self.play(FadeIn(rh, rs), run_time=0.5)

        # Latency bars (CUDA vs CPU)
        lat_specs = [
            (1.22, "CUDA (Kaggle GPU)", 236.5, 315.5, TEAL),
            (0.45, "CPU (Local)", 418.0, 566.6, TERRA),
        ]
        lat_max_w = 2.65
        for ly, ltitle, p50, p95, lcol in lat_specs:
            lt = txt(ltitle, size=14, color=INK, weight=BOLD).move_to([3.30, ly + 0.24, 0])
            lt.align_to(right_p.get_left() + RIGHT * 0.32, LEFT)

            bar = Rectangle(width=lat_max_w * (p50 / 450.0), height=0.32, stroke_width=0,
                            fill_color=lcol, fill_opacity=1.0)
            bar.move_to([3.30, ly - 0.10, 0]).align_to(right_p.get_left() + RIGHT * 0.32, LEFT)

            vt = txt(f"p50 = {p50:.1f} ms  |  p95 = {p95:.1f} ms".replace(".", ","),
                     size=12, color=lcol, weight=BOLD).next_to(bar, RIGHT, buff=0.14)
            # Ensure text stays inside right panel
            if vt.get_right()[0] > right_p.get_right()[0] - 0.15:
                vt.scale_to_fit_width(right_p.get_right()[0] - 0.15 - vt.get_left()[0])

            self.play(FadeIn(lt), GrowFromEdge(bar, LEFT), FadeIn(vt), run_time=0.9)

        speed_note = txt("→ CUDA tăng tốc 1,77× độ trễ trung vị (p50)",
                         size=13, color=TEAL, weight=BOLD).move_to([3.30, -0.10, 0])
        div_line = Line([right_p.get_left()[0] + 0.30, -0.38, 0],
                        [right_p.get_right()[0] - 0.30, -0.38, 0],
                        color=RULE, stroke_width=1.1)
        self.play(FadeIn(speed_note), Create(div_line), run_time=0.5)

        # ΔW Compression tradeoff (FP32 / FP16 / Top-20%)
        chdr = txt("Nén ΔW (Node Monitor Simulator)", size=15, color=INK, weight=BOLD).move_to([3.30, -0.68, 0])
        chdr.align_to(right_p.get_left() + RIGHT * 0.32, LEFT)
        self.play(FadeIn(chdr), run_time=0.4)

        comp_specs = [
            (-1.12, "FP32 (Gốc)", 1.00, "100% payload", MUTED),
            (-1.54, "FP16", 0.50, "50% (-50%)", TEAL),
            (-1.96, "Top-20%", 0.20, "20% (-80%)", TEAL),
        ]
        comp_max_w = 2.55
        for cy, clab, ratio, cdesc, ccol in comp_specs:
            cl = txt(clab, size=13, color=BODY, weight=BOLD).move_to([1.15, cy, 0])
            cl.align_to(right_p.get_left() + RIGHT * 0.32, LEFT)
            cbar = Rectangle(width=comp_max_w * ratio, height=0.26, stroke_width=0,
                             fill_color=ccol, fill_opacity=0.95)
            cbar.move_to([2.85, cy, 0]).align_to([1.95, cy, 0], LEFT)
            cd = txt(cdesc, size=12, color=ccol, weight=BOLD).next_to(cbar, RIGHT, buff=0.14)
            if cd.get_right()[0] > right_p.get_right()[0] - 0.20:
                cd.scale_to_fit_width(right_p.get_right()[0] - 0.20 - cd.get_left()[0])
            self.play(FadeIn(cl), GrowFromEdge(cbar, LEFT), FadeIn(cd), run_time=0.65)

        self.wait(1.3)


ALL_SCENES = [
    Vid1PublicPrivateBoundary,
    Vid2LightGCN2Hop,
    Vid3SparseFedAvgDrift,
    Vid4CatalogAndTelemetry,
]
