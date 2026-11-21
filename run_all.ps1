# Chạy toàn bộ pipeline: từ dữ liệu thô tới báo cáo .docx
#
#   powershell -ExecutionPolicy Bypass -File run_all.ps1
#   powershell -ExecutionPolicy Bypass -File run_all.ps1 -SkipTests    # bỏ qua test
#
# Chạy hoàn toàn offline (dữ liệu MEDAJob đã có sẵn trong Lab03).
#
# Vì sao ép TMP/TEMP và MPLCONFIGDIR vào trong dự án:
# trên máy này %TEMP% và các thư mục cache mặc định (~/.matplotlib,
# ~/.streamlit) không ghi được, khiến matplotlib và Streamlit lỗi khởi động.

param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$script:failures = @()
$script:t0 = Get-Date

# ---------------------------------------------------------------------
# Môi trường
# ---------------------------------------------------------------------
$Root = $PSScriptRoot
Set-Location $Root

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$TmpDir = Join-Path $Root "artifacts\.tmp"
$MplDir = Join-Path $Root "artifacts\.mplcache"
New-Item -ItemType Directory -Force -Path $TmpDir, $MplDir | Out-Null
$env:TMP = $TmpDir
$env:TEMP = $TmpDir
$env:MPLCONFIGDIR = $MplDir

function Write-Step($msg) {
    Write-Host ""
    Write-Host ("=" * 74) -ForegroundColor DarkGray
    Write-Host $msg -ForegroundColor Cyan
    Write-Host ("=" * 74) -ForegroundColor DarkGray
}

function Invoke-Stage {
    param([string]$Name, [string]$Script)
    Write-Step $Name
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & python "$Script"
    $code = $LASTEXITCODE
    $sw.Stop()
    if ($code -ne 0) {
        Write-Host "  THẤT BẠI (exit $code) sau $([int]$sw.Elapsed.TotalSeconds)s" -ForegroundColor Red
        $script:failures += "$Name (exit $code)"
        return $false
    }
    Write-Host "  OK — $([int]$sw.Elapsed.TotalSeconds)s" -ForegroundColor Green
    return $true
}

Write-Host ""
Write-Host "  GNN + HỌC LIÊN BANG — CHẠY TOÀN BỘ PIPELINE" -ForegroundColor White
Write-Host "  Gợi ý việc làm trên kiến trúc dữ liệu phân tán" -ForegroundColor Gray
Write-Host "  Python: $(python --version 2>&1)" -ForegroundColor Gray

# ---------------------------------------------------------------------
# 1. Kiểm tra môi trường
# ---------------------------------------------------------------------
Write-Step "0/6  KIỂM TRA MÔI TRƯỜNG"

$required = @("numpy", "pandas", "torch", "sklearn", "matplotlib", "streamlit",
              "altair", "networkx", "scipy", "pyarrow")
$missing = @()
foreach ($m in $required) {
    $ok = & python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('$m') else 1)" 2>$null
    if ($LASTEXITCODE -ne 0) { $missing += $m }
}
if ($missing.Count -gt 0) {
    Write-Host "  Thiếu gói: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "  Cài bằng: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}
Write-Host "  Đủ gói cần thiết: $($required -join ', ')" -ForegroundColor Green

# ---------------------------------------------------------------------
# 2. Dữ liệu MEDAJob
# ---------------------------------------------------------------------
$rawDir = & python -c "import yaml;print(yaml.safe_load(open('config.yaml',encoding='utf-8'))['paths']['medajob_raw'])"
if (-not (Test-Path $rawDir)) {
    Write-Host "  Không tìm thấy dữ liệu MEDAJob tại: $rawDir" -ForegroundColor Red
    Write-Host "  Sửa đường dẫn 'medajob_raw' trong config.yaml" -ForegroundColor Yellow
    exit 1
}
$needFiles = @("job.csv", "ratings.csv", "user_profiles.csv", "job_views.csv")
$absent = $needFiles | Where-Object { -not (Test-Path (Join-Path $rawDir $_)) }
if ($absent) {
    Write-Host "  Thiếu file: $($absent -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "  Dữ liệu MEDAJob: $rawDir" -ForegroundColor Green

# ---------------------------------------------------------------------
# 3. Các bước
# ---------------------------------------------------------------------
$ok = Invoke-Stage "1/6  LÀM SẠCH MEDAJob VÀ DỰNG ĐỒ THỊ" "src/medajob/prepare.py"

if ($ok) {
    $ok = Invoke-Stage "2/6  THỰC NGHIỆM GỢI Ý (Centralized / Local / FedAvg / FedProx)" `
                       "src/medajob/run_experiments.py"
}

# ---------------------------------------------------------------------
# 4. Hình và báo cáo
# ---------------------------------------------------------------------
if ($ok -and (Test-Path "results/reco_main.json")) {
    Invoke-Stage "3/6  SINH 9 HÌNH CHO BÁO CÁO" "src/report/figures.py" | Out-Null
    Invoke-Stage "4/6  SINH BẢNG SỐ LIỆU CHUẨN (docs/SO_LIEU_CHINH.md)" `
                 "src/report/make_facts.py" | Out-Null
    Invoke-Stage "5/6  DỰNG BÁO CÁO .DOCX" "src/report/build_docx.py" | Out-Null
} else {
    Write-Host ""
    Write-Host "  Bỏ qua hình/báo cáo vì thiếu results/reco_main.json" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------
# 5. Test
# ---------------------------------------------------------------------
if (-not $SkipTests) {
    Write-Step "6/6  KIỂM THỬ TỰ ĐỘNG"
    & python -m pytest tests/ -q --no-header
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Một số test thất bại" -ForegroundColor Red
        $script:failures += "pytest"
    } else {
        Write-Host "  Tất cả test đạt" -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------
# 6. Tổng kết
# ---------------------------------------------------------------------
$elapsed = [int]((Get-Date) - $script:t0).TotalSeconds

Write-Host ""
Write-Host ("=" * 74) -ForegroundColor DarkGray
if ($script:failures.Count -eq 0) {
    Write-Host "  HOÀN TẤT trong ${elapsed}s" -ForegroundColor Green
} else {
    Write-Host "  HOÀN TẤT CÓ LỖI trong ${elapsed}s" -ForegroundColor Yellow
    foreach ($f in $script:failures) { Write-Host "    - $f" -ForegroundColor Red }
}
Write-Host ("=" * 74) -ForegroundColor DarkGray

Write-Host ""
Write-Host "  Sản phẩm:" -ForegroundColor White
$outputs = @(
    @{p = "results/reco_main.json";       d = "kết quả gợi ý"},
    @{p = "results/figures";              d = "9 hình"},
    @{p = "docs/SO_LIEU_CHINH.md";        d = "bảng số liệu chuẩn"},
    @{p = "docs/BAO_CAO_GNN_FL.docx";     d = "báo cáo"}
)
foreach ($o in $outputs) {
    if (Test-Path $o.p) {
        $size = if ((Get-Item $o.p).PSIsContainer) { "" }
                else { " ({0:N0} KB)" -f ((Get-Item $o.p).Length / 1KB) }
        Write-Host ("    [x] {0,-34} {1}{2}" -f $o.p, $o.d, $size) -ForegroundColor Green
    } else {
        Write-Host ("    [ ] {0,-34} {1}" -f $o.p, $o.d) -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "  Chạy demo trực quan:" -ForegroundColor White
Write-Host '    python -m streamlit run app/streamlit_app.py --server.headless=true' -ForegroundColor Gray
Write-Host ""
Write-Host "  Mở báo cáo:" -ForegroundColor White
Write-Host "    docs\BAO_CAO_GNN_FL.docx   (trong Word: Ctrl+A rồi F9 để cập nhật mục lục)" -ForegroundColor Gray
Write-Host ""

if ($script:failures.Count -gt 0) { exit 1 }
exit 0
