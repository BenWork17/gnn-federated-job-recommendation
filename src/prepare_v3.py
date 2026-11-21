"""
prepare_v3.py — Dựng đồ thị dị thể CareerBuilder + O*NET, chia client theo NHÀ TUYỂN DỤNG.

Vì sao có bản v3 (so với các bản probe trước):
  · Probe cũ chỉ trích được 34,54% job có employer và lẫn rác nặng: top theo số
    application có 'if you' (2.646), 'our client' (2.367), 'this' (1.175), '\\r we' (948).
    Bước 1 ở đây siết lại: whitelist hậu tố pháp lý (đầu câu + NEO Ở CUỐI câu),
    regex câu đầu ('X is a/the ...', 'X seeks ...'), email + website domain có loại
    trừ headhunt và mail cá nhân, blacklist cụm đại từ, danh sách từ chức danh,
    chuẩn hoá HTML/mojibake; tên phải xuất hiện ở >= 2 JOB KHÁC NHAU.
  · Probe cũ trộn hai cấp mã nghề (11-1011.00 vs 11-1011) -> phồng 67,4% số cạnh.
    Ở đây mã nghề CHỈ dùng dạng GỐC 6 ký tự soc[:7], nhất quán ở: nút nghề,
    cạnh job-nghề, cạnh nghề-kỹ năng, cạnh user-nghề.
  · RAM khả dụng ~3,9 GB còn jobs.tsv 3,2 GB -> TUYỆT ĐỐI không pandas cho jobs.tsv.
    Mọi file lớn đọc streaming bằng csv.reader + csv.field_size_limit.

Đồ thị dị thể, nút xếp theo 4 khối:  [ user | job | occupation | skill ]
  edge_type (int16):
    0 = user – job        (application)                      RIÊNG TƯ, chia train/test
    1 = job  – occupation (map title -> O*NET)               công khai
    2 = occupation – skill (O*NET Technology Skills)         công khai
    3 = user – occupation (user_history.JobTitle -> nghề)    RIÊNG TƯ
  Mỗi cạnh lưu 2 chiều (a->b, b->a) cùng edge_type -> số cạnh có hướng = 2 x vô hướng.

Kỹ năng phía user là SUY QUA NGHỀ (job title -> occupation -> skill), KHÔNG phải tự
khai; user chạm skill qua 2 bước nhảy user–occupation–skill. Ghi rõ trong meta.json.

Artifacts (artifacts/v3/):
  graph.npz          ma trận/vector chỉ số + cạnh + mặt nạ train/test
  clients.json       danh sách client (employer) kèm thống kê, sắp theo n_apps giảm dần
  job_titles.json    {"<job_id>": {title, city, state, employer}} cho job trong P1
  user_titles.json   {"<user_id>": {title, occupation}} — title gần nhất từ user_history
  meta.json          toàn bộ thống kê, cấu hình, cảnh báo, thời điểm chạy

Chạy:
    python src/prepare_v3.py
    python src/prepare_v3.py --limit-jobs 100000      # chạy thử nhanh
"""

from __future__ import annotations

import argparse
import array
import csv
import html
import json
import re
import sys
import time
import unicodedata
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------
# 0. Hằng số đường dẫn + tiện ích
# ---------------------------------------------------------------------
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(r"E:\2026\DUT\IOT\Cuoiki\NewData")
ONET_ZIP = ROOT / "_newdata_audit" / "t4_verify" / "db_29_3_text.zip"
OUT_DIR = ROOT / "artifacts" / "v3"

VERSION = "v3.1"
TEST_RATIO = 0.2
MIN_APPS_FOR_TEST = 5


def banner(title: str) -> None:
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78, flush=True)


def step(msg: str) -> None:
    print(f"  · {msg}", flush=True)


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def rss_mb() -> float | None:
    """RAM thực tế (WorkingSetSize) của tiến trình — để cảnh báo ngưỡng 3 GB.

    Lưu ý: phải khai báo argtypes/restype, nếu không trên x64 con trỏ HANDLE
    bị cắt còn 32 bit và GetProcessMemoryInfo trả 0.
    """
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        k32 = ctypes.WinDLL("kernel32")
        psapi = ctypes.WinDLL("psapi")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.GetCurrentProcess.argtypes = []
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD
        ]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        ok = psapi.GetProcessMemoryInfo(
            k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb
        )
        if not ok:
            return None
        return float(pmc.WorkingSetSize) / (1024 * 1024)
    except Exception:  # pragma: no cover — log là phụ, không được làm hỏng pipeline
        return None


class MemWatch:
    def __init__(self) -> None:
        self.peak = rss_mb() or 0.0

    def tick(self, tag: str = "") -> float:
        cur = rss_mb() or 0.0
        self.peak = max(self.peak, cur)
        if tag:
            step(f"RAM {cur:,.0f} MB (đỉnh {self.peak:,.0f} MB) — {tag}")
        return cur


MEM = MemWatch()


# ---------------------------------------------------------------------
# 1. Chuẩn hoá text
# ---------------------------------------------------------------------
TAG_RX = re.compile(r"<[^>]{0,800}>")
MOJI_RX = re.compile("[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f]")
WS_RX = re.compile(r"\s+")


def detag(text: str) -> str:
    """Bỏ HTML tag, entity, mojibake, và escape literal dạng '\\r' '\\n'."""
    if not text:
        return ""
    t = TAG_RX.sub(" ", text)
    t = t.replace("\\r", " ").replace("\\n", " ").replace("\\t", " ")
    t = html.unescape(t)
    t = MOJI_RX.sub(" ", t)
    return WS_RX.sub(" ", t).strip()


# --- BƯỚC 1: trích employer -------------------------------------------
LEGAL = (
    r"(?:Inc|LLC|L\.L\.C\.?|Corp|Corporation|Company|Co|Ltd|Limited|LLP|L\.P\.?|LP|"
    r"Group|Holdings|Enterprises|Associates|Partners|PLC|GmbH|AG|SA|NV|BV)"
)
LEGAL_TAIL = (
    r"(?:Inc|LLC|Corp|Corporation|Company|Ltd|Limited|LLP|LP|Group|Holdings|"
    r"Enterprises|Partners|PLC|GmbH)"
)
# "TMR, Inc. is ..." ở ĐẦU câu
RX_LEGAL_HEAD = re.compile(r"^(.{3,70}?)[\s,]+" + LEGAL + r"\.?(?=[\s,;:)\-–—\"'”’]|$)")
# Hậu tố pháp lý NEO Ở CUỐI: "Thomaston CT026274 Treadwell Corporation"
RX_LEGAL_SUFFIX = re.compile(
    r"((?:[A-Z][\w&'\.\-]*\s+){1,3}" + LEGAL_TAIL + r"\.?)(?=[\s,;:)\-–—\"'”’]|$)"
)
# "X is a/the ..." , "X, Inc. is ..."
RX_IS_A = re.compile(
    r"^(.{3,62}?)(?:\s*,\s*" + LEGAL + r"\.?)?\s*(?:is|are)\s+"
    r"(?:a|an|the|one|now|currently|seeking|looking|hiring|proud|committed|dedicated|"
    r"national|leading|growing|global|full-service|premier|well|recognized)\b",
    re.I,
)
# "X seeks ..." , "X is seeking ..."
RX_SEEKS = re.compile(
    r"^(.{3,62}?)\s+(?:seeks|is seeking|is currently seeking|currently seeks|"
    r"is looking for|is hiring|has an opening|has openings)\b",
    re.I,
)
RX_ABOUT = re.compile(
    r"(?:about us|company summary|company overview|who we are)\s*[:\-•]?\s*"
    r"([A-Z][\w&.,'\- ]{3,60})",
    re.I,
)
RX_EMAIL = re.compile(r"[\w.\-+]+@([\w\-]{2,40})\.([a-z]{2,6})\b", re.I)
RX_WEB = re.compile(
    r"(?:https?://|www\.)([a-z0-9][\w\-]{1,40}\.(?:com|net|org|us|biz|info|co))\b", re.I
)
RX_ALLCAPS = re.compile(
    r"^([A-Z][A-Z&'\.\-]*(?:\s+[A-Z][A-Z&'\.\-]*){0,4})\s*"
    r"(?:[-–—,]|\s+(?:is|has|seeks|comes|come|now)\b)"
)

# Domain headhunt / staffing / cổng tuyển dụng / mail cá nhân:
# KHÔNG phải tên nhà tuyển dụng.
HEADHUNT_DOMAINS = {
    "randstadusa.com", "roberthalf.com", "volt.com", "kellyservices.com", "adecco.com",
    "manpower.com", "aerotek.com", "kforce.com", "teksystems.com", "insightglobal.com",
    "staffmark.com", "job.com", "monster.com", "careerbuilder.com", "indeed.com",
    "snagajob.com", "hire.com", "aol.com", "yahoo.com", "gmail.com", "hotmail.com",
    "msn.com",
    # phát hiện thêm trong dữ liệu (đều là staffing / cổng tuyển dụng)
    "adeccona.com", "rht.com", "accountemps.com", "ajilon.com", "modis.com", "rhi.com",
    "officeteam.com", "experis.com", "collabera.com", "roberthalflegal.com",
    "careerlisterapp.com", "nigelfrank.com", "accountingprincipals.com",
    "parkerlynch.com", "superiorgroup.com", "randstad.com", "manpowergroup.com",
    "adeccousa.com", "kellyservices.us", "spherion.com", "selectstaffing.com",
    "coremedicalgroup.com", "technisource.com", "mergisgroup.com", "ashleyellis.com",
    "dart.net", "sms.com", "jobs.com", "jobsearch.com", "hcareers.com", "jobs.net",
    "free-ads.com", "classifieds.com", "simplyhired.com", "ziprecruiter.com",
    "superiorjobs.com", "peopleanswers.com", "aerotekcareers.com",
    "randstadcareers.com",
    # nền tảng / ATS / placeholder
    "site.com", "example.com", "yoursite.com", "mycompany.com", "company.com",
    "email.com", "domain.com", "website.com", "ourwebsite.com", "google.com",
    "facebook.com", "twitter.com", "linkedin.com", "youtube.com", "apple.com",
    "microsoft.com", "taleo.net", "ultipro.com", "kronos.com", "workday.com",
    "icims.com", "brassring.com", "kenexa.com", "successfactors.com", "recruit.com",
    "apply.com", "application.com",
}
FREE_MAIL = {
    "aol.com", "yahoo.com", "gmail.com", "hotmail.com", "msn.com", "live.com",
    "outlook.com", "comcast.net", "att.net", "verizon.net", "me.com", "icloud.com",
    "sbcglobal.net", "bellsouth.net", "charter.net", "cox.net", "earthlink.net",
    "juno.com", "mac.com", "protonmail.com",
}
BAD_TLD = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".css", ".js", ".html", ".htm")

# Nhãn mở đầu thường gặp -> bỏ trước khi xét.
PREFIX_RX = re.compile(
    r"^(?:!+\*?!*|[*•·\-–—:>\s]+|job classification\s*:\s*[^|]*|job description\s*:?\s*|"
    r"position description\s*:?\s*|description\s*:?\s*|about\s+(?:us\s*:?\s*)?|"
    r"who we are\s*[:\-•]?\s*|overview\s*:?\s*|summary\s*:?\s*|company\s*:?\s*|"
    r"employer\s*:?\s*|organization\s*:?\s*|macy's overview\s*:?\s*)",
    re.I,
)

# Cụm LUÔN là rác (khớp substring trên tên đã lowercase).
HARD_NOISE = (
    "our client", "my client", "the client", "a client", "this client", "if you",
    "a growing company", "confidential", "now hiring", "immediate opening", "no corp",
    "equal opportunity", "eeo", "apply now", "click here", "job description",
    "job summary", "position summary", "job overview", "position overview",
    "responsibilities", "qualifications", "company summary", "company overview",
    "job classification", "direct hire", "contract to hire", "temp to hire",
    "full time", "part time", "temporary", "permanent", "overview:", "summary:",
    "whether you", "currently we", "who we are", "about us", "our company", "our team",
    "our employees", "our customer", "our retail", "our progressive", "we are",
    "we're", "we have", "we offer", "join us", "join our", "apply today",
    "salary", "benefits", "compensation", "location:", "monday", "tuesday",
    "weekend", "@",
)
# Từ chức năng: chỉ là rác khi cả tên chỉ gồm các từ này (hoặc đứng ở hai đầu
# mà không có hậu tố pháp lý).
STOP_TOKENS = {
    "the", "a", "an", "this", "that", "these", "those", "we", "our", "you", "your", "my",
    "their", "it", "its", "is", "are", "and", "or", "of", "for", "with", "in", "on", "at",
    "to", "from", "if", "as", "be", "will", "must", "have", "has", "please", "note",
    "description", "summary", "overview", "location", "compensation", "benefits",
    "requirements", "position", "job", "opening", "openings", "hiring", "immediate",
    "various", "multiple", "not", "no", "all", "any", "new", "many", "some", "now",
    "currently", "here", "there", "who", "what", "when", "where", "why", "how", "also",
    "may", "can", "should", "would", "upscale", "prominent", "leading", "major",
}
# Danh từ chung ở CUỐI tên.
GENERIC_TAIL = {
    "company", "companies", "corporation", "corp", "organization", "organisation",
    "employer", "client", "firm", "group", "agency", "business", "enterprise", "service",
    "services", "industry", "solutions", "provider", "leader", "department", "division",
    "team", "staff", "opportunity", "career", "recruiter", "staffing", "contractor",
    "franchise", "professional", "specialist", "associate", "associates",
}
GENERIC_ADJ = {
    "growing", "established", "national", "regional", "local", "leading", "premier",
    "fortune", "large", "small", "mid", "sized", "well", "dynamic", "successful",
    "rapidly", "fast", "global", "international", "major", "top", "new", "private",
    "public", "energy", "manufacturing", "healthcare", "health", "financial", "retail",
    "technology", "software", "it", "medical", "engineering", "consulting", "commercial",
    "residential", "industrial", "automotive", "food", "insurance", "banking", "legal",
    "nonprofit", "certified", "payment", "processing", "stable", "reputable",
    "innovative", "join", "world's", "worlds", "largest", "car", "rental", "great",
    "place", "work", "workplace", "best", "one", "upscale", "prominent", "award",
    "winning", "solutions", "consumer",
}
# Từ chỉ CHỨC DANH — có mặt thì gần như chắc chắn là tiêu đề tin, không phải công ty.
ROLE_WORDS = {
    "sales", "associate", "associates", "professional", "technician", "engineer",
    "manager", "driver", "drivers", "nurse", "specialist", "coordinator", "assistant",
    "clerk", "representative", "accountant", "developer", "analyst", "consultant",
    "supervisor", "director", "administrator", "teacher", "cook", "server", "cashier",
    "receptionist", "welder", "mechanic", "operator", "inspector", "agent", "recruiter",
    "hvac", "cdl", "rn", "lpn", "cna", "customer", "service", "staffing", "teller",
    "designer", "architect", "therapist", "pharmacist", "attorney", "paralegal",
    "scientist", "chemist", "plumber", "electrician", "carpenter", "painter",
    "housekeeping", "dishwasher", "barista", "bartender", "host", "hostess", "intern",
    "apprentice", "trainee", "helper", "laborer", "warehouse", "picker", "packer",
    "positions", "position", "opening", "openings", "vendor", "prep",
}
LEGAL_RE = re.compile(r"^(.*?)[\s,]+" + LEGAL + r"\.?$", re.I)


def clean_employer_name(raw: str, is_domain: bool = False) -> str | None:
    """Chuẩn hoá + lọc một ứng viên tên nhà tuyển dụng. None nếu là rác."""
    if not raw:
        return None
    s = detag(raw)
    if not s:
        return None
    s = PREFIX_RX.sub("", s).strip()
    if not s:
        return None
    s = re.sub(r"\([^)]{0,50}\)", " ", s)               # bỏ ngoặc (M/F/D), (Remote)...
    s = s.replace("®", "").replace("™", "").replace("©", "")
    s = s.strip(" ,.;:-–—\"'“”‘’|/\\&+* \t!•")
    s = WS_RX.sub(" ", s)
    if not s or len(s) > 70:
        return None
    low = s.lower()
    low = re.sub(r"(?<=[a-z0-9])\.(?=\s|$)", "", low)   # "Inc." -> "inc"
    low = WS_RX.sub(" ", low).strip(" ,.;:-")
    if len(low) < 3 or len(low) > 55:
        return None
    if any(n in low for n in HARD_NOISE):
        return None
    toks = low.split()
    if not toks or len(toks) > 7:
        return None
    if all(t in STOP_TOKENS for t in toks):
        return None

    has_legal = bool(LEGAL_RE.match(low))
    if has_legal:
        # Phần trước hậu tố pháp lý phải có ít nhất 1 từ là tên riêng,
        # nếu không "the company" / "fast growing company" sẽ lọt qua.
        head_toks = LEGAL_RE.match(low).group(1).split()
        if not head_toks:
            return None
        if all(
            t in STOP_TOKENS or t in GENERIC_ADJ or t in GENERIC_TAIL or t in ROLE_WORDS
            for t in head_toks
        ):
            return None
    if not is_domain and not has_legal:
        if any(t in ROLE_WORDS for t in toks):
            return None
        if toks[-1] in GENERIC_TAIL:
            head = toks[:-1]
            if not head or all(t in STOP_TOKENS or t in GENERIC_ADJ for t in head):
                return None
        if toks[0] in STOP_TOKENS or toks[-1] in STOP_TOKENS:
            return None
    if len(toks) == 1 and toks[0] in GENERIC_TAIL | GENERIC_ADJ | STOP_TOKENS:
        return None
    if not re.search(r"[a-z]", low):
        return None
    if re.fullmatch(r"[\d\W]+", low):
        return None
    if not is_domain and not has_legal and not re.search(r"[A-Z]", s):
        return None                                 # phải trông như tên riêng
    return low


def employer_from_text(desc: str, req: str) -> tuple[str | None, str | None]:
    """Trả (tên đã chuẩn hoá, nguồn trích) từ Description + Requirements của 1 job."""
    d = detag(desc)
    if not d:
        return None, None
    head = d[:700]
    first = re.split(r"(?<=[.!?])\s+|\s{2,}", head, maxsplit=1)[0][:220]

    # Ưu tiên 1: hậu tố pháp lý ở đầu câu ("TMR, Inc. is ...") — tín hiệu mạnh nhất.
    for text, src in ((first, "S1_legal_dau_cau"), (head, "S1_legal_dau_mo_ta")):
        m = RX_LEGAL_HEAD.match(text)
        if m:
            name = clean_employer_name(m.group(0)[: m.end()])
            if name:
                return name, src
    # Ưu tiên 2: "X is a/the ..."
    m = RX_IS_A.match(first)
    if m:
        name = clean_employer_name(m.group(1))
        if name:
            return name, "S2_is_a"
    # Ưu tiên 3: "X seeks ..."
    m = RX_SEEKS.match(first)
    if m:
        name = clean_employer_name(m.group(1))
        if name:
            return name, "S3_seeks"
    # Ưu tiên 4: tên VIẾT HOA TOÀN BỘ ở đầu ("CITY BEVERAGES Come to work ...")
    m = RX_ALLCAPS.match(first)
    if m:
        name = clean_employer_name(m.group(1))
        if name:
            return name, "S6_viet_hoa"
    # Ưu tiên 5: hậu tố pháp lý NEO Ở CUỐI câu đầu
    for m in RX_LEGAL_SUFFIX.finditer(first):
        name = clean_employer_name(m.group(1))
        if name:
            return name, "S7_hau_to_cuoi"
    # Ưu tiên 6: khối "About us: ..."
    m = RX_ABOUT.search(head)
    if m:
        name = clean_employer_name(m.group(1))
        if name:
            return name, "S4_about_us"
    # Ưu tiên 7-8: domain email rồi domain website (đã loại headhunt + mail cá nhân)
    blob = d[:5000] + " " + detag(req)[:3000]
    for dom, tld in RX_EMAIL.findall(blob):
        full = f"{dom}.{tld}".lower().lstrip(".")
        if full in HEADHUNT_DOMAINS or full in FREE_MAIL:
            continue
        if full.endswith(BAD_TLD):
            continue
        name = clean_employer_name(full, is_domain=True)
        if name:
            return name, "S5_domain_email"
    for dom in RX_WEB.findall(blob):
        full = dom.lower().lstrip(".")
        if full in HEADHUNT_DOMAINS or full in FREE_MAIL:
            continue
        name = clean_employer_name(full, is_domain=True)
        if name:
            return name, "S8_domain_website"
    return None, None


# --- BƯỚC 2: chuẩn hoá title nghề -------------------------------------
GENDER_RX = re.compile(r"\((?:m|f|d|w|m/w/d|m/f/d|m/f|x|gn|all genders)\)", re.I)
REMOTE_RX = re.compile(r"\((?:remote|hybrid|onsite|on-site|wfh)\)", re.I)
YEAR_RX = re.compile(r"\b(19|20)\d{2}\b")
NONWORD_RX = re.compile(r"[^a-z0-9+#. ]+")


def norm_title(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = GENDER_RX.sub(" ", s)
    s = REMOTE_RX.sub(" ", s)
    s = YEAR_RX.sub(" ", s)
    s = s.replace("&", " and ")
    s = NONWORD_RX.sub(" ", s)
    return WS_RX.sub(" ", s).strip()


def loose_title(s: str) -> str:
    """Map lỏng: cắt tại -/|/, rồi bỏ 1 token cuối -> tăng phủ."""
    head = re.split(r"[-/|,]", s)[0]
    toks = head.split()
    if len(toks) > 2:
        toks = toks[:-1]
    return " ".join(toks)


# ---------------------------------------------------------------------
# 2. Đọc O*NET từ zip
# ---------------------------------------------------------------------
def zread(z: zipfile.ZipFile, filename: str) -> str:
    for n in z.namelist():
        norm = n.replace("\\", "/")
        if norm == filename or norm.endswith("/" + filename):
            return z.read(n).decode("utf-8", "replace")
    raise FileNotFoundError(filename)


def read_tsv_text(text: str) -> tuple[list[str], list[list[str]]]:
    rd = csv.reader(text.splitlines(), delimiter="\t", quoting=csv.QUOTE_NONE)
    header = next(rd)
    return header, [r for r in rd if r]


def load_onet(zip_path: Path) -> dict:
    """Nạp bảng tra: title -> mã nghề GỐC soc[:7], và nghề -> tập kỹ năng công nghệ."""
    banner("BƯỚC 2+3 — NẠP O*NET (Occupation Data, Alternate Titles, Technology Skills)")
    with zipfile.ZipFile(zip_path) as z:
        occ_h, occ_rows = read_tsv_text(zread(z, "Occupation Data.txt"))
        alt_h, alt_rows = read_tsv_text(zread(z, "Alternate Titles.txt"))
        ts_h, ts_rows = read_tsv_text(zread(z, "Technology Skills.txt"))

    # KHÔNG dùng Skills.txt: 879/879 nghề đủ 35 element -> entropy 0, vô dụng.
    i_code, i_title = occ_h.index("O*NET-SOC Code"), occ_h.index("Title")
    i_acode, i_alt = alt_h.index("O*NET-SOC Code"), alt_h.index("Alternate Title")
    i_short = alt_h.index("Short Title") if "Short Title" in alt_h else -1
    i_tcode, i_ex = ts_h.index("O*NET-SOC Code"), ts_h.index("Example")

    title2soc: dict[str, str] = {}
    soc_title: dict[str, str] = {}
    for r in occ_rows:
        if len(r) <= max(i_code, i_title):
            continue
        soc_title[r[i_code]] = r[i_title]
        t = norm_title(r[i_title])
        if t:
            title2soc.setdefault(t, r[i_code])
    for r in alt_rows:
        if len(r) <= max(i_acode, i_alt):
            continue
        for raw in (r[i_alt], r[i_short] if 0 <= i_short < len(r) else ""):
            t = norm_title(raw)
            if t:
                title2soc.setdefault(t, r[i_acode])
    title2soc_loose: dict[str, str] = {}
    for t, soc in title2soc.items():
        lt = loose_title(t)
        if lt:
            title2soc_loose.setdefault(lt, soc)

    # Kỹ năng: gom theo mã GỐC soc[:7] — NHẤT QUÁN với nút nghề.
    occ_skills: dict[str, set[str]] = {}
    for r in ts_rows:
        if len(r) <= max(i_tcode, i_ex):
            continue
        s7 = r[i_tcode][:7]
        ex = r[i_ex].strip()
        if ex:
            occ_skills.setdefault(s7, set()).add(ex)

    n_tools = len({s for v in occ_skills.values() for s in v})
    step(f"Occupation Data: {len(occ_rows):,} dòng, {len(soc_title):,} mã nghề (đầy đủ)")
    step(f"Alternate Titles: {len(alt_rows):,} dòng -> {len(title2soc):,} khoá title")
    step(f"Technology Skills: {len(ts_rows):,} dòng -> {len(occ_skills):,} nghề soc[:7], "
         f"{n_tools:,} kỹ năng phân biệt")

    return {
        "title2soc": title2soc,
        "title2soc_loose": title2soc_loose,
        "soc_title": soc_title,
        "occ_skills": occ_skills,
        "n_occ_onet": len(soc_title),
        "n_skill_onet": n_tools,
    }


def map_title_to_soc(title: str, onet: dict) -> str | None:
    """Map title tự do -> mã nghề: thử khớp chặt trước, rồi khớp lỏng."""
    t = norm_title(title)
    if not t:
        return None
    soc = onet["title2soc"].get(t)
    if soc:
        return soc
    return onet["title2soc_loose"].get(loose_title(t))


# ---------------------------------------------------------------------
# 3. Quét jobs.tsv (streaming, KHÔNG pandas)
# ---------------------------------------------------------------------
def scan_jobs(path: Path, onet: dict, limit: int = 0) -> dict:
    banner("BƯỚC 1 — QUÉT jobs.tsv: TRÍCH EMPLOYER + MAP NGHỀ")
    t0 = time.perf_counter()
    job_index: dict[str, int] = {}
    job_ids: list[str] = []
    emp_names: list[str] = []
    emp_lookup: dict[str, int] = {}
    emp_id = array.array("i")          # employer id theo job index (-1 nếu không có)
    soc_id = array.array("i")          # chỉ số trong soc7_list (-1 nếu không map được)
    soc7_list: list[str] = []
    soc7_lookup: dict[str, int] = {}
    # Metadata hiển thị: chỉ giữ cho job CÓ employer (đó là điều kiện vào P1),
    # để không phải giữ 1,09 triệu bộ ba chuỗi trong RAM.
    meta_by_job: dict[int, tuple[str, str, str]] = {}
    src_counter: Counter = Counter()
    n_rows = n_unique = n_soc = n_emp = n_bad = 0

    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        header = next(rd)
        i_id, i_title = header.index("JobID"), header.index("Title")
        i_desc, i_req = header.index("Description"), header.index("Requirements")
        i_city = header.index("City") if "City" in header else -1
        i_state = header.index("State") if "State" in header else -1
        width = len(header)
        for row in rd:
            n_rows += 1
            if len(row) != width:
                n_bad += 1
                continue
            jid = row[i_id]
            if jid in job_index:       # JobID trùng -> chỉ giữ bản ghi đầu
                continue
            job_index[jid] = n_unique
            job_ids.append(jid)
            j_idx = n_unique
            n_unique += 1

            soc = map_title_to_soc(row[i_title], onet)
            if soc:
                n_soc += 1
                s7 = soc[:7]
                sid = soc7_lookup.get(s7)
                if sid is None:
                    sid = len(soc7_list)
                    soc7_lookup[s7] = sid
                    soc7_list.append(s7)
            else:
                sid = -1
            soc_id.append(sid)

            name, src = employer_from_text(row[i_desc], row[i_req])
            if name:
                n_emp += 1
                src_counter[src] += 1
                eid = emp_lookup.get(name)
                if eid is None:
                    eid = len(emp_names)
                    emp_lookup[name] = eid
                    emp_names.append(name)
                meta_by_job[j_idx] = (
                    detag(row[i_title])[:180],
                    (row[i_city].strip()[:60] if i_city >= 0 else ""),
                    (row[i_state].strip()[:20] if i_state >= 0 else ""),
                )
            else:
                eid = -1
            emp_id.append(eid)

            if limit and n_unique >= limit:
                break
            if n_unique % 200000 == 0:
                step(f"...{n_unique:,} job | có nghề {n_soc:,} | có employer {n_emp:,} "
                     f"| {time.perf_counter() - t0:,.0f}s")
                MEM.tick()

    dt = time.perf_counter() - t0
    step(f"Quét {n_rows:,} dòng -> {n_unique:,} JobID duy nhất "
         f"({n_bad:,} dòng sai số cột) trong {dt:,.0f}s")
    step(f"Map được nghề: {n_soc:,} ({100.0 * n_soc / max(n_unique, 1):.2f}%) — "
         f"{len(soc7_list):,} mã nghề soc[:7]")
    step(f"Trích được employer: {n_emp:,} ({100.0 * n_emp / max(n_unique, 1):.2f}%) — "
         f"{len(emp_names):,} tên phân biệt")
    step(f"Nguồn trích: {dict(src_counter)}")
    MEM.tick("sau khi quét jobs.tsv")

    return {
        "n_rows": n_rows,
        "n_jobs": n_unique,
        "bad_rows": n_bad,
        "job_index": job_index,
        "job_ids": job_ids,
        "emp_id": emp_id,
        "emp_names": emp_names,
        "soc_id": soc_id,
        "soc7_list": soc7_list,
        "n_jobs_with_soc": n_soc,
        "n_jobs_with_emp": n_emp,
        "src_counter": src_counter,
        "meta_by_job": meta_by_job,
        "seconds": dt,
    }


# ---------------------------------------------------------------------
# 4. Quét apps.tsv
# ---------------------------------------------------------------------
def scan_apps(path: Path, jobs: dict, min_apps: int, onet: dict) -> dict:
    banner("BƯỚC 4 — QUÉT apps.tsv: GHÉP USER-JOB, ĐẾM APPLICATION THEO EMPLOYER")
    t0 = time.perf_counter()
    job_index = jobs["job_index"]
    emp_id = np.frombuffer(jobs["emp_id"], dtype=np.int32)
    emp_names = jobs["emp_names"]

    users: dict[str, int] = {}
    user_ids: list[str] = []
    u_arr = array.array("i")
    j_arr = array.array("i")
    n_rows = n_bad = n_with_job = n_with_emp = 0

    with open(path, encoding="utf-8", newline="") as f:
        rd = csv.reader(f, delimiter="\t")
        header = next(rd)
        i_u, i_j = header.index("UserID"), header.index("JobID")
        for row in rd:
            if len(row) <= max(i_u, i_j):
                n_bad += 1
                continue
            n_rows += 1
            j = job_index.get(row[i_j])
            if j is None:
                continue
            n_with_job += 1
            if int(emp_id[j]) < 0:
                continue
            n_with_emp += 1
            uid = users.get(row[i_u])
            if uid is None:
                uid = len(users)
                users[row[i_u]] = uid
                user_ids.append(row[i_u])
            u_arr.append(uid)
            j_arr.append(j)

    step(f"{n_rows:,} dòng application ({n_bad:,} dòng thiếu cột)")
    step(f"Job có trong jobs.tsv: {n_with_job:,} "
         f"({100.0 * n_with_job / max(n_rows, 1):.2f}%)")
    step(f"Job + có employer: {n_with_emp:,} "
         f"({100.0 * n_with_emp / max(n_rows, 1):.2f}%)")
    step(f"User phân biệt: {len(users):,}")

    # --- gộp application trùng (user, job)
    u_np = np.frombuffer(u_arr, dtype=np.int32)
    j_np = np.frombuffer(j_arr, dtype=np.int32)
    del u_arr, j_arr
    key = u_np.astype(np.int64) * np.int64(jobs["n_jobs"]) + j_np.astype(np.int64)
    _, first_idx = np.unique(key, return_index=True)
    first_idx.sort()
    n_dup = len(key) - len(first_idx)
    u_np, j_np = u_np[first_idx], j_np[first_idx]
    step(f"App trùng (user, job) gộp: {n_dup:,} -> {len(u_np):,} cặp duy nhất")

    # --- ngưỡng application / employer (đếm trên cặp duy nhất)
    # Chỉ đếm trên job thuộc P1 (có employer + map được nghề có kỹ năng), để
    # ngưỡng client và tập job của đồ thị nói về CÙNG một tập quan sát.
    p1_job = valid_p1_job_mask(jobs, onet, np.ones(len(emp_names), dtype=bool))
    in_p1 = p1_job[j_np]
    step(f"Cặp (user, job) có job thuộc P1: {int(in_p1.sum()):,} / {len(u_np):,}")
    u_np, j_np = u_np[in_p1], j_np[in_p1]

    pair_emp = emp_id[j_np]
    cnt_pair = np.bincount(pair_emp, minlength=len(emp_names))
    keep_emp = cnt_pair >= min_apps
    mask = keep_emp[pair_emp]
    step(f"Ngưỡng >= {min_apps} app: giữ {int(keep_emp.sum()):,} / {len(emp_names):,} employer")
    u_np, j_np, pair_emp = u_np[mask], j_np[mask], pair_emp[mask]
    step(f"Cặp (user, job) thuộc client hợp lệ: {len(u_np):,} "
         f"({100.0 * len(u_np) / max(n_rows, 1):.2f}% tổng app)")
    MEM.tick("sau khi quét apps.tsv")

    return {
        "n_rows": n_rows,
        "n_bad": n_bad,
        "n_with_job": n_with_job,
        "n_with_emp": n_with_emp,
        "n_p1_pairs": int(in_p1.sum()),
        "n_apps_kept": int(len(u_np)),
        "n_dup": int(n_dup),
        "users": users,
        "user_ids": user_ids,
        "u": u_np,
        "j": j_np,
        "pair_emp": pair_emp,
        "cnt_pair": cnt_pair,
        "keep_emp": keep_emp,
        "seconds": time.perf_counter() - t0,
    }


# ---------------------------------------------------------------------
# 5. Chia client theo employer
# ---------------------------------------------------------------------
def build_clients(apps: dict, jobs: dict, min_apps: int) -> dict:
    banner("BƯỚC 4b — DỰNG CLIENT (1 EMPLOYER = 1 CLIENT) VÀ ĐÁNH LẠI CHỈ SỐ NÚT")
    emp_names = jobs["emp_names"]
    keep_emp = apps["keep_emp"]
    cnt_pair = apps["cnt_pair"]

    kept_emp = np.flatnonzero(keep_emp)
    # sắp theo số application GIẢM DẦN; hoà -> theo tên (deterministic)
    order = sorted(kept_emp.tolist(), key=lambda e: (-int(cnt_pair[e]), emp_names[e]))
    client_of_emp = {e: c for c, e in enumerate(order)}
    n_clients = len(order)
    step(f"Số client: {n_clients:,} (employer có >= {min_apps} application)")

    pair_emp = apps["pair_emp"]
    client_of_pair = np.fromiter(
        (client_of_emp[int(e)] for e in pair_emp), dtype=np.int32, count=len(pair_emp)
    )

    # --- user / job giữ lại, sắp tăng dần để deterministic
    kept_u = np.unique(apps["u"])
    kept_j = np.unique(apps["j"])
    step(f"User có quan sát: {len(kept_u):,} | Job có quan sát: {len(kept_j):,}")

    u_rank = np.full(int(kept_u.max()) + 1, -1, dtype=np.int32)
    u_rank[kept_u] = np.arange(len(kept_u), dtype=np.int32)
    j_rank = np.full(int(kept_j.max()) + 1, -1, dtype=np.int32)
    j_rank[kept_j] = np.arange(len(kept_j), dtype=np.int32)
    u_idx = u_rank[apps["u"]]
    j_idx = j_rank[apps["j"]]

    # --- thống kê client
    n_apps_c = np.bincount(client_of_pair, minlength=n_clients)
    n_users_c = np.bincount(
        np.unique(client_of_pair.astype(np.int64) * np.int64(len(kept_u)) + u_idx)
        // np.int64(len(kept_u)),
        minlength=n_clients,
    )
    n_jobs_c = np.bincount(
        np.unique(client_of_pair.astype(np.int64) * np.int64(len(kept_j)) + j_idx)
        // np.int64(len(kept_j)),
        minlength=n_clients,
    )

    # --- client của job
    client_of_job = np.full(len(kept_j), -1, dtype=np.int32)
    client_of_job[j_idx] = client_of_pair

    # --- client của user = client có NHIỀU app nhất (hoà -> client_id nhỏ hơn)
    uniq_cu, cnt_cu = np.unique(
        np.stack([u_idx, client_of_pair], axis=1), axis=0, return_counts=True
    )
    ord_cu = np.lexsort((uniq_cu[:, 1], -cnt_cu, uniq_cu[:, 0]))
    us, cs = uniq_cu[ord_cu, 0], uniq_cu[ord_cu, 1]
    first_pos = np.unique(us, return_index=True)[1]
    client_of_user = np.full(len(kept_u), -1, dtype=np.int32)
    client_of_user[us[first_pos]] = cs[first_pos].astype(np.int32)

    n_clients_per_user = np.bincount(us, minlength=len(kept_u))
    multi_users = int((n_clients_per_user > 1).sum())
    step(f"User ứng tuyển ở >1 client (cross-silo tự nhiên): {multi_users:,} "
         f"({100.0 * multi_users / max(len(kept_u), 1):.1f}%)")

    clients = [
        {
            "client_id": c,
            "employer_name": emp_names[e],
            "n_apps": int(n_apps_c[c]),
            "n_users": int(n_users_c[c]),
            "n_jobs": int(n_jobs_c[c]),
        }
        for c, e in enumerate(order)
    ]
    if clients:
        step(f"Client lớn nhất: {clients[0]['employer_name']} ({clients[0]['n_apps']:,} app); "
             f"nhỏ nhất: {clients[-1]['employer_name']} ({clients[-1]['n_apps']:,} app)")

    return {
        "clients": clients,
        "n_clients": n_clients,
        "client_of_pair": client_of_pair,
        "client_of_job": client_of_job,
        "client_of_user": client_of_user,
        "kept_u": kept_u,
        "kept_j": kept_j,
        "u_idx": u_idx,
        "j_idx": j_idx,
        "n_apps_c": n_apps_c,
        "multi_users": multi_users,
        "n_clients_per_user": n_clients_per_user,
    }


# ---------------------------------------------------------------------
# 6. Quét user_history.tsv -> cạnh user-nghề
# ---------------------------------------------------------------------
def scan_history(path: Path, onet: dict, apps: dict, cl: dict) -> dict:
    banner("BƯỚC 3b — QUÉT user_history.tsv: USER -> NGHỀ (suy kỹ năng qua nghề)")
    t0 = time.perf_counter()
    users = apps["users"]
    kept_u = cl["kept_u"]
    occ_index = cl["occ_index"]

    # uid nội bộ -> chỉ số nút user
    uid2node = np.full(len(users), -1, dtype=np.int32)
    uid2node[kept_u] = np.arange(len(kept_u), dtype=np.int32)

    u_arr = array.array("i")
    o_arr = array.array("i")
    # title gần nhất theo Sequence, cho mọi user trong đồ thị
    latest_seq = np.full(len(kept_u), -1, dtype=np.int64)
    latest_title: list[str] = [""] * len(kept_u)
    latest_soc: list[str] = [""] * len(kept_u)
    n_rows = n_mapped_title = n_mapped_occ = 0

    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f, delimiter="\t")
        header = next(rd)
        i_u, i_t = header.index("UserID"), header.index("JobTitle")
        i_seq = header.index("Sequence") if "Sequence" in header else -1
        for row in rd:
            if len(row) <= max(i_u, i_t):
                continue
            n_rows += 1
            uid = users.get(row[i_u])
            if uid is None:
                continue
            node = int(uid2node[uid])
            if node < 0:
                continue

            # title gần nhất (Sequence lớn nhất; thiếu cột -> lấy dòng cuối)
            seq = int(row[i_seq]) if i_seq >= 0 and row[i_seq].strip().isdigit() else n_rows
            if seq >= latest_seq[node]:
                latest_seq[node] = seq
                latest_title[node] = detag(row[i_t])[:180]
                soc_latest = map_title_to_soc(row[i_t], onet)
                latest_soc[node] = soc_latest[:7] if soc_latest else ""

            soc = map_title_to_soc(row[i_t], onet)
            if not soc:
                continue
            n_mapped_title += 1
            oi = occ_index.get(soc[:7])
            if oi is None:                 # nghề không có trong đồ thị -> bỏ
                continue
            n_mapped_occ += 1
            u_arr.append(node)
            o_arr.append(oi)

    step(f"{n_rows:,} dòng user_history | map được nghề {n_mapped_title:,} "
         f"({100.0 * n_mapped_title / max(n_rows, 1):.2f}%)")
    step(f"Nghề nằm trong đồ thị: {n_mapped_occ:,} dòng -> gộp cặp (user, nghề)")
    MEM.tick("sau khi quét user_history.tsv")

    u = np.frombuffer(u_arr, dtype=np.int32) if len(u_arr) else np.zeros(0, np.int32)
    o = np.frombuffer(o_arr, dtype=np.int32) if len(o_arr) else np.zeros(0, np.int32)
    return {
        "n_rows": n_rows,
        "n_mapped_title": n_mapped_title,
        "n_mapped_occ": n_mapped_occ,
        "u": u,
        "o": o,
        "latest_title": latest_title,
        "latest_soc": latest_soc,
        "n_users_with_title": int(sum(1 for t in latest_title if t)),
        "seconds": time.perf_counter() - t0,
    }


# ---------------------------------------------------------------------
# 7. Dựng đồ thị
# ---------------------------------------------------------------------
def collect_occupations(jobs: dict, kept_j: np.ndarray, onet: dict) -> tuple[list[str], dict]:
    """Tập nghề của các job còn trong đồ thị.

    Giữ MỌI mã nghề map được (kể cả nghề không có kỹ năng công nghệ): nghề đó vẫn
    là nút thật và vẫn nối job lên, chỉ là không phát sinh cạnh nghề-kỹ năng.
    Nhờ vậy lớp occupation không bị đứt gãy mà cũng không mất job oan.
    """
    soc_id = np.frombuffer(jobs["soc_id"], dtype=np.int32)
    soc7_list = jobs["soc7_list"]
    present = set()
    for j in kept_j.tolist():
        sid = int(soc_id[j])
        if sid >= 0:
            present.add(soc7_list[sid])
    occ_ids = sorted(present)
    return occ_ids, {s: i for i, s in enumerate(occ_ids)}


def valid_p1_job_mask(jobs: dict, onet: dict, emp_keep: np.ndarray) -> np.ndarray:
    """Mặt nạ job ĐỦ ĐIỀU KIỆN vào P1.

    P1 = job có employer (đã qua lọc >= 2 job). Đây là định nghĩa duy nhất quán:
    mọi job mà một client sở hữu đều là nút trong đồ thị.

    Job nào map được mã nghề thì có thêm đúng 1 cạnh job-occupation; job không
    map được thì KHÔNG có cạnh đó. Tỉ lệ này được báo minh bạch trong meta
    (edges.n_jobs_with_occupation_edge / pct_jobs_with_occupation_edge) chứ
    không âm thầm cắt bớt dữ liệu tương tác.
    """
    soc_id = np.frombuffer(jobs["soc_id"], dtype=np.int32)
    n = len(soc_id)
    if not n:
        return np.zeros(0, dtype=bool)
    return np.frombuffer(jobs["emp_id"], dtype=np.int32) >= 0


def build_graph(onet: dict, jobs: dict, cl: dict, hist: dict, occ_ids: list[str],
                occ_index: dict, seed: int) -> dict:
    banner("BƯỚC 5 — DỰNG ĐỒ THỊ VÀ CHIA TRAIN/TEST")
    occ_skills = onet["occ_skills"]
    kept_j = cl["kept_j"]
    kept_u = cl["kept_u"]
    soc_id = np.frombuffer(jobs["soc_id"], dtype=np.int32)
    soc7_list = jobs["soc7_list"]

    # Nghề không có kỹ năng công nghệ vẫn là nút hợp lệ -> dùng .get(), không [].
    skill_set = sorted({s for o in occ_ids for s in occ_skills.get(o, ())})
    skill_index = {s: i for i, s in enumerate(skill_set)}
    n_occ, n_skill = len(occ_ids), len(skill_set)
    n_u, n_j = len(kept_u), len(kept_j)

    off_user = 0
    off_job = off_user + n_u
    off_occ = off_job + n_j
    off_skill = off_occ + n_occ
    n_nodes = off_skill + n_skill
    step(f"Nút: {n_nodes:,} = {n_u:,} user + {n_j:,} job + {n_occ:,} nghề + {n_skill:,} kỹ năng")

    src = array.array("q")
    dst = array.array("q")
    etype = array.array("h")
    tr = array.array("b")
    te = array.array("b")

    def add(a: int, b: int, t: int, train: bool, test: bool) -> None:
        """Thêm MỘT cạnh vô hướng (1 cột trong edge_index, hướng a->b).

        Đồ thị được đánh dấu is_symmetric=true; bên nạp chỉ cần đối xứng hoá
        một lần (edge_index và edge_index.flip(0)) thay vì lưu 2 chiều ở đây.
        """
        src.append(a); dst.append(b); etype.append(t)
        tr.append(1 if train else 0); te.append(1 if test else 0)

    # --- (0) user - job, chia test theo user
    u_idx, j_idx = cl["u_idx"], cl["j_idx"]
    order = np.lexsort((j_idx, u_idx))
    u_sorted, j_sorted = u_idx[order], j_idx[order]
    bounds = np.flatnonzero(np.diff(u_sorted)) + 1
    groups = np.split(np.arange(len(u_sorted)), bounds)
    rng = np.random.default_rng(seed)
    is_test = np.zeros(len(u_sorted), dtype=bool)
    for g in groups:
        if len(g) >= MIN_APPS_FOR_TEST:
            n_test = max(1, int(round(len(g) * TEST_RATIO)))
            is_test[rng.choice(g, size=n_test, replace=False)] = True
    for k in range(len(u_sorted)):
        add(int(off_user + u_sorted[k]), int(off_job + j_sorted[k]), 0,
            not is_test[k], bool(is_test[k]))
    n_e0 = len(u_sorted)
    step(f"Cạnh user-job: {n_e0:,} ({int((~is_test).sum()):,} train / "
         f"{int(is_test.sum()):,} test) trên {len(np.unique(u_sorted)):,} user")

    # --- (1) job - nghề
    n_e1 = 0
    for jj, jo in enumerate(kept_j.tolist()):
        sid = int(soc_id[jo])
        if sid < 0:
            continue
        oi = occ_index.get(soc7_list[sid])
        if oi is None:
            continue
        add(int(off_job + jj), int(off_occ + oi), 1, True, False)
        n_e1 += 1
    step(f"Cạnh job-nghề: {n_e1:,}")

    # --- (2) nghề - kỹ năng (mã GỐC soc[:7] -> không phồng số cạnh)
    # TẬP kỹ năng là set[str] -> thứ tự lặp phụ thuộc PYTHONHASHSEED, nên phải
    # SẮP XẾP để edge_index tất định giữa các lần chạy (đã kiểm chứng bằng hash).
    n_e2 = 0
    for oi, code in enumerate(occ_ids):
        for sk in sorted(occ_skills.get(code, ())):
            add(int(off_occ + oi), int(off_skill + skill_index[sk]), 2, True, False)
            n_e2 += 1
    step(f"Cạnh nghề-kỹ năng: {n_e2:,}")

    # --- (3) user - nghề (gộp trùng)
    denom = max(n_occ, 1)
    if len(hist["u"]):
        key = hist["u"].astype(np.int64) * np.int64(denom) + hist["o"].astype(np.int64)
        uk = np.unique(key)
        hu = (uk // np.int64(denom)).astype(np.int64)
        ho = (uk % np.int64(denom)).astype(np.int64)
    else:
        hu = np.zeros(0, np.int64)
        ho = np.zeros(0, np.int64)
    for a, b in zip(hu.tolist(), ho.tolist()):
        add(int(off_user + a), int(off_occ + b), 3, True, False)
    n_e3 = len(hu)
    step(f"Cạnh user-nghề: {n_e3:,}")

    # QUY ƯỚC CẠNH (Cách A — chuẩn PyTorch Geometric):
    #   mỗi cạnh VÔ HƯỚNG = đúng 1 cột trong edge_index, 1 phần tử edge_type,
    #   1 phần tử trong train_mask và test_mask. Đồ thị là đối xứng
    #   (is_symmetric=true) -> khi nạp chỉ cần đối xứng hoá một lần.
    #   Nhờ vậy edge_type.shape[0] == edge_index.shape[1] == mask.shape[0],
    #   nên edge_type[train_mask] và mask[edge_index[0]] luôn đúng chỉ số.
    edge_index = np.stack(
        [np.frombuffer(src, dtype=np.int64), np.frombuffer(dst, dtype=np.int64)]
    ).copy()
    edge_type = np.frombuffer(etype, dtype=np.int16).copy()
    train_mask = np.frombuffer(tr, dtype=np.int8).astype(bool).copy()
    test_mask = np.frombuffer(te, dtype=np.int8).astype(bool).copy()
    n_edges = int(edge_index.shape[1])
    ln_e, ln_t, ln_tr, ln_te = n_edges, len(edge_type), len(train_mask), len(test_mask)
    step(f"Tổng cạnh (vô hướng, 1 dòng/cạnh): {n_edges:,} | "
         f"edge_type {ln_t:,} | train {ln_tr:,} | test {ln_te:,}")
    assert ln_e == ln_t == ln_tr == ln_te, (
        f"LỆCH ĐỘ DÀI: edge_index {ln_e}, edge_type {ln_t}, train {ln_tr}, test {ln_te}"
    )
    assert not (train_mask & test_mask).any(), "train_mask và test_mask giao nhau"
    assert bool(train_mask.any()), "train_mask rỗng"

    is_public = np.zeros(n_nodes, dtype=np.int8)
    is_public[off_occ:] = 1        # nghề + kỹ năng: tri thức O*NET công khai

    return {
        "n_u": n_u, "n_j": n_j, "n_occ": n_occ, "n_skill": n_skill, "n_nodes": n_nodes,
        "offsets": np.array([off_user, off_job, off_occ, off_skill], dtype=np.int64),
        "edge_index": edge_index, "edge_type": edge_type,
        "train_mask": train_mask, "test_mask": test_mask, "is_public": is_public,
        "occ_ids": np.array(occ_ids), "skill_names": np.array(skill_set),
        "n_e0": n_e0, "n_e1": n_e1, "n_e2": n_e2, "n_e3": n_e3,
        "is_test": is_test, "u_sorted": u_sorted, "j_sorted": j_sorted,
    }


# ---------------------------------------------------------------------
# 8. main
# ---------------------------------------------------------------------
def count_rows(path: Path) -> int:
    n = 0
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f, delimiter="\t")
        next(rd, None)
        for _ in rd:
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(
        description="prepare_v3 — CareerBuilder + O*NET -> graph.npz / clients.json / meta.json"
    )
    ap.add_argument("--data-dir", default=str(DATA_DIR))
    ap.add_argument("--onet-zip", default=str(ONET_ZIP))
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-apps", type=int, default=10,
                    help="số application tối thiểu để một employer thành client")
    ap.add_argument("--min-jobs-per-employer", type=int, default=2,
                    help="tên employer phải xuất hiện ở >= N job khác nhau")
    ap.add_argument("--limit-jobs", type=int, default=0, help="chỉ quét N job đầu (0 = tất cả)")
    args = ap.parse_args()

    t_start = time.perf_counter()
    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    banner("PREPARE_V3 — CareerBuilder + O*NET -> đồ thị dị thể, client = nhà tuyển dụng")
    step(f"seed={args.seed} | client >= {args.min_apps} app | "
         f"employer >= {args.min_jobs_per_employer} job | out={out_dir}")
    MEM.tick("khởi động")

    onet = load_onet(Path(args.onet_zip))
    jobs = scan_jobs(data_dir / "jobs.tsv", onet, limit=args.limit_jobs)

    # --- BƯỚC 1e: bỏ tên chỉ xuất hiện ở 1 job (rác / công ty không thật)
    banner(f"BƯỚC 1e — LỌC EMPLOYER PHẢI XUẤT HIỆN Ở >= {args.min_jobs_per_employer} JOB")
    emp_id_np = np.frombuffer(jobs["emp_id"], dtype=np.int32).copy()
    n_before = len(jobs["emp_names"])
    job_per_emp = np.bincount(emp_id_np[emp_id_np >= 0], minlength=n_before)
    keep_name = job_per_emp >= args.min_jobs_per_employer
    n_single = int((~keep_name).sum())
    emp_id_np[~keep_name[emp_id_np]] = -1
    jobs["emp_id"] = array.array("i", emp_id_np.tobytes())
    n_job_after = int((emp_id_np >= 0).sum())
    step(f"Tên employer trước lọc: {n_before:,}")
    step(f"Loại vì chỉ có <{args.min_jobs_per_employer} job: {n_single:,} "
         f"({100.0 * n_single / max(n_before, 1):.1f}%)")
    step(f"Còn lại: {int(keep_name.sum()):,} employer | job có employer: {n_job_after:,} "
         f"({100.0 * n_job_after / max(jobs['n_jobs'], 1):.2f}%)")
    MEM.tick("sau lọc employer >= 2 job")

    apps = scan_apps(data_dir / "apps.tsv", jobs, args.min_apps, onet)
    cl = build_clients(apps, jobs, args.min_apps)

    occ_ids, occ_index = collect_occupations(jobs, cl["kept_j"], onet)
    n_occ_all = len(occ_ids)
    n_occ_with_skill = sum(1 for s in occ_ids if onet["occ_skills"].get(s))
    step(f"Nghề của job trong đồ thị: {n_occ_all:,} | trong đó có kỹ năng công nghệ: "
         f"{n_occ_with_skill:,} (không kỹ năng: {n_occ_all - n_occ_with_skill:,}, "
         f"vẫn giữ làm nút nhưng không có cạnh nghề-kỹ năng)")
    cl["occ_index"] = occ_index

    hist = scan_history(data_dir / "user_history.tsv", onet, apps, cl)
    g = build_graph(onet, jobs, cl, hist, occ_ids, occ_index, args.seed)

    # ---------- ghi artifacts ----------
    banner("BƯỚC 5b — GHI ARTIFACTS")
    # user_ids / job_ids: ID GỐC (chuỗi) theo đúng thứ tự chỉ số nút
    user_ids_out = np.array([apps["user_ids"][int(i)] for i in cl["kept_u"]])
    job_ids_out = np.array([jobs["job_ids"][int(i)] for i in cl["kept_j"]])

    # --- TỰ KIỂM TRA tính nhất quán trước khi ghi (chặn lỗi trộn cấp / lệch độ dài)
    ei, et = g["edge_index"], g["edge_type"]
    n_e = int(ei.shape[1])
    off = g["offsets"]
    n_u, n_j, n_o, n_s = g["n_u"], g["n_j"], g["n_occ"], g["n_skill"]
    assert ei.shape[0] == 2, f"edge_index phải có 2 hàng, đang là {ei.shape}"
    assert n_e == len(et) == len(g["train_mask"]) == len(g["test_mask"]), (
        f"LỆCH ĐỘ DÀI: edge_index {n_e}, edge_type {len(et)}, "
        f"train {len(g['train_mask'])}, test {len(g['test_mask'])}"
    )
    assert int(ei.min()) >= 0 and int(ei.max()) < g["n_nodes"], "chỉ số nút ngoài phạm vi"
    assert off.tolist() == [0, n_u, n_u + n_j, n_u + n_j + n_o], f"offsets sai: {off.tolist()}"
    for typ, lo, hi, lo2, hi2 in (
        (0, off[0], off[0] + n_u, off[1], off[1] + n_j),        # user - job
        (1, off[1], off[1] + n_j, off[2], off[2] + n_o),        # job  - occ
        (2, off[2], off[2] + n_o, off[3], off[3] + n_s),        # occ  - skill
        (3, off[0], off[0] + n_u, off[2], off[2] + n_o),        # user - occ
    ):
        sel = np.flatnonzero(et == typ)
        if sel.size:
            a, b = ei[0, sel], ei[1, sel]
            ok = (((a >= lo) & (a < hi) & (b >= lo2) & (b < hi2)) |
                  ((b >= lo) & (b < hi) & (a >= lo2) & (a < hi2)))
            assert bool(ok.all()), f"cạnh type={typ} có đầu mút sai khối nút"
    assert all(len(str(x)) == 7 for x in g["occ_ids"]), "mã nghề phải dài 6 ký tự (soc[:7])"

    # Tỉ lệ job nối được lên nghề: báo minh bạch, KHÔNG assert cứng (job không
    # map được mã nghề vẫn là nút hợp lệ, chỉ thiếu cạnh job-occupation).
    sel1 = np.flatnonzero(et == 1)
    job_side = ei[0, sel1]
    job_side = job_side[(job_side >= off[1]) & (job_side < off[1] + n_j)]
    n_job_with_occ = int(np.unique(job_side).size)
    pct_job_with_occ = round(100.0 * n_job_with_occ / max(n_j, 1), 2)
    step(f"Job có cạnh nghề: {n_job_with_occ:,}/{n_j:,} ({pct_job_with_occ}%) "
         f"— {n_j - n_job_with_occ:,} job không map được mã nghề (vẫn giữ làm nút)")
    assert n_job_with_occ > 0, "không job nào nối được lên nghề"
    step(f"Tự kiểm tra: {n_e:,} cạnh, 4 loại cạnh, offsets và mã nghề nhất quán")

    npz_path = out_dir / "graph.npz"
    tmp_npz = out_dir / "_graph.npz.tmp"
    with open(tmp_npz, "wb") as fh:          # ghi tạm rồi thay -> chạy lại an toàn
        np.savez_compressed(
            fh,
            n_nodes=np.int64(g["n_nodes"]),
            n_users=np.int64(g["n_u"]),
            n_jobs=np.int64(g["n_j"]),
            n_skills=np.int64(g["n_skill"]),
            n_occupations=np.int64(g["n_occ"]),
            offsets=g["offsets"],
            edge_index=g["edge_index"],
            edge_type=g["edge_type"],
            train_mask=g["train_mask"],
            test_mask=g["test_mask"],
            is_public=g["is_public"],
            user_ids=user_ids_out,
            job_ids=job_ids_out,
            client_of_job=cl["client_of_job"],
            client_of_user=cl["client_of_user"],
            occ_ids=g["occ_ids"],
            skill_names=g["skill_names"],
            edge_type_names=np.array(["user-job", "job-occ", "occ-skill", "user-occ"]),
            node_order=np.array(["user", "job", "occupation", "skill"]),
            is_symmetric=np.bool_(True),
            edge_convention=np.array(
                "one_row_per_undirected_edge: edge_type.shape[0] == "
                "edge_index.shape[1] == train_mask.shape[0] == test_mask.shape[0]"
            ),
        )
    tmp_npz.replace(npz_path)
    size_npz = npz_path.stat().st_size
    step(f"graph.npz: {human_bytes(size_npz)}")

    clients_path = out_dir / "clients.json"
    with open(clients_path, "w", encoding="utf-8") as f:
        json.dump(cl["clients"], f, ensure_ascii=False, indent=1)
    size_clients = clients_path.stat().st_size
    step(f"clients.json: {human_bytes(size_clients)} ({cl['n_clients']:,} client)")

    # --- job_titles.json: metadata hiển thị cho MỌI nút job trong đồ thị.
    # Không lọc theo nghề: API/UI cần title cho cả job không map được nghề.
    job_title_map: dict[str, dict[str, str]] = {}
    meta_by_job = jobs["meta_by_job"]
    soc_id_np = np.frombuffer(jobs["soc_id"], dtype=np.int32)
    n_job_no_meta = 0
    for jj, jo in enumerate(cl["kept_j"].tolist()):
        info = meta_by_job.get(jo)
        eid = int(emp_id_np[jo])
        if not info:
            n_job_no_meta += 1
            continue
        title, city, state = info
        sid = int(soc_id_np[jo])
        soc_code = jobs["soc7_list"][sid] if sid >= 0 else ""
        job_title_map[jobs["job_ids"][jo]] = {
            "title": title,
            "city": city,
            "state": state,
            "employer": jobs["emp_names"][eid] if eid >= 0 else "",
            "occupation": soc_code,
        }
    jt_path = out_dir / "job_titles.json"
    with open(jt_path, "w", encoding="utf-8") as f:
        json.dump(job_title_map, f, ensure_ascii=False)
    size_jt = jt_path.stat().st_size
    step(f"job_titles.json: {human_bytes(size_jt)} ({len(job_title_map):,}/"
         f"{g['n_j']:,} nút job; {n_job_no_meta:,} job thiếu metadata gốc)")

    # --- user_titles.json: title gần nhất từ user_history
    user_title_map: dict[str, dict[str, str]] = {}
    for node, uid in enumerate(cl["kept_u"].tolist()):
        t = hist["latest_title"][node]
        if not t:
            continue
        user_title_map[apps["user_ids"][uid]] = {
            "title": t,
            "occupation": hist["latest_soc"][node],
        }
    ut_path = out_dir / "user_titles.json"
    with open(ut_path, "w", encoding="utf-8") as f:
        json.dump(user_title_map, f, ensure_ascii=False)
    size_ut = ut_path.stat().st_size
    step(f"user_titles.json: {human_bytes(size_ut)} ({len(user_title_map):,} user)")

    # ---------- meta.json ----------
    n_app_rows = apps["n_rows"]
    sizes = (np.array([c["n_apps"] for c in cl["clients"]], dtype=np.int64)
             if cl["clients"] else np.array([0]))
    n_e_total = int(g["edge_index"].shape[1])
    # Độ thưa đo trên lớp tương tác user-job (ma trận n_users x n_jobs).
    density = g["n_e0"] / max(g["n_u"] * g["n_j"], 1) * 100.0
    n_users_rows = count_rows(data_dir / "users.tsv")
    step(f"users.tsv: {n_users_rows:,} dòng")

    meta = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_seconds": round(time.perf_counter() - t_start, 1),
        "seed": args.seed,
        "job_titles_file": "job_titles.json",
        "user_titles_file": "user_titles.json",
        "has_job_metadata": True,
        "artifacts": {
            "graph.npz": human_bytes(size_npz),
            "clients.json": human_bytes(size_clients),
            "job_titles.json": human_bytes(size_jt),
            "user_titles.json": human_bytes(size_ut),
        },
        "config": {
            "min_apps_per_client": args.min_apps,
            "min_jobs_per_employer": args.min_jobs_per_employer,
            "test_ratio": TEST_RATIO,
            "min_apps_for_test": MIN_APPS_FOR_TEST,
            "limit_jobs": args.limit_jobs or None,
            "occupation_code": (
                "O*NET-SOC cắt còn 6 ký tự soc[:7] — dùng NHẤT QUÁN ở nút nghề, cạnh job-nghề, "
                "cạnh nghề-kỹ năng, cạnh user-nghề (bản cũ trộn cấp làm phồng 67,4% số cạnh)"
            ),
            "skill_source": (
                "O*NET Technology Skills.txt (KHÔNG dùng Skills.txt: 879/879 nghề đủ 35 "
                "element -> entropy 0)"
            ),
        },
        "paths": {
            "data_dir": str(data_dir),
            "onet_zip": str(args.onet_zip),
            "artifacts": str(out_dir),
        },
        "raw": {
            "jobs_rows": jobs["n_rows"],
            "jobs_unique_ids": jobs["n_jobs"],
            "apps_rows": n_app_rows,
            "users_rows": n_users_rows,
            "user_history_rows": hist["n_rows"],
            "jobs_bad_format_rows": jobs["bad_rows"],
            "apps_bad_format_rows": apps["n_bad"],
        },
        "employer_extraction": {
            "n_jobs_with_employer_raw": jobs["n_jobs_with_emp"],
            "pct_jobs_with_employer_raw": round(
                100.0 * jobs["n_jobs_with_emp"] / max(jobs["n_jobs"], 1), 2),
            "n_distinct_names_raw": n_before,
            "dropped_fewer_than_min_jobs": n_single,
            "min_jobs_per_employer": args.min_jobs_per_employer,
            "n_distinct_employers_after_job_filter": int(keep_name.sum()),
            "n_jobs_with_employer_after_job_filter": n_job_after,
            "pct_jobs_with_employer_after_job_filter": round(
                100.0 * n_job_after / max(jobs["n_jobs"], 1), 2),
            "n_apps_with_employer": apps["n_with_emp"],
            "pct_apps_with_employer": round(
                100.0 * apps["n_with_emp"] / max(n_app_rows, 1), 2),
            "n_apps_with_employer_and_client": apps["n_apps_kept"],
            "pct_apps_with_employer_and_client": round(
                100.0 * apps["n_apps_kept"] / max(n_app_rows, 1), 2),
            "source_counts": dict(jobs["src_counter"]),
            "duplicate_user_job_apps_merged": apps["n_dup"],
            "filter_steps": [
                {"step": "0. apps.tsv gốc (mọi dòng)",
                 "n_employers": None, "n_jobs_with_employer": None,
                 "n_apps": n_app_rows, "pct_apps_remaining": 100.0},
                {"step": "1. job có trong jobs.tsv",
                 "n_employers": None, "n_jobs_with_employer": None,
                 "n_apps": apps["n_with_job"],
                 "pct_apps_remaining": round(100.0 * apps["n_with_job"] / max(n_app_rows, 1), 2)},
                {"step": "2. + trích được employer (regex/domain/blacklist)",
                 "n_employers": n_before, "n_jobs_with_employer": jobs["n_jobs_with_emp"],
                 "n_apps": apps["n_with_emp"],
                 "pct_apps_remaining": round(100.0 * apps["n_with_emp"] / max(n_app_rows, 1), 2)},
                {"step": f"3. + bỏ tên chỉ xuất hiện ở <{args.min_jobs_per_employer} job",
                 "n_employers": int(keep_name.sum()), "n_jobs_with_employer": n_job_after,
                 "n_apps": None, "pct_apps_remaining": None},
                {"step": "4. + job map được nghề CÓ kỹ năng (P1)",
                 "n_employers": None, "n_jobs_with_employer": None,
                 "n_apps": apps["n_p1_pairs"],
                 "pct_apps_remaining": round(
                     100.0 * apps["n_p1_pairs"] / max(n_app_rows, 1), 2)},
                {"step": f"5. + employer >= {args.min_apps} application (client cuối)",
                 "n_employers": cl["n_clients"], "n_jobs_with_employer": None,
                 "n_apps": apps["n_apps_kept"],
                 "pct_apps_remaining": round(
                     100.0 * apps["n_apps_kept"] / max(n_app_rows, 1), 2)},
            ],
            "coverage_explanation": (
                "Vì sao % app phủ thấp hơn con số probe 43,50%: probe chỉ trích employer "
                "trên job có employer rồi join thẳng sang apps; ở đây còn 3 bộ lọc siết chất "
                "lượng làm giảm thêm: (a) bỏ tên employer chỉ xuất hiện ở <2 job, "
                "(b) yêu cầu job map được nghề CÓ kỹ năng công nghệ (P1), "
                f"(c) chỉ giữ employer có >= {args.min_apps} application. "
                "Xem pct_apps_remaining của từng bước để thấy mức giảm. Đây là đánh đổi có "
                "chủ ý để đổi lấy độ chính xác của nhãn employer, không phải trích kém đi."
            ),
            "top20_employers_by_apps": [
                [c["employer_name"], c["n_apps"]] for c in cl["clients"][:20]
            ],
        },
        "clients": {
            "threshold_min_apps": args.min_apps,
            "n_clients": cl["n_clients"],
            "n_apps_covered": int(sizes.sum()),
            "pct_apps_covered_of_all_apps": round(
                100.0 * sizes.sum() / max(n_app_rows, 1), 2),
            "n_users_covered": g["n_u"],
            "n_jobs_covered": g["n_j"],
            "size_stats": {
                "min": int(sizes.min()),
                "p25": int(np.quantile(sizes, 0.25)),
                "median": int(np.median(sizes)),
                "p75": int(np.quantile(sizes, 0.75)),
                "max": int(sizes.max()),
                "mean": round(float(sizes.mean()), 1),
                "max_min_ratio": round(float(sizes.max()) / max(float(sizes.min()), 1), 2),
                "top1_share_pct": round(
                    100.0 * float(sizes.max()) / max(float(sizes.sum()), 1), 2),
            },
            "n_users_multi_client": cl["multi_users"],
            "pct_users_multi_client": round(
                100.0 * cl["multi_users"] / max(g["n_u"], 1), 2),
            "mean_clients_per_user": round(float(cl["n_clients_per_user"].mean()), 2),
            "cross_silo_note": (
                "CROSS-SILO HỢP LỆ — KHÔNG phải rò rỉ dữ liệu. Mỗi client (employer) chỉ sở hữu "
                "quan sát 'user X ứng tuyển vào job CỦA TÔI'. Một user có thể ứng tuyển ở nhiều "
                "employer nên xuất hiện ở nhiều silo — đó là bản chất thị trường tuyển dụng, không "
                "phải chia sẻ dữ liệu giữa các client. Client không thấy application của user vào "
                "job của employer khác."
            ),
        },
        "occupations": {
            "n_occupations": g["n_occ"],
            "code_level": "soc[:7] (6 ký tự gốc), nhất quán ở mọi nơi",
            "n_occupations_onet_total": len(onet["soc_title"]),
            "n_occupations_of_jobs_in_graph": n_occ_all,
            "n_occupations_with_skill": n_occ_with_skill,
            "n_occupations_without_skill": n_occ_all - n_occ_with_skill,
            "n_jobs_mapped_to_occupation": jobs["n_jobs_with_soc"],
            "pct_jobs_mapped_to_occupation": round(
                100.0 * jobs["n_jobs_with_soc"] / max(jobs["n_jobs"], 1), 2),
            "mean_jobs_per_occupation": round(g["n_j"] / max(g["n_occ"], 1), 1),
        },
        "skills": {
            "n_skill_nodes": g["n_skill"],
            "source": "O*NET Technology Skills.txt",
            "n_skills_onet_total": onet["n_skill_onet"],
            "mean_skills_per_occupation": round(g["n_e2"] / max(g["n_occ"], 1), 2),
            "user_history_titles_mapped": hist["n_mapped_title"],
            "pct_user_history_titles_mapped": round(
                100.0 * hist["n_mapped_title"] / max(hist["n_rows"], 1), 2),
            "user_history_rows_used": hist["n_mapped_occ"],
            "user_occupation_edges": g["n_e3"],
            "note": (
                "Kỹ năng phía user là SUY QUA NGHỀ: user_history.JobTitle -> mã nghề -> tập kỹ năng "
                "của nghề. KHÔNG phải kỹ năng tự khai. Đồ thị không lưu cạnh user-skill trực tiếp; "
                "user chạm skill qua 2 bước nhảy user-occupation-skill (tránh phình số cạnh)."
            ),
        },
        "nodes": {
            "n_nodes": g["n_nodes"],
            "n_users": g["n_u"],
            "n_jobs": g["n_j"],
            "n_occupations": g["n_occ"],
            "n_skills": g["n_skill"],
            "offsets": g["offsets"].tolist(),
            "order": ["user", "job", "occupation", "skill"],
            "n_public_nodes": int(g["is_public"].sum()),
        },
        "edges": {
            "n_edges_stored": n_e_total,
            "convention": (
                "MỘT dòng cho MỖI cạnh vô hướng (chuẩn PyTorch Geometric). "
                "edge_type.shape[0] == edge_index.shape[1] == train_mask.shape[0] "
                "== test_mask.shape[0]."
            ),
            "is_symmetric": True,
            "symmetrize_hint": (
                "Đồ thị đối xứng: khi nạp, dùng edge_index và edge_index.flip(0) "
                "(hoặc torch_geometric.utils.to_undirected) nếu mô hình cần cả hai chiều."
            ),
            "by_type": {
                "0_user_job": g["n_e0"],
                "1_job_occupation": g["n_e1"],
                "2_occupation_skill": g["n_e2"],
                "3_user_occupation": g["n_e3"],
            },
            "n_jobs_with_occupation_edge": n_job_with_occ,
            "pct_jobs_with_occupation_edge": pct_job_with_occ,
            "n_jobs_without_occupation_edge": n_j - n_job_with_occ,
            "occupation_coverage_note": (
                "Job không map được mã nghề O*NET vẫn là NÚT hợp lệ và vẫn giữ nguyên "
                "cạnh user-job; chúng chỉ thiếu cạnh job-occupation nên skill không lan "
                "tới được. Tỉ lệ này được báo ở đây thay vì âm thầm cắt bớt tương tác."
            ),
            "split": {
                "unit": "cạnh user-job",
                "train": int((~g["is_test"]).sum()),
                "test": int(g["is_test"].sum()),
                "test_ratio": TEST_RATIO,
                "min_apps_for_test": MIN_APPS_FOR_TEST,
                "note": ("train_mask/test_mask là mặt nạ theo CẠNH, độ dài = số cạnh "
                         "(= edge_index.shape[1]). Mọi cạnh không phải user-job nằm "
                         "trong train_mask."),
            },
        },
        "job_metadata": {
            "n_jobs": len(job_title_map),
            "fields": ["title", "city", "state", "employer"],
            "definition_of_P1": (
                "job có client (employer >= ngưỡng). Mọi job client sở hữu đều là nút. "
                "Job map được mã nghề O*NET thì có thêm cạnh job-occupation."
            ),
            "note": (
                "Không đòi job phải map được nghề, vì đòi như vậy sẽ bỏ ~2/3 tương tác "
                "và % app phủ tụt từ 27% xuống 9%. Job không nghề vẫn giữ cạnh user-job; "
                "tỉ lệ nối được nghề xem edges.n_jobs_with_occupation_edge."
            ),
            "size": human_bytes(size_jt),
        },
        "user_metadata": {
            "n_users": len(user_title_map),
            "fields": ["title", "occupation"],
            "source": "user_history.JobTitle có Sequence lớn nhất",
            "size": human_bytes(size_ut),
        },
        "sparsity_pct": round(density, 6),
        "memory_peak_mb": round(MEM.peak, 1),
        "memory_peak_gb": round(MEM.peak / 1024, 2),
        "notes": [
            "jobs.tsv đọc streaming bằng csv.reader, KHÔNG dùng pandas (RAM chỉ 3,9 GB).",
            "Mã nghề dùng dạng gốc soc[:7] đồng nhất ở mọi nơi -> không phồng số cạnh.",
            "Mỗi cạnh vô hướng lưu ĐÚNG 1 dòng trong edge_index (chuẩn PyG); đồ thị đối "
            "xứng nên bên nạp tự đối xứng hoá bằng edge_index.flip(0) khi cần.",
            "client_of_user = client có nhiều application nhất (hoà -> client_id nhỏ hơn); "
            "user vẫn có thể thuộc nhiều client, xem pct_users_multi_client.",
            "user_ids/job_ids trong graph.npz là ID GỐC dạng chuỗi, theo đúng thứ tự chỉ số nút.",
            "job_titles.json / user_titles.json là file PHỤ cho UI và notebook; graph.npz không đổi.",
        ],
    }
    meta_path = out_dir / "meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    size_meta = meta_path.stat().st_size
    step(f"meta.json: {human_bytes(size_meta)}")

    # ---------- báo cáo cuối ----------
    banner("KẾT QUẢ")
    step(f"Thời gian chạy: {meta['runtime_seconds']:,.1f}s")
    step(f"graph.npz {human_bytes(size_npz)} | clients.json {human_bytes(size_clients)} | "
         f"job_titles.json {human_bytes(size_jt)} | user_titles.json {human_bytes(size_ut)} | "
         f"meta.json {human_bytes(size_meta)}")
    step(f"Nút: {g['n_nodes']:,} = {g['n_u']:,} user + {g['n_j']:,} job + "
         f"{g['n_occ']:,} nghề + {g['n_skill']:,} kỹ năng")
    step(f"Cạnh (1 dòng/cạnh vô hướng): {n_e_total:,} = user-job {g['n_e0']:,} | "
         f"job-occ {g['n_e1']:,} | occ-skill {g['n_e2']:,} | user-occ {g['n_e3']:,}")
    step(f"Client: {cl['n_clients']:,} | app phủ {meta['clients']['pct_apps_covered_of_all_apps']}%"
         f" | thưa {density:.6f}%")
    step(f"RAM đỉnh: {MEM.peak:,.0f} MB ({MEM.peak / 1024:.2f} GB)"
         + ("  ⚠ VƯỢT 3 GB" if MEM.peak > 3072 else ""))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
