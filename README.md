# GNN + Há»c liÃªn bang cho gá»£i Ã½ viá»‡c lÃ m

Äá»“ Ã¡n cuá»‘i ká»³ mÃ´n **DSS â€” Há»‡ há»— trá»£ quyáº¿t Ä‘á»‹nh**
Phan Gia Báº£o Â· 102220265 â€” Nguyá»…n VÄƒn ChÆ°Æ¡ng Â· 102220267

Dá»¯ liá»‡u tuyá»ƒn dá»¥ng thuá»™c vá» nhiá»u ná»n táº£ng/doanh nghiá»‡p khÃ¡c nhau vÃ  khÃ´ng
Ä‘Æ°á»£c phÃ©p gom vá» má»™t mÃ¡y chá»§. Äá»“ Ã¡n dá»±ng **Ä‘á»“ thá»‹** ngÆ°á»i dÃ¹ngâ€“tinâ€“ká»¹ nÄƒngâ€“
ngÃ nh rá»“i huáº¥n luyá»‡n nÃ³ báº±ng **há»c liÃªn bang**, Ä‘á»ƒ dá»¯ liá»‡u gá»‘c khÃ´ng rá»i
khá»i nÆ¡i lÆ°u trá»¯ â€” chá»‰ tham sá»‘ mÃ´ hÃ¬nh Ä‘Æ°á»£c trao Ä‘á»•i.

---

## Cháº¡y trong 3 lá»‡nh

```powershell
# 1. Dá»±ng toÃ n bá»™: sá»‘ liá»‡u â†’ hÃ¬nh â†’ bÃ¡o cÃ¡o
powershell -ExecutionPolicy Bypass -File run_all.ps1

# 2. Má»Ÿ demo trá»±c quan
python -m streamlit run app/streamlit_app.py --server.headless=true

# 3. Má»Ÿ bÃ¡o cÃ¡o
docs\BAO_CAO_GNN_FL.docx     # trong Word: Ctrl+A rá»“i F9 Ä‘á»ƒ cáº­p nháº­t má»¥c lá»¥c
```

ToÃ n bá»™ cháº¡y trÃªn **CPU**, khÃ´ng cáº§n GPU, khÃ´ng cáº§n máº¡ng, khoáº£ng **2 phÃºt**
(dá»¯ liá»‡u MEDAJob láº¥y tá»« thÆ° má»¥c `Lab03` cá»§a mÃ´n há»c).

---

## BÃ i toÃ¡n

| | |
|---|---|
| **Dá»¯ liá»‡u** | MEDAJob: 1.014 tin, 70 á»©ng viÃªn, 307 tÆ°Æ¡ng tÃ¡c (máº­t Ä‘á»™ 0,43%) |
| **Äá»“ thá»‹** | NgÆ°á»i dÃ¹ng â€“ Tin â€“ Ká»¹ nÄƒng â€“ NgÃ nh (603 ká»¹ nÄƒng, 10 ngÃ nh) |
| **MÃ´ hÃ¬nh** | LightGCN 2 táº§ng, 32 chiá»u |
| **PhÃ¢n tÃ¡n** | FedAvg / FedProx qua 5â€“12 khÃ¡ch hÃ ng, 20 vÃ²ng |
| **Káº¿t quáº£** | Recall@20: 0,402 â†’ **0,497** (táº­p trung: 0,504) |

---

## Káº¿t quáº£ chÃ­nh, nÃ³i tháº³ng

**ÄÃ£ lÃ m Ä‘Æ°á»£c**

- Há»c liÃªn bang láº¥y láº¡i **92,9%** khoáº£ng cÃ¡ch mÃ  viá»‡c chia nhá» dá»¯ liá»‡u gÃ¢y ra
  (cá»¥c bá»™ 0,402 â†’ liÃªn bang 0,497 â†’ táº­p trung 0,504), **khÃ´ng gá»­i má»™t dÃ²ng
  dá»¯ liá»‡u nÃ o**.
- MÃ´ hÃ¬nh Ä‘á»“ thá»‹ vÆ°á»£t má»i baseline: R@20 = 0,504 so vá»›i Item-KNN 0,349,
  phá»• biáº¿n 0,245, ná»™i dung 0,109.
- Ranh giá»›i dá»¯ liá»‡u Ä‘Æ°á»£c kiá»ƒm báº±ng test tá»± Ä‘á»™ng: payload client chá»‰ cÃ³ chá»‰ sá»‘
  nÃºt, vector float32 vÃ  trá»ng sá»‘ â€” khÃ´ng cÃ³ `user_id`, `job_id` hay rating.

**ChÆ°a lÃ m Ä‘Æ°á»£c** (Ä‘Æ°á»£c phÃ¢n tÃ­ch trong bÃ¡o cÃ¡o, khÃ´ng giáº¥u)

- Há»c liÃªn bang **khÃ´ng tiáº¿t kiá»‡m bÄƒng thÃ´ng** á»Ÿ quy mÃ´ nÃ y (tá»‘n gáº¥p 6.565 láº§n).
  Lá»£i Ã­ch náº±m á»Ÿ tuÃ¢n thá»§ phÃ¡p lÃ½, khÃ´ng pháº£i byte.
- Táº­p kiá»ƒm thá»­ gá»£i Ã½ chá»‰ cÃ³ **16 ngÆ°á»i dÃ¹ng** â†’ khoáº£ng tin cáº­y rá»™ng, nhiá»u
  chÃªnh lá»‡ch chÆ°a cÃ³ Ã½ nghÄ©a thá»‘ng kÃª.
- **ChÆ°a Ä‘o Ä‘Æ°á»£c má»©c Ä‘á»™ hÃ i lÃ²ng ngÆ°á»i dÃ¹ng** â€” yÃªu cáº§u cá»§a Ä‘á» bÃ i nhÆ°ng cáº§n
  A/B test trÃªn ngÆ°á»i dÃ¹ng tháº­t.
- **ChÆ°a cÃ³ báº£o vá»‡ riÃªng tÆ° tháº­t sá»±**: váº«n gá»­i tham sá»‘, chÆ°a cÃ³ secure
  aggregation hay DP-SGD.

---

## Cáº¥u trÃºc

```
CuoiKi/
â”œâ”€ run_all.ps1              # má»™t lá»‡nh cháº¡y háº¿t
â”œâ”€ config.yaml              # toÃ n bá»™ tham sá»‘ â€” khÃ´ng hard-code
â”œâ”€ requirements.txt
â”œâ”€ src/
â”‚  â”œâ”€ common.py             # seed, ghi JSON, bootstrap CI
â”‚  â”œâ”€ medajob/
â”‚  â”‚  â”œâ”€ prepare.py         # lÃ m sáº¡ch + dá»±ng Ä‘á»“ thá»‹ â†’ artifacts/medajob/
â”‚  â”‚  â”œâ”€ models.py          # LightGCN, GraphSAGE, baseline
â”‚  â”‚  â”œâ”€ federated.py       # FedAvg thÆ°a, FedProx
â”‚  â”‚  â”œâ”€ evaluate.py        # R@K, NDCG@K, MRR@K + CI
â”‚  â”‚  â””â”€ run_experiments.py # â†’ results/reco_main.json
â”‚  â””â”€ report/
â”‚     â”œâ”€ figures.py         # 9 hÃ¬nh 400 dpi
â”‚     â”œâ”€ make_facts.py      # â†’ docs/SO_LIEU_CHINH.md
â”‚     â””â”€ build_docx.py      # dá»±ng bÃ¡o cÃ¡o tá»« template khoa
â”œâ”€ app/                     # Streamlit, 6 trang
â”œâ”€ notebooks/               # tÃ¡i láº­p sá»‘ liá»‡u
â”œâ”€ tests/                   # regression test cho lá»—i tháº­t Ä‘Ã£ gáº·p
â”œâ”€ artifacts/               # dá»¯ liá»‡u Ä‘Ã£ xá»­ lÃ½ (sinh tá»± Ä‘á»™ng, khÃ´ng commit)
â”œâ”€ results/                 # JSON + figures/*.png (sinh tá»± Ä‘á»™ng)
â””â”€ docs/
   â”œâ”€ BAO_CAO_GNN_FL.docx   # bÃ¡o cÃ¡o
   â”œâ”€ PHAN_TICH_DE_TAI.md   # phÃ¢n tÃ­ch Ä‘á» bÃ i
   â”œâ”€ SO_LIEU_CHINH.md      # báº£ng sá»‘ liá»‡u chuáº©n (tá»± sinh)
   â””â”€ KICH_BAN_DEMO.md      # ká»‹ch báº£n trÃ¬nh bÃ y
```

---

## 6 trang demo

| Trang | Tráº£ lá»i cÃ¢u há»i gÃ¬ |
|---|---|
| **Tá»•ng quan** | VÃ¬ sao khÃ´ng gom dá»¯ liá»‡u vá» má»™t mÃ¡y chá»§, vÃ  Ä‘á»“ thá»‹ giÃºp gÃ¬? |
| **Äá»“ thá»‹ viá»‡c lÃ m** | CÃ¡i gÃ¬ á»Ÿ mÃ¡y chá»§, cÃ¡i gÃ¬ á»Ÿ khÃ¡ch hÃ ng? (báº­t/táº¯t Ä‘Æ°á»£c, cÃ³ cháº¿ Ä‘á»™ **3D**) |
| **MÃ´ phá»ng liÃªn bang** | Má»—i vÃ²ng tá»‘n bao nhiÃªu, cháº¥t lÆ°á»£ng tÄƒng tháº¿ nÃ o? (cÃ³ nÃºt tá»± phÃ¡t) |
| **Gá»£i Ã½ cho á»©ng viÃªn** | VÃ¬ sao tin nÃ y Ä‘Æ°á»£c Ä‘á» xuáº¥t? (cÃ³ cá»™t ká»¹ nÄƒng khá»›p) |
| **Káº¿t luáº­n & háº¡n cháº¿** | Äáº¡t/khÃ´ng Ä‘áº¡t, vÃ  lÃ m tiáº¿p tháº¿ nÃ o |

### Giao diá»‡n

App dÃ¹ng **theme sÃ¡ng** khai bÃ¡o trong `.streamlit/config.toml`, vá»›i báº£ng mÃ u
khá»›p 9 hÃ¬nh trong bÃ¡o cÃ¡o (cÃ¹ng má»™t "giá»ng" giá»¯a app vÃ  tÃ i liá»‡u).

CÃ³ hiá»‡u á»©ng Ä‘á»™ng á»Ÿ ba má»©c:

1. **Vi mÃ´** â€” tháº» sá»‘ liá»‡u trÆ°á»£t lÃªn, Ã´ phÃ¡t hiá»‡n trÆ°á»£t vÃ o, biá»ƒu Ä‘á»“ hiá»‡n dáº§n
   so le, hover cÃ³ Ä‘á»• bÃ³ng. LÃ m báº±ng CSS trong `app/components/theme.py`.
2. **Tá»± phÃ¡t** â€” trang *MÃ´ phá»ng liÃªn bang* cÃ³ cÃ´ng táº¯c "â–¶ Tá»± cháº¡y" phÃ¡t láº¡i
   tá»«ng vÃ²ng. DÃ¹ng `st.fragment(run_every=...)` nÃªn **khÃ´ng cháº·n** pháº§n cÃ²n
   láº¡i cá»§a trang (khÃ¡c vá»›i `time.sleep()`).
3. **TÃ´n trá»ng accessibility** â€” báº­t "giáº£m chuyá»ƒn Ä‘á»™ng" trong Windows thÃ¬ má»i
   animation tá»± táº¯t (`prefers-reduced-motion`).

> **Ghi chÃº ká»¹ thuáº­t:** Altair 6.0 Ä‘Ã£ bá» `.transition()` (cÃ³ á»Ÿ báº£n 5) vÃ 
> Vega-Lite khÃ´ng nháº­n `config.animation`, nÃªn animation biá»ƒu Ä‘á»“ Ä‘Æ°á»£c lÃ m
> báº±ng CSS thay vÃ¬ API biá»ƒu Ä‘á»“. ÄÃ¢y lÃ  lÃ½ do cÃ³ file `theme.py`.

### Äá»“ thá»‹ 3D

Trang *Äá»“ thá»‹ viá»‡c lÃ m* cÃ³ cÃ´ng táº¯c **2D / 3D**. Báº£n 3D xoay vÃ  zoom Ä‘Æ°á»£c tháº­t
(trá»¥c z tháº­t báº±ng WebGL), dá»±ng báº±ng [`3d-force-graph`](https://github.com/vasturiano/3d-force-graph)
nhÃºng qua `st.components.v1.html`.

Hai cháº¿ Ä‘á»™ dÃ¹ng **cÃ¹ng má»™t hÃ m** `build_graph_view(dim=...)` vÃ  cÃ¹ng cÃ´ng thá»©c
bá»‘ cá»¥c `spring_layout(..., dim=...)`, chá»‰ khÃ¡c sá»‘ chiá»u. Nhá» váº­y báº­t/táº¯t
2Dâ€“3D khÃ´ng lÃ m Ä‘á»•i táº­p nÃºt/cáº¡nh, cÅ©ng khÃ´ng lÃ m hÃ¬nh "nháº£y" vá»‹ trÃ­.

**File JS náº±m sáºµn trong repo** (`app/assets/3d-force-graph.min.js`, 690 KB, Ä‘Ã£
gÃ³i sáºµn Three.js) nÃªn app **khÃ´ng cáº§n máº¡ng** khi báº£o vá»‡. Náº¿u clone repo mÃ 
thiáº¿u file: `python tools/fetch_3d_asset.py` (cháº¡y má»™t láº§n).

> **VÃ¬ sao khÃ´ng dÃ¹ng pydeck?** Báº£n Ä‘áº§u dÃ¹ng `pdk.View(type="OrbitView")`
> vÃ  káº¿t quáº£ lÃ  **khung tráº¯ng**. NguyÃªn nhÃ¢n Ä‘Ã£ kiá»ƒm chá»©ng: pydeck serialize
> view thÃ nh `"@@type": "OrbitView"`, cÃ²n bundle deck.gl mÃ  Streamlit Ä‘Ã³ng gÃ³i
> **chá»‰ Ä‘Äƒng kÃ½ `MapView`** â€” grep toÃ n bá»™ 15 MB static khÃ´ng cÃ³ má»™t chá»¯
> `OrbitView`. Registry tráº£ `undefined` â†’ canvas rá»—ng, **khÃ´ng bÃ¡o lá»—i**.
> CÃ¹ng deck Ä‘Ã³ xuáº¥t ra HTML riÃªng (náº¡p deck.gl 9 tá»« CDN) thÃ¬ váº«n váº½ Ä‘Æ°á»£c, nÃªn
> Ä‘Ã¢y khÃ´ng pháº£i lá»—i dá»¯ liá»‡u. Xem má»¥c 9 cá»§a
> [docs/KHAO_SAT_DEMO_TRUC_QUAN.md](docs/KHAO_SAT_DEMO_TRUC_QUAN.md).

Báº£n 3D cÃ³ **thÃ´ng bÃ¡o lá»—i rÃµ rÃ ng** thay vÃ¬ khung tráº¯ng im láº·ng: náº¿u thiáº¿u
WebGL2 hoáº·c khá»Ÿi táº¡o tháº¥t báº¡i, iframe hiá»‡n hÆ°á»›ng dáº«n chuyá»ƒn sang tab 2D.

#### Äiá»u khiá»ƒn Ä‘á»“ thá»‹ 3D (náº±m trong khung, khÃ´ng gÃ¢y rerun)

385 nÃºt / 1.915 cáº¡nh nhÃ¬n á»Ÿ dáº¡ng "má»i thá»© Ä‘an nhau" thÃ¬ khÃ³ Ä‘á»c, nÃªn cÃ³ sáºµn
báº£ng Ä‘iá»u khiá»ƒn:

| Äiá»u khiá»ƒn | TÃ¡c dá»¥ng |
|---|---|
| **Chá»¥m theo liÃªn káº¿t** | Lá»±c Ä‘áº©y tá»± do â€” tháº¥y cáº¥u trÃºc tá»± nhiÃªn, cá»¥m nÃ o chá»¥m vÃ o nhau |
| **TÃ¡ch cá»¥m theo loáº¡i** | Dá»i 4 loáº¡i nÃºt vá» 4 hÆ°á»›ng: tháº¥y ngay "cÃ¡i gÃ¬ lÃ  cá»§a ai" |
| **Xáº¿p táº§ng** | NgÃ nh â†’ Ká»¹ nÄƒng â†’ Tin â†’ NgÆ°á»i dÃ¹ng, má»—i táº§ng má»™t máº·t pháº³ng |
| **Báº­c â‰¥ n** | áº¨n nÃºt Ã­t liÃªn káº¿t â€” lá»c nhiá»…u, chá»‰ giá»¯ nÃºt "trung tÃ¢m" |
| **LÃ m ná»•i khi rÃª / báº¥m** | TÃ´ má» má»i thá»© khÃ´ng liÃªn quan; báº¥m Ä‘á»ƒ **ghim** vÃ¹ng má»™t nÃºt |
| **Xem láº¡i toÃ n bá»™** | Bá» ghim, vá» gÃ³c nhÃ¬n bao quÃ¡t |

GÃ³c pháº£i cÃ³ **chÃº giáº£i mÃ u**: 4 loáº¡i nÃºt + 2 loáº¡i cáº¡nh + ghi chÃº "kÃ­ch thÆ°á»›c nÃºt
= báº­c". RÃª chuá»™t lÃªn nÃºt hiá»‡n **tooltip tá»± viáº¿t** (ná»n tráº¯ng, chá»¯ Ä‘áº­m, cÃ³ cháº¥m
mÃ u) â€” khÃ´ng dÃ¹ng tooltip máº·c Ä‘á»‹nh cá»§a thÆ° viá»‡n vÃ¬ nÃ³ lÃ  chá»¯ `lavender` khÃ´ng
ná»n, trÃªn ná»n tráº¯ng cá»§a app thÃ¬ gáº§n nhÆ° vÃ´ hÃ¬nh.

ToÃ n bá»™ Ä‘iá»u khiá»ƒn náº±m **trong** iframe. ÄÃ¢y lÃ  quyáº¿t Ä‘á»‹nh cÃ³ chá»§ Ä‘Ã­ch: náº¿u Ä‘áº·t
á»Ÿ phÃ­a Streamlit thÃ¬ má»—i láº§n báº¥m lÃ  má»™t láº§n rerun â€” iframe náº¡p láº¡i 1 MB HTML,
lá»±c Ä‘áº©y cháº¡y láº¡i tá»« Ä‘áº§u, Ä‘á»“ thá»‹ "nháº£y" ráº¥t khÃ³ quan sÃ¡t. Äá»•i láº¡i, tráº¡ng thÃ¡i
Ä‘á»“ thá»‹ khÃ´ng Ä‘á»“ng bá»™ vá»›i Streamlit (báº¥m sang trang khÃ¡c rá»“i quay láº¡i sáº½ vá» máº·c
Ä‘á»‹nh).

> **VÃ¬ sao trÆ°á»›c Ä‘Ã³ khÃ³ nhÃ¬n:** báº£n Ä‘áº§u ghim cá»©ng má»i nÃºt báº±ng `fx/fy/fz`, nÃªn
> lá»±c Ä‘áº©y 3D **khÃ´ng lÃ m gÃ¬ cáº£** â€” toáº¡ Ä‘á»™ Python giá»¯ nguyÃªn vÃ  Ä‘á»“ thá»‹ Ä‘áº·c láº¡i.
> Giá» dÃ¹ng `x/y/z`, lá»±c Ä‘áº©y hoáº¡t Ä‘á»™ng tháº­t. CÃ³ test riÃªng canh viá»‡c nÃ y
> (`test_3d_nodes_not_hard_pinned`).

> **VÃ¬ sao khÃ´ng dÃ¹ng `d3Force`/`d3ReheatSimulation`:** hai API nÃ y báº­t
> `engineRunning` cá»§a thÆ° viá»‡n mÃ  khÃ´ng báº£o Ä‘áº£m `layout` Ä‘Ã£ Ä‘Æ°á»£c dá»±ng, gÃ¢y lá»—i
> `Cannot read properties of undefined (reading 'tick')`. Má»i thay Ä‘á»•i bá»‘ cá»¥c
> Ä‘i qua `graphData()`. CÃ³ 2 test canh (`test_no_unsafe_d3_api_calls`,
> `test_all_graph_methods_are_verified`).

---

## Kiá»ƒm thá»­

```powershell
python -m pytest tests/ -q
```

Bá»™ test bao gá»“m cÃ¡c **regression test cho lá»—i tháº­t Ä‘Ã£ gáº·p**:

- `test_federated.py` â€” sá»‘ háº¡ng proximal cá»§a FedProx **pháº£i cÃ³ gradient**
  (bug dÃ¹ng `state_dict()` khiáº¿n FedProx = FedAvg).
- `test_federated.py` â€” payload client **khÃ´ng chá»©a dá»¯ liá»‡u thÃ´** vÃ  kÃ­ch thÆ°á»›c
  khÃ´ng phá»¥ thuá»™c sá»‘ báº£n ghi.
- `test_determinism.py` â€” cÃ¹ng seed pháº£i cho cÃ¹ng káº¿t quáº£; mÃ´ hÃ¬nh Ä‘á»“ thá»‹ pháº£i
  vÆ°á»£t má»i baseline khÃ´ng dÃ¹ng Ä‘á»“ thá»‹.
- `test_graph_view.py` â€” `job_nodes` **khÃ´ng Ä‘Æ°á»£c cá»™ng offset láº§n hai**, vÃ  nÃºt
  nhÃ£n "Tin tuyá»ƒn dá»¥ng" pháº£i Ä‘Ãºng báº±ng 200 (bug cÅ© chá»‰ cho 171 vÃ¬ 29 id rÆ¡i
  sang dáº£i ká»¹ nÄƒng, lÃ m máº¥t 540 cáº¡nh). CÅ©ng kiá»ƒm 2D/3D cÃ¹ng ná»™i dung vÃ  toáº¡ Ä‘á»™
  3D khÃ´ng cÃ³ NaN.
- `test_docs_consistency.py` â€” vÄƒn xuÃ´i khÃ´ng Ä‘Æ°á»£c cÃ²n dáº¥u váº¿t cá»§a Ä‘á» tÃ i IoT
  Ä‘Ã£ gá»¡, vÃ  má»i con sá»‘ nháº¯c tá»›i pháº£i khá»›p `results/*.json`.
- `test_ui_fixes.py` â€” 6 lá»—i giao diá»‡n: hai layer biá»ƒu Ä‘á»“ lá»‡ch `sort`, **cá»™t
  biáº¿n máº¥t khi dÃ¹ng thang log** (xem ghi chÃº dÆ°á»›i), camera 3D tá»± canh láº¡i sau
  khi zoom, thiáº¿u chÃº giáº£i mÃ u, tooltip chá»¯ sÃ¡ng trÃªn ná»n tráº¯ng, vÃ  khÃ´ng Ä‘Æ°á»£c
  dá»‹ch thuáº­t ngá»¯ chuyÃªn ngÃ nh.

> **VÃ¬ sao biá»ƒu Ä‘á»“ cá»™t KHÃ”NG dÃ¹ng thang log:** `mark_bar` váº½ tá»« baseline 0, mÃ 
> 0 trÃªn thang log lÃ  âˆ’âˆž, nÃªn Vega sinh path chiá»u cao **0px** â€” cá»™t biáº¿n máº¥t,
> chá»‰ cÃ²n nhÃ£n sá»‘ lÆ¡ lá»­ng. ÄÃ£ thá»­ thÃªm `y2` tÆ°á»ng minh vÃ  Ä‘áº·t `domain` tÆ°á»ng
> minh, **cáº£ hai Ä‘á»u khÃ´ng cá»©u Ä‘Æ°á»£c**. NÃªn `bar_chart(..., log_y=True)` nay
> bá» log scale vÃ  ghi giÃ¡ trá»‹ tháº­t lÃªn Ä‘áº§u cá»™t. CÃ³ test canh
> (`test_bar_chart_bars_have_height_with_log_y`).

---

## Ghi chÃº vá» mÃ´i trÆ°á»ng

MÃ¡y phÃ¡t triá»ƒn cÃ³ vÃ i rÃ ng buá»™c Ä‘Ã£ áº£nh hÆ°á»Ÿng Ä‘áº¿n thiáº¿t káº¿, Ä‘Æ°á»£c ghi láº¡i Ä‘á»ƒ
ngÆ°á»i cháº¡y láº¡i khÃ´ng báº¥t ngá»:

1. **KhÃ´ng cÃ i Ä‘Æ°á»£c gÃ³i má»›i** (pip bá»‹ cháº·n ghi metadata). VÃ¬ váº­y khÃ´ng dÃ¹ng
   PyTorch Geometric / DGL â€” lan truyá»n Ä‘á»“ thá»‹ Ä‘Æ°á»£c viáº¿t thuáº§n PyTorch. Biá»ƒu Ä‘á»“
   dÃ¹ng Altair thay vÃ¬ Plotly.
2. **`~/.matplotlib`, `~/.streamlit`, `%TEMP%` khÃ´ng ghi Ä‘Æ°á»£c.** `run_all.ps1`
   vÃ  app Ä‘Ã£ Ã©p cÃ¡c thÆ° má»¥c cache vÃ o `artifacts/`. Náº¿u cháº¡y tay, cáº§n Ä‘áº·t:
   ```powershell
   $env:MPLCONFIGDIR = "$PWD\artifacts\.mplcache"
   $env:TMP = "$PWD\artifacts\.tmp"
   ```
3. **KhÃ´ng chá»¥p screenshot tá»± Ä‘á»™ng Ä‘Æ°á»£c** (sandbox cháº·n pipe). áº¢nh giao diá»‡n
   trong bÃ¡o cÃ¡o lÃ  hÃ¬nh váº½ tá»« dá»¯ liá»‡u, khÃ´ng pháº£i áº£nh chá»¥p mÃ n hÃ¬nh.
4. **CÃ³ vÃ i thÆ° má»¥c rÃ¡c bá»‹ khoÃ¡ quyá»n** (`_tmp/`, `pytest-cache-files-*/`) do
   quÃ¡ trÃ¬nh dÃ² mÃ´i trÆ°á»ng lÃºc Ä‘áº§u. ChÃºng **khÃ´ng áº£nh hÆ°á»Ÿng** Ä‘áº¿n pipeline vÃ 
   Ä‘Ã£ náº±m trong `.gitignore`. Náº¿u muá»‘n xoÃ¡, cháº¡y PowerShell **vá»›i quyá»n quáº£n
   trá»‹**:
   ```powershell
   Remove-Item -Recurse -Force _tmp, pytest-cache-files-*
   ```

---

## Dá»¯ liá»‡u vÃ  tÃ i liá»‡u tham kháº£o

**Dá»¯ liá»‡u** â€” MEDAJob, bá»™ dá»¯ liá»‡u cá»§a mÃ´n há»c, táº£i tá»« há»‡ thá»‘ng mÃ´n há»c
(má»¥c Há»“ sÆ¡ â†’ Táº£i MEDAJob CSV).

**TÃ i liá»‡u chÃ­nh**

- He vÃ  cá»™ng sá»± (2020). *LightGCN: Simplifying and Powering Graph Convolution
  Network for Recommendation.* SIGIR '20.
- McMahan vÃ  cá»™ng sá»± (2017). *Communication-Efficient Learning of Deep
  Networks from Decentralized Data.* AISTATS 2017. (FedAvg)
- Li vÃ  cá»™ng sá»± (2020). *Federated Optimization in Heterogeneous Networks.*
  MLSys 2020. (FedProx)
- Rendle vÃ  cá»™ng sá»± (2009). *BPR: Bayesian Personalized Ranking from Implicit
  Feedback.* UAI 2009.
