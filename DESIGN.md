---
name: GNN + FL Job Recommendation UI
theme: light
contract: "Use only tokens defined here. Invent nothing."
primary: "#FF5A1F"
primary_hover: "#EA580C"
primary_accessible: "#C2410C"
primary_soft: "#FFF7ED"
canvas: "#F8FAFC"
surface: "#FFFFFF"
surface_glass: "rgba(255, 255, 255, 0.68)"
border: "#E2E8F0"
border_glass: "rgba(255, 255, 255, 0.92)"
ink: "#0F172A"
ink_muted: "#475569"
ink_subtle: "#64748B"
font_display: "Space Grotesk"
font_sans: "Plus Jakarta Sans"
font_mono: "JetBrains Mono"
radius_card: "12px"
radius_control: "8px"
---

# DESIGN.md — GNN + Federated Learning Job Recommendation UI

> **Contract:** Use only tokens, states, and component patterns defined in this file. Invent nothing.

---

## 1. Visual Theme & Atmosphere

- **Aesthetic Direction:** Warm Architectural Light (`#F8FAFC` 24×24px blueprint dot-grid + warm Signal Orange ambient mesh) paired with high-clarity frosted glass (`rgba(255, 255, 255, 0.68)`, `backdrop-filter: blur(18px) saturate(175%)`).
- **Editorial Precision:** Swiss-grid hierarchy, crisp hairline borders (`#E2E8F0` / `rgba(255, 255, 255, 0.92)`), tight display tracking, and zero generic multi-color SaaS card clutter.

---

## 2. Color Palette & Semantic Roles

| Token | Value | Strict Usage |
| :--- | :--- | :--- |
| `ORANGE` | `#FF5A1F` | Primary CTAs, active nav/tab accents, Border Beam, slider/radio/checkbox active state, hero FedAvg series |
| `ORANGE_HOVER` | `#EA580C` | Primary CTA gradient bottom, active icon fill, focus border |
| `ORANGE_DARK` | `#C2410C` | Accessible text/labels on `#FFF7ED` or glass (WCAG AA ≥ 4.6:1) |
| `ORANGE_SOFT` | `#FFF7ED` | Active nav pill fill, tag pill bg, hover wash, question banner tint |
| `ORANGE_BORDER` | `#FED7AA` | Tag pill border, hover border highlight (`#FDBA74` on interactive lift) |
| `INK` | `#0F172A` | Display headings, hero metrics, centralized baseline, primary text |
| `INK_MUTED` | `#475569` | Secondary body copy, inactive nav labels, chart axis labels |
| `INK_SUBTLE` | `#64748B` | Micro-labels, inactive 2D icons, table metadata |
| `CANVAS` | `#F8FAFC` | Base page background behind dot-grid (`#CBD5E1`) and warm radial mesh |
| `SURFACE` | `#FFFFFF` | Inputs, selects, active segmented tabs, plot canvases |
| `GLASS` | `rgba(255, 255, 255, 0.68)` | Frosted cards, expanders, topbar, sidebar, console panels |
| `BORDER` | `#E2E8F0` | 1px hairline borders on controls, dividers, dataframes, alerts |
| `GREEN` | `#10B981` | Healthy node latency (`p50`), pass/live status badges |
| `WARN` | `#F59E0B` | Medium latency, demo/degraded warnings |
| `RED` | `#EF4444` | High latency (`p95`), private edges, error states |
| `SKY` | `#0EA5E9` | Informational status stripe, skill nodes |

Shared categorical palette (`PALETTE`): `["#FF5A1F", "#0F172A", "#0EA5E9", "#10B981", "#8B5CF6", "#64748B"]`.

---

## 3. Typography Scale & Weights

| Role | Font Family | Size / Weight | Tracking / Numerics |
| :--- | :--- | :--- | :--- |
| `h1` / `stTitle` | `Space Grotesk` | `2rem–2.25rem` / `700` | `-0.035em` |
| `Hero Metric` (`.hx-hero-val`) | `Space Grotesk` | `3.1rem` / `700` | `-0.04em`, `tabular-nums` |
| `KPI Metric` (`.hx-metric`) | `Space Grotesk` | `1.85rem` / `700` | `-0.035em`, `tabular-nums` |
| `h2, h3` | `Space Grotesk` | `1.15rem–1.4rem` / `700` | `-0.02em` |
| `Body / UI` | `Plus Jakarta Sans` | `16px` / `400–600` | `line-height: 1.43` |
| `Kickers / Telemetry` | `JetBrains Mono` | `0.72rem–0.8rem` / `600–700` | `0.06em–0.08em`, `tabular-nums` |

---

## 4. Layout & Spacing Grid

- **8px Baseline Grid:** Block gap `0.85rem`, divider margin `1rem 0`, card padding `0.9rem 1rem`–`1.35rem 1.45rem`.
- **Asymmetric Bento Hero (`tong_quan.py`):** Top stage pairs the **Three.js 3D Federated Learning Network Hero** and the `FedAvg Recall@20` Border Beam card, with 2 compact glass metric tiles and 2 `.hx-editorial-card` narrative cards structured cleanly below.
- **Single-Row Control Bar & Collapsed Explainers:** Primary actions sit in one row; secondary methodology explanations collapse inside `st.expander(..., expanded=False)`.
- **Embedded Console (`html.is-embed`):** Hides duplicate brand header, elevates `.console` to `order: 2`, and collapses `#ncWhatPanel` by default inside Streamlit.

---

## 5. Component State Contracts

| Component | Resting | Hover | Focus / Active / Selected |
| :--- | :--- | :--- | :--- |
| **Cards** (`.hx-card`, `.hx-bento-hero`, `.hx-bento-tile`, `.hx-editorial-card`, `.gx-mini-card`) | `rgba(255,255,255,0.68)`, `blur(18px) saturate(175%)`, 3-layer shadow | `perspective(900px) rotateX(1.5deg) rotateY(-1.5deg) translateY(-3px)`, `#FDBA74` rim | Border Beam (`#FB923C → #FF5A1F`) on hero |
| **Inputs & Selects** (`[data-baseweb="input"]`, `[data-baseweb="textarea"]`, `[data-baseweb="select"] > div`) | `#FFFFFF`, `1px solid #E2E8F0`, `8px` radius | Border `#CBD5E1` | `:focus-within`: `#FF5A1F` border + `0 0 0 3px rgba(255,90,31,0.14)` ring |
| **Multiselect Tags** (`[data-baseweb="tag"]`) | `#FFF7ED` bg, `#C2410C` text, `1px solid #FED7AA` | `#FFEDD5` bg | — |
| **Segmented Tabs** (`[data-baseweb="tab-list"]`, `[data-baseweb="tab"]`) | `rgba(241,245,249,0.85)` bar, `4px` pad, `10px` radius | `#0F172A` text | `[aria-selected="true"]`: `#FFFFFF` pill, `0 1px 3px rgba(15,23,42,0.08)`, `#FF5A1F` accent |
| **Expanders** (`[data-testid="stExpander"]`) | `rgba(255,255,255,0.72)`, `blur(14px)`, `1px solid #E2E8F0`, `10px` radius | `#FDBA74` border | Expanded summary `#0F172A` bold |
| **Radios, Checkboxes, Sliders** | `#FFFFFF` surface, `#CBD5E1` border | `#FF5A1F` border | `#FF5A1F` fill/track; slider thumb `#FFFFFF` + `2px solid #FF5A1F` |
| **Buttons** (`.stButton > button`, `.btn-primary`) | Secondary: `#FFFFFF` + specular inset; Primary: `#FF5A1F → #EA580C` | `translateY(-1px)` + `#FDBA74` / warm shadow | `:active`: `translateY(1px) scale(0.985)` |
| **Tables & Alerts** (`[data-testid="stDataFrame"]`, `[data-testid="stAlert"]`) | `1px solid #E2E8F0`, `10px` radius, frosted `#FFFFFF` | — | Alerts carry `4px` semantic left stripe |
| **Sidebar Nav** (`[data-testid="stSidebarNavLink"]`) | `#475569` text, `#64748B` 2D SVG `mask-image` | `#FFF7ED` bg, `#0F172A` text/icon | `[aria-current="page"]`: `#FFF7ED` bg, `#C2410C` text, `#EA580C` icon, `inset 3px 0 0 #FF5A1F` |

---

## 6. 3D, WebGL & Motion Rules

- **Three.js 3D Federated Learning Network Hero (`app/components/three_hero.py`):** Offline-vendored `app/assets/three.min.js` (`WebGLRenderer({ alpha: true, antialias: true })`) rendering a translucent `#0F172A` wireframe aggregator icosahedron + glowing `#FF5A1F` core, 84 Fibonacci-distributed employer nodes, animated gradient-packet pulses, `lerp` mouse parallax, interactive `Pulse Round` wave, `Pause/Play` toggle, and automatic 2D Canvas fallback.
- **Border Beam & 3D Tilt:** `@property --beam-angle` (`6s linear infinite`), `cubic-bezier(0.22, 1, 0.36, 1)` spring easing, `initTactile3D()` (`±2.5deg` tilt + warm `--mx`/`--my` sheen in `ui/`), and `flPulse` (`1.8s infinite`) on live status dots.
- **Accessibility:** `@media (prefers-reduced-motion: reduce)` disables all CSS animations, Border Beams, 3D tilts, and pauses idle WebGL rotation.

---

## 7. Do's & Don'ts

- **Do:** Keep technical jargon (`Federated Learning`, `GNN`, `GraphSAGE`, `cold-start`) in English per `docs/QUY_UOC_THUAT_NGU.md`.
- **Do:** Maintain 60fps in dense 220-cell `.node` grids by omitting `backdrop-filter` on individual `.node` cells.
- **Don't:** Invent ad-hoc hex colors, rainbow KPI top bars, or unstyled default BaseWeb boxes.
- **Don't:** Add redundant `st.caption` margin notes, developer debug footers, or raw OS emojis in sidebar navigation.
