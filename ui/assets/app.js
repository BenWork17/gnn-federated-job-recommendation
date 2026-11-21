/* =====================================================================
   FL NODE CONSOLE — giám sát node học liên bang (GNN + FL)
   HTML/CSS/JS thuần, không build step. Mở trực tiếp bằng file:// hoặc
   serve tĩnh đều chạy. Không framework, không npm.

   HỢP ĐỒNG API (backend phải trả đúng tên field):
     GET  /health
     GET  /api/clients?limit=&offset=
     GET  /api/clients/{client_id}
     GET  /api/graph/summary
     POST /api/train/start
     GET  /api/train/status/{run_id}
     GET  /api/train/runs
     WS   /ws/latency
     WS   /ws/train/{run_id}
   ===================================================================== */

/* >>> CẤU HÌNH DUY NHẤT — sửa đúng một chỗ này <<< */
/* Có thể ghi đè khi cần bằng query string: index.html?api=http://127.0.0.1:8011 */
const API_BASE =
  new URLSearchParams(location.search).get('api') || 'http://127.0.0.1:8000';
/* <<< hết phần cấu hình >>> */

const WS_RETRY_MS = 3000;          // tự thử lại WS mỗi 3s
const LAT_OK_MS = 50;              // xanh  : < 50 ms
const LAT_WARN_MS = 200;           // vàng  : < 200 ms, đỏ: >= 200 ms
const MAX_NODE_CELLS = 220;
const MAX_LOG_LINES = 400;
const DEMO_CLIENT_COUNT = 9116;    // khớp số client thật (employer >= 10 application)
const CLIENT_PAGE_FETCH = 1000;    // cỡ trang khi tải toàn bộ client
const MAX_FETCH_PAGES = 40;        // trần an toàn, tránh vòng lặp vô hạn
const SORT_SERVER_KEYS = new Set(['n_apps', 'n_users', 'n_jobs', 'name', 'client_id']);

/* ------------------------------------------------------------------ */
/* Tiện ích                                                            */
/* ------------------------------------------------------------------ */

const $ = (id) => document.getElementById(id);

const numFmt = new Intl.NumberFormat('vi-VN');
const fmtInt = (v) => (v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : numFmt.format(Math.round(Number(v))));
const fmtNum = (v, digits = 3) =>
  v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(digits);
const fmtMs = (v) => (v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : `${Math.round(Number(v))} ms`);
const fmtBytes = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  if (n < 1024) return `${Math.round(n)} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
};
const pad2 = (n) => String(n).padStart(2, '0');
const clockStr = (d = new Date()) => `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
const esc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function latState(ms) {
  if (ms === null || ms === undefined || Number.isNaN(Number(ms))) return 'pending';
  const v = Number(ms);
  if (v < LAT_OK_MS) return 'ok';
  if (v < LAT_WARN_MS) return 'warn';
  return 'bad';
}

function percentile(sortedArr, p) {
  if (!sortedArr.length) return null;
  const idx = (sortedArr.length - 1) * p;
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sortedArr[lo];
  return sortedArr[lo] + (sortedArr[hi] - sortedArr[lo]) * (idx - lo);
}

function debounce(fn, wait) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

/* ------------------------------------------------------------------ */
/* Trạng thái ứng dụng                                                 */
/* ------------------------------------------------------------------ */

const state = {
  mode: 'live',            // 'live' | 'demo'
  autoDemoReason: '',
  health: null,
  summary: null,
  clients: [],             // toàn bộ client (nếu tải được), đã sắp xếp
  clientsTotal: 0,
  serverPaged: false,      // backend chặn tải toàn bộ -> phân trang phía server
  sort: { key: 'n_apps', dir: 'desc' },
  page: 0,
  pageSize: 50,
  selectedClientId: null,
  run: null,               // {run_id, total_rounds, participants:[client_id], algo}
  runStatus: 'idle',
  runRound: 0,
  nodes: new Map(),        // client_id -> {latency, state, bytesUp, bytesDown}
  roundLatencies: [],      // (giữ cho tương thích) latency của vòng hiện tại
  latenciesByRound: new Map(), // round -> Map(client_id -> latency)
  completedRounds: new Set(),  // các vòng đã nhận message type='round'
  finishing: false,            // đã chốt xong lượt chạy (chống log/refresh lặp)
  metrics: [],             // [{round, recall20, ndcg20, mrr20, loss}]
  latencySeries: [],       // [{round, p50, p95}]
  bytesTotal: 0,
  wsLatency: null,
  wsTrain: null,
  wsRetryTimer: null,
  demo: null,              // bộ mô phỏng cục bộ khi DEMO MODE
  logCount: 0,
};

let chartRecall = null;
let chartLatency = null;

/* ------------------------------------------------------------------ */
/* Gọi API                                                             */
/* ------------------------------------------------------------------ */

function apiUrl(path) {
  return API_BASE.replace(/\/+$/, '') + path;
}

async function apiFetch(path, { method = 'GET', body = null, timeout = 8000 } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const res = await fetch(apiUrl(path), {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`HTTP ${res.status} ${text.slice(0, 160)}`);
    }
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

function wsUrl(path) {
  const override = new URLSearchParams(location.search).get('ws');
  if (override) return override.replace(/\/+$/, '') + path;
  return API_BASE.replace(/^http/, 'ws').replace(/\/+$/, '') + path;
}

/* ------------------------------------------------------------------ */
/* Log dòng chảy                                                       */
/* ------------------------------------------------------------------ */

function logClear() {
  const box = $('log');
  box.innerHTML = '';
  state.logCount = 0;
}

function logLine(html, cls = '') {
  const box = $('log');
  if (!state.logCount) box.innerHTML = '';
  const div = document.createElement('div');
  div.className = `log-line ${cls}`.trim();
  div.innerHTML = html;
  box.appendChild(div);
  state.logCount += 1;
  while (box.children.length > MAX_LOG_LINES) box.removeChild(box.firstChild);
  if ($('autoscroll').checked) box.scrollTop = box.scrollHeight;
}

function logEvent(msg, cls = 'lg-event') {
  logLine(`<span class="lg-t">${clockStr()}</span><span class="lg-msg">${esc(msg)}</span>`, cls);
}

/* Mỗi message WS in đúng một dòng: "round X client Y latency Z ms" (+ byte trao đổi). */
function logTick({ round, clientId, latency, bytesUp, bytesDown, ts }) {
  const when = ts ? new Date(ts) : new Date();
  const t = Number.isNaN(when.getTime()) ? clockStr() : clockStr(when);
  const st = latState(latency);
  const dir = `${fmtBytes(bytesUp)}↑ ${fmtBytes(bytesDown)}↓`;
  logLine(
    `<span class="lg-t">${t}</span>` +
      `<span class="lg-r">round ${esc(round)}</span>` +
      `<span class="lg-c">client ${esc(clientId)}</span>` +
      `<span class="lg-lat">latency ${fmtMs(latency)} <span style="color:var(--ink-3)">· ${esc(dir)}</span></span>`,
    '',
  );
  const box = $('log');
  const last = box.lastElementChild;
  if (last) last.dataset.state = st;
}

/* ------------------------------------------------------------------ */
/* Badge helpers                                                       */
/* ------------------------------------------------------------------ */

function setBadge(el, tone, text) {
  el.dataset.tone = tone || '';
  el.innerHTML = `<span class="dot"></span>${esc(text)}`;
}

/* ------------------------------------------------------------------ */
/* Health                                                              */
/* ------------------------------------------------------------------ */

async function checkHealth({ silent = false } = {}) {
  try {
    const h = await apiFetch('/health', { timeout: 4000 });
    state.health = h;
    const ok = (h.status || '').toLowerCase() === 'ok' || h.status === true;
    setBadge($('healthBadge'), ok ? 'ok' : 'warn', ok ? 'online' : String(h.status ?? 'unknown'));
    $('dbState').textContent = h.db ? 'kết nối' : 'không';
    $('dbState').style.color = h.db ? 'var(--ok)' : 'var(--bad)';
    $('artState').textContent = h.artifacts ? 'có' : 'thiếu';
    $('artState').style.color = h.artifacts ? 'var(--ok)' : 'var(--warn)';
    if (state.mode === 'demo' && state.autoDemoReason) {
      // backend sống lại: tự quay về chế độ live, giữ nguyên lượt chạy đang có
      enterLiveMode({ keepRun: true });
    }
    return true;
  } catch (err) {
    state.health = null;
    setBadge($('healthBadge'), 'bad', 'offline');
    $('dbState').textContent = '—';
    $('artState').textContent = '—';
    // Chỉ tự rơi vào DEMO khi chưa có lượt chạy nào. Đang train mà backend
    // chập chờn thì giữ nguyên dữ liệu cuối, badge WS đã báo disconnected.
    const busy = state.runStatus === 'running';
    if (state.mode === 'live' && !busy) {
      if (!silent) logEvent(`Không gọi được /health (${err.message}) — chuyển DEMO MODE.`, 'lg-error');
      enterDemoMode(`Không kết nối được backend tại ${API_BASE} — đang hiển thị dữ liệu giả lập để xem giao diện.`);
    } else if (state.mode === 'live' && busy && !silent) {
      logEvent('Backend không phản hồi trong khi đang chạy — giữ dữ liệu cuối, chờ kết nối lại.', 'lg-error');
    }
    return false;
  }
}

/* ------------------------------------------------------------------ */
/* Chế độ DEMO / LIVE                                                  */
/* ------------------------------------------------------------------ */

function showDemoNotice(on, reason) {
  const n = $('demoNotice');
  n.classList.toggle('is-on', on);
  if (reason) $('demoReason').textContent = reason;
}

function enterDemoMode(reason) {
  if (state.mode === 'demo') return;
  state.mode = 'demo';
  state.autoDemoReason = reason || '';
  showDemoNotice(true, reason);
  closeSockets();
  buildDemoClients();
  buildDemoSummary();
  logEvent('DEMO MODE: dùng dữ liệu giả lập cục bộ, không gọi backend.', 'lg-error');
  renderAll();
  startDemoLoop();
  startRecoveryProbe();
}

/* Khi backend chết, thử lại /health mỗi 3s để tự quay về LIVE.
   (Đây là dò sức khoẻ, không phải polling dữ liệu train.) */
let recoveryTimer = null;

function startRecoveryProbe() {
  clearInterval(recoveryTimer);
  recoveryTimer = setInterval(() => {
    if (state.mode !== 'demo' || !state.autoDemoReason) {
      clearInterval(recoveryTimer);
      recoveryTimer = null;
      return;
    }
    checkHealth({ silent: true });
  }, WS_RETRY_MS);
}

function stopRecoveryProbe() {
  clearInterval(recoveryTimer);
  recoveryTimer = null;
}

function enterLiveMode({ keepRun = false } = {}) {
  const wasDemo = state.mode === 'demo';
  state.mode = 'live';
  state.autoDemoReason = '';
  showDemoNotice(false);
  stopDemoLoop();
  stopRecoveryProbe();
  const hadRun = !!state.run;
  if (!keepRun) resetRun({ keepLog: true });
  loadLiveData();
  if (keepRun || hadRun) {
    // tiếp tục lượt chạy đang có: nối lại cả hai kênh
    connectLatencySocket();
    if (state.run && String(state.run.run_id) !== 'pending') connectTrainSocket();
  } else {
    if (wasDemo) logEvent('Đã trở lại chế độ backend thật.', 'lg-dim');
    if (!state.run) connectLatencySocket();
  }
}

function buildDemoSummary() {
  renderSummary({
    n_users: 171807,
    n_jobs: 84845,
    n_skills: 7760,
    n_occupations: 583,
    n_edges_user_job: 436893,
    n_edges_job_skill: 2593468,
    n_edges_user_skill: 18017133,
    n_clients: 9116,
    sparsity_pct: 99.872967,
  });
}

/* PRNG 32-bit chính xác (mulberry32). Không dùng LCG nhân lớn vì
   seed * 1103515245 vượt 2^53 -> sai số, sinh dòng trùng nhau. */
function makeRng(seed0) {
  let a = seed0 >>> 0;
  return function rng() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function buildDemoClients() {
  const topV3 = [
    { client_id: 0, name: 'randstad', n_apps: 4745, n_users: 4215, n_jobs: 603, status: 'active' },
    { client_id: 1, name: 'allmedstaffing.com', n_apps: 1567, n_users: 1437, n_jobs: 219, status: 'active' },
    { client_id: 2, name: 'webhrdept.com', n_apps: 1531, n_users: 1364, n_jobs: 104, status: 'active' },
    { client_id: 3, name: 'spherion', n_apps: 1487, n_users: 1412, n_jobs: 161, status: 'active' },
    { client_id: 4, name: 'select-staffing.com', n_apps: 1477, n_users: 1074, n_jobs: 79, status: 'active' },
    { client_id: 5, name: 'lcca.com', n_apps: 1451, n_users: 1278, n_jobs: 342, status: 'active' },
    { client_id: 6, name: 'elitemed.com', n_apps: 1407, n_users: 1213, n_jobs: 283, status: 'active' },
    { client_id: 7, name: 'greenkeyllc.com', n_apps: 1341, n_users: 777, n_jobs: 68, status: 'active' },
    { client_id: 8, name: 'selfopportunity.com', n_apps: 1285, n_users: 1196, n_jobs: 199, status: 'active' },
    { client_id: 9, name: 'unitedhealth group', n_apps: 1248, n_users: 1203, n_jobs: 586, status: 'active' },
    { client_id: 10, name: 'dr pepper snapple group', n_apps: 1185, n_users: 1166, n_jobs: 317, status: 'active' },
    { client_id: 11, name: 'volt', n_apps: 1176, n_users: 1058, n_jobs: 217, status: 'active' },
    { client_id: 12, name: 'expresspros.com', n_apps: 1151, n_users: 1134, n_jobs: 169, status: 'active' },
    { client_id: 13, name: 'otcmarkets.com', n_apps: 1099, n_users: 951, n_jobs: 272, status: 'active' },
    { client_id: 14, name: 'elitestaffinginc.com', n_apps: 1080, n_users: 972, n_jobs: 92, status: 'active' },
    { client_id: 15, name: 'express employment professionals', n_apps: 1044, n_users: 961, n_jobs: 107, status: 'active' },
    { client_id: 16, name: 'oce.com', n_apps: 1026, n_users: 931, n_jobs: 29, status: 'active' },
    { client_id: 17, name: 'remingtoncollege.edu', n_apps: 1001, n_users: 874, n_jobs: 68, status: 'active' },
    { client_id: 18, name: 'ultimatestaffing.com', n_apps: 1000, n_users: 873, n_jobs: 101, status: 'active' },
    { client_id: 19, name: 'volt workforce solutions', n_apps: 937, n_users: 863, n_jobs: 128, status: 'active' },
    { client_id: 20, name: 'workway', n_apps: 920, n_users: 720, n_jobs: 109, status: 'active' },
  ];
  const bases = [
    'apex staffing', 'aerotek', 'kelly services', 'manpower', 'adecco',
    'robert half', 'kforce', 'insight global', 'teksystems', 'modis',
    'cybercoders', 'judge group', 'lucas group', 'beacon hill', 'atrium',
    'proclinical', 'medpro', 'careerstaff', 'firstpro', 'staffmark',
  ];
  const tails = ['solutions', 'group', 'partners', 'services', 'inc', 'staffing', 'consulting', 'network', 'global', 'corp', 'systems', 'associates', 'enterprises', 'agency', 'team'];
  const rnd = makeRng(20261108);
  const clients = [...topV3];
  // Cùng quy mô với dữ liệu thật CareerBuilder V3: 9.116 client (employer có >= 10 application).
  for (let i = topV3.length; i < DEMO_CLIENT_COUNT; i += 1) {
    const nApps = Math.round(10 + Math.pow(rnd(), 2.8) * 900);
    const nJobs = Math.max(1, Math.round(nApps * (0.12 + rnd() * 0.25)));
    const nUsers = Math.max(1, Math.round(nApps * (0.65 + rnd() * 0.3)));
    clients.push({
      client_id: i,
      name: `${bases[Math.floor(rnd() * bases.length)]} ${tails[Math.floor(rnd() * tails.length)]} #${i}`,
      n_apps: nApps,
      n_users: nUsers,
      n_jobs: nJobs,
      status: nApps >= 50 ? 'active' : 'idle',
    });
  }
  state.clients = clients;
  state.clientsTotal = clients.length;
  state.serverPaged = false;
  state.page = 0;
  sortClients();
}

function startDemoLoop() {
  stopDemoLoop();
  // DEMO: không tự chạy train; chỉ chờ người dùng bấm "Chạy demo" / Start.
  $('runBadge').dataset.tone = '';
  setBadge($('runBadge'), '', 'demo');
  state.demo = { ticks: null, round: 0 };
}

function stopDemoLoop() {
  if (state.demo && state.demo.ticks) clearInterval(state.demo.ticks);
  if (state.demo) state.demo.ticks = null;
}

/* ------------------------------------------------------------------ */
/* Tải dữ liệu live                                                    */
/* ------------------------------------------------------------------ */

async function loadLiveData() {
  await checkHealth({ silent: true });
  if (state.mode !== 'live') return;
  await Promise.allSettled([loadSummary(), loadClients()]);
  renderTable();
  ncRefresh();
  $('refreshBtn').disabled = false;
}

async function loadSummary() {
  try {
    const s = await apiFetch('/api/graph/summary', { timeout: 20000 });
    state.summary = s;
    renderSummary(s);
  } catch (err) {
    logEvent(`Không tải được /api/graph/summary: ${err.message}`, 'lg-error');
  }
}

function renderSummary(s) {
  const map = [
    ['sUsers', s.n_users],
    ['sJobs', s.n_jobs],
    ['sSkills', s.n_skills],
    ['sOcc', s.n_occupations],
    ['sUJ', s.n_edges_user_job],
    ['sJS', s.n_edges_job_skill],
    ['sUS', s.n_edges_user_skill],
    ['sClients', s.n_clients],
  ];
  map.forEach(([id, v]) => {
    const el = $(id);
    el.textContent = fmtInt(v);
    el.closest('.strip-item').dataset.pending = '0';
  });
  const sp = $('sSparse');
  sp.textContent = s.sparsity_pct === null || s.sparsity_pct === undefined ? '—' : `${fmtNum(s.sparsity_pct, 2)} %`;
  sp.closest('.strip-item').dataset.pending = '0';
  $('clientTotal').textContent = fmtInt(s.n_clients);
}

async function loadClients() {
  $('tableNote').textContent = 'đang tải danh sách…';
  const all = [];
  let total = null;
  let offset = 0;
  let completed = false;

  for (let p = 0; p < MAX_FETCH_PAGES; p += 1) {
    try {
      const r = await apiFetch(`/api/clients?limit=${CLIENT_PAGE_FETCH}&offset=${offset}`, { timeout: 15000 });
      const items = Array.isArray(r.items) ? r.items : [];
      if (total === null) total = Number(r.total) || items.length;
      all.push(...items);
      offset += items.length;
      if (!items.length || all.length >= total) {
        completed = true;
        break;
      }
    } catch (err) {
      logEvent(`Tải /api/clients lỗi ở offset ${offset}: ${err.message}`, 'lg-error');
      break;
    }
  }

  if (!completed && total !== null && all.length < total) {
    // Backend chặn tải toàn bộ: quay về phân trang phía server.
    state.serverPaged = true;
    state.clientsTotal = total;
    state.clients = [];
    state.page = 0;
    logEvent(`Backend trả tối đa ${all.length}/${fmtInt(total)} client mỗi lượt — dùng phân trang phía server.`);
    await loadClientPage();
    return;
  }

  state.serverPaged = false;
  state.clients = all;
  state.clientsTotal = total ?? all.length;
  $('clientTotal').textContent = fmtInt(state.clientsTotal);
  $('refreshBtn').disabled = false;
  logEvent(`Đã tải ${fmtInt(state.clients.length)} client từ backend.`, 'lg-dim');
  sortClients();
  renderTable();
  ncRefresh();
}

function sortClients() {
  const { key, dir } = state.sort;
  const mul = dir === 'asc' ? 1 : -1;
  state.clients.sort((a, b) => {
    const av = a?.[key];
    const bv = b?.[key];
    if (typeof av === 'string' || typeof bv === 'string') {
      return String(av ?? '').localeCompare(String(bv ?? ''), 'vi') * mul;
    }
    return ((Number(av) || 0) - (Number(bv) || 0)) * mul;
  });
}

async function loadClientPage() {
  const { key, dir } = state.sort;
  const q = new URLSearchParams({ limit: String(state.pageSize), offset: String(state.page * state.pageSize) });
  if (SORT_SERVER_KEYS.has(key)) {
    q.set('sort', key);
    q.set('order', dir);
  }
  try {
    const r = await apiFetch(`/api/clients?${q.toString()}`, { timeout: 10000 });
    state.clients = Array.isArray(r.items) ? r.items : [];
    state.clientsTotal = Number(r.total) || state.clients.length;
    $('clientTotal').textContent = fmtInt(state.clientsTotal);
    // sắp xếp tại chỗ cho trang hiện tại (backend có thể bỏ qua tham số sort)
    sortClients();
    renderTable();
  } catch (err) {
    logEvent(`Tải trang client lỗi: ${err.message}`, 'lg-error');
    $('clientBody').innerHTML = `<tr><td colspan="6" class="table-state">Không tải được danh sách client từ backend.</td></tr>`;
  }
}

/* ------------------------------------------------------------------ */
/* Bảng client                                                         */
/* ------------------------------------------------------------------ */

function currentRows() {
  if (state.serverPaged) return state.clients;
  const start = state.page * state.pageSize;
  return state.clients.slice(start, start + state.pageSize);
}

function statusTone(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'active' || s === 'ok' || s === 'online' || s === 'training') return 'ok';
  if (s === 'idle' || s === 'pending' || s === 'ready') return 'pending';
  if (s === 'failed' || s === 'error' || s === 'offline') return 'bad';
  return 'pending';
}

function renderTable() {
  const body = $('clientBody');
  const rows = currentRows();
  const total = state.clientsTotal || state.clients.length;
  const pages = Math.max(1, Math.ceil(total / state.pageSize));

  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="6" class="table-state">${
      state.mode === 'demo' ? 'Không có client trong dữ liệu giả lập.' : 'Chưa có client — kiểm tra /api/clients.'
    }</td></tr>`;
  } else {
    body.innerHTML = rows
      .map((c) => {
        const tone = statusTone(c.status);
        const selected = Number(c.client_id) === Number(state.selectedClientId) ? ' is-selected' : '';
        return `<tr data-client="${esc(c.client_id)}" class="${selected}" tabindex="0">
          <td class="num">${esc(c.client_id)}</td>
          <td class="name-cell" title="${esc(c.name)}">${esc(c.name || '—')}</td>
          <td class="num">${fmtInt(c.n_apps)}</td>
          <td class="num">${fmtInt(c.n_users)}</td>
          <td class="num">${fmtInt(c.n_jobs)}</td>
          <td><span class="status-cell"><span class="dot ${tone === 'pending' ? 'pending' : tone}"></span>${esc(c.status || 'unknown')}</span></td>
        </tr>`;
      })
      .join('');
  }

  $('pageInfo').textContent = `trang ${state.page + 1} / ${pages}`;
  $('rowInfo').textContent = `${fmtInt(total)} client`;
  $('prevPage').disabled = state.page <= 0;
  $('nextPage').disabled = state.page + 1 >= pages;
  $('tableNote').textContent = state.serverPaged
    ? 'phân trang phía server'
    : `sắp xếp theo ${state.sort.key} ${state.sort.dir === 'asc' ? 'tăng' : 'giảm'}`;

  $$('.th-sort').forEach((btn) => {
    const active = btn.dataset.sort === state.sort.key;
    btn.dataset.active = active ? '1' : '0';
    const arrow = btn.querySelector('.arrow');
    if (arrow) arrow.textContent = active ? (state.sort.dir === 'asc' ? '▲' : '▼') : '·';
  });
}

const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function selectClientRow(clientId) {
  state.selectedClientId = clientId;
  $$('#clientBody tr').forEach((tr) => {
    tr.classList.toggle('is-selected', Number(tr.dataset.client) === Number(clientId));
  });
  const box = $('detailBox');
  box.classList.remove('is-off');
  // mở luôn panel trace của node (yêu cầu "bấm một ô node ra trace")
  ncTraceSelect(clientId);

  const local = state.clients.find((c) => Number(c.client_id) === Number(clientId));
  if (state.mode === 'demo' || !local) {
    if (local) renderClientDetail(local);
    return;
  }
  try {
    const d = await apiFetch(`/api/clients/${encodeURIComponent(clientId)}`, { timeout: 8000 });
    renderClientDetail(d);
  } catch (err) {
    renderClientDetail(local);
    logEvent(`Không tải chi tiết client ${clientId}: ${err.message}`, 'lg-error');
  }
}

function renderClientDetail(c) {
  $('detailName').textContent = c.name || '—';
  $('detailId').textContent = `#${c.client_id}`;
  $('detailCounts').textContent =
    `${fmtInt(c.n_apps)} application · ${fmtInt(c.n_users)} người dùng · ${fmtInt(c.n_jobs)} tin · ${c.status || 'unknown'}`;
  const skills = Array.isArray(c.top_skills) ? c.top_skills.slice(0, 10) : [];
  $('detailSkills').innerHTML = skills.length
    ? skills.map((s) => `<span class="skill-chip">${esc(s)}</span>`).join('')
    : '<span style="font-size:11.5px;color:var(--ink-3)">không có top_skills trong response</span>';
}

/* ------------------------------------------------------------------ */
/* Lưới node                                                           */
/* ------------------------------------------------------------------ */

function buildNodeGrid(participants) {
  const grid = $('nodeGrid');
  grid.innerHTML = '';
  state.nodes.clear();
  const list = participants.slice(0, MAX_NODE_CELLS);
  if (!list.length) {
    grid.innerHTML = '<div class="node-empty">Bấm <strong>Start Training</strong> để tạo lưới node.</div>';
    return;
  }
  const frag = document.createDocumentFragment();
  list.forEach((cid, idx) => {
    const cell = document.createElement('button');
    cell.type = 'button';
    cell.className = 'node';
    cell.dataset.client = String(cid);
    cell.dataset.state = 'pending';
    cell.textContent = String(idx + 1);
    cell.title = `client ${cid} — chưa báo cáo`;
    cell.setAttribute('role', 'listitem');
    cell.addEventListener('click', () => {
      selectClientRow(cid);
      logEvent(`Chọn node client ${cid} từ lưới.`, 'lg-dim');
    });
    frag.appendChild(cell);
    state.nodes.set(Number(cid), { latency: null, state: 'pending', bytesUp: 0, bytesDown: 0 });
  });
  grid.appendChild(frag);
  updateNodeFoot();
}

function nodeCell(clientId) {
  return $('nodeGrid').querySelector(`.node[data-client="${clientId}"]`);
}

function paintNode(clientId, latency) {
  const cell = nodeCell(clientId);
  const key = Number(clientId);
  let rec = state.nodes.get(key);

  if (!cell) {
    // client báo cáo mà chưa có ô: thêm ô mới nếu còn chỗ
    const grid = $('nodeGrid');
    if (grid.querySelector('.node') === null) grid.innerHTML = '';
    if (state.nodes.size >= MAX_NODE_CELLS) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'node';
    btn.dataset.client = String(clientId);
    btn.dataset.state = 'pending';
    btn.textContent = String(state.nodes.size + 1);
    btn.addEventListener('click', () => selectClientRow(clientId));
    grid.appendChild(btn);
    rec = { latency: null, state: 'pending', bytesUp: 0, bytesDown: 0 };
    state.nodes.set(key, rec);
  }
  const el = cell || nodeCell(clientId);
  if (!el || !rec) return;

  rec.latency = Number(latency);
  rec.state = latState(latency);
  el.dataset.state = rec.state;
  el.title = `client ${clientId} · ${fmtMs(latency)}`;
  el.classList.add('is-fresh');
  setTimeout(() => el.classList.remove('is-fresh'), 260);
}

function updateNodeFoot() {
  const vals = [...state.nodes.values()].filter((n) => n.latency !== null).map((n) => n.latency);
  vals.sort((a, b) => a - b);
  const reported = vals.length;
  $('nodeReported').textContent = `${reported}/${state.nodes.size}`;
  $('nodeP50').textContent = fmtMs(percentile(vals, 0.5));
  $('nodeP95').textContent = fmtMs(percentile(vals, 0.95));
  $('nodeMax').textContent = fmtMs(vals.length ? vals[vals.length - 1] : null);
  $('nodeBytes').textContent = state.bytesTotal ? fmtBytes(state.bytesTotal) : '—';

  if (state.run) {
    $('nodeNote').textContent = `run ${String(state.run.run_id).slice(0, 8)}… · vòng ${state.runRound}/${state.run.total_rounds}`;
  }
}

/* ------------------------------------------------------------------ */
/* Biểu đồ                                                             */
/* ------------------------------------------------------------------ */

const CHART_FONT = 'Plex Mono, monospace';

function chartDefaults() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        display: true,
        position: 'top',
        align: 'end',
        labels: {
          boxWidth: 9,
          boxHeight: 9,
          usePointStyle: false,
          font: { family: CHART_FONT, size: 10 },
          color: '#475569',
          padding: 10,
        },
      },
      tooltip: {
        backgroundColor: '#FFFFFF',
        titleColor: '#0F172A',
        bodyColor: '#334155',
        borderColor: '#E2E8F0',
        borderWidth: 1,
        titleFont: { family: CHART_FONT, size: 11 },
        bodyFont: { family: CHART_FONT, size: 11 },
        padding: 10,
        cornerRadius: 8,
        displayColors: true,
      },
    },
    scales: {
      x: {
        grid: { color: '#F1F5F9', drawTicks: false },
        border: { color: '#E2E8F0' },
        ticks: { color: '#64748B', font: { family: CHART_FONT, size: 10 }, maxRotation: 0, autoSkipPadding: 12 },
        title: { display: true, text: 'vòng', color: '#64748B', font: { family: CHART_FONT, size: 10 } },
      },
      y: {
        grid: { color: '#F1F5F9', drawTicks: false },
        border: { color: '#E2E8F0' },
        ticks: { color: '#64748B', font: { family: CHART_FONT, size: 10 }, maxTicksLimit: 5 },
      },
    },
  };
}

function initCharts() {
  if (typeof Chart === 'undefined') {
    logEvent('Không tải được Chart.js — biểu đồ tắt, các phần còn lại vẫn chạy.', 'lg-error');
    return;
  }
  Chart.defaults.font.family = CHART_FONT;

  const ctxR = $('chartRecall').getContext('2d');
  chartRecall = new Chart(ctxR, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Recall@20',
          data: [],
          borderColor: '#FF5A1F',
          backgroundColor: 'rgba(255, 90, 31, 0.12)',
          borderWidth: 2,
          pointRadius: 2,
          pointBackgroundColor: '#EA580C',
          tension: 0.25,
          fill: true,
        },
      ],
    },
    options: (() => {
      const o = chartDefaults();
      o.scales.y.min = 0;
      o.scales.y.ticks.callback = (v) => Number(v).toFixed(2);
      o.plugins.tooltip.callbacks = { label: (c) => `Recall@20 ${Number(c.parsed.y).toFixed(4)}` };
      return o;
    })(),
  });

  const ctxL = $('chartLatency').getContext('2d');
  chartLatency = new Chart(ctxL, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'p50',
          data: [],
          borderColor: '#10B981',
          backgroundColor: 'rgba(16, 185, 129, 0.10)',
          borderWidth: 2,
          pointRadius: 2,
          pointBackgroundColor: '#10B981',
          tension: 0.25,
          fill: true,
        },
        {
          label: 'p95',
          data: [],
          borderColor: '#EF4444',
          backgroundColor: 'transparent',
          borderWidth: 2,
          borderDash: [4, 3],
          pointRadius: 2,
          pointBackgroundColor: '#EF4444',
          tension: 0.25,
        },
      ],
    },
    options: (() => {
      const o = chartDefaults();
      o.scales.y.min = 0;
      o.scales.y.ticks.callback = (v) => `${Math.round(v)} ms`;
      o.plugins.tooltip.callbacks = { label: (c) => `${c.dataset.label} ${Number(c.parsed.y).toFixed(1)} ms` };
      return o;
    })(),
  });
}

function resetCharts() {
  if (chartRecall) {
    chartRecall.data.labels = [];
    chartRecall.data.datasets.forEach((d) => {
      d.data = [];
    });
    chartRecall.update('none');
  }
  if (chartLatency) {
    chartLatency.data.labels = [];
    chartLatency.data.datasets.forEach((d) => {
      d.data = [];
    });
    chartLatency.update('none');
  }
  ['roRound', 'roRecall', 'roNdcg', 'roLoss', 'roP50', 'roP95'].forEach((id) => {
    $(id).textContent = '—';
  });
}

function pushMetric(round, metrics, latency) {
  const m = metrics || {};
  const point = {
    round: Number(round),
    recall20: Number(m.recall20 ?? m.recall ?? NaN),
    ndcg20: Number(m.ndcg20 ?? m.ndcg ?? NaN),
    mrr20: Number(m.mrr20 ?? m.mrr ?? NaN),
    loss: Number(m.loss ?? NaN),
  };
  const existing = state.metrics.findIndex((x) => x.round === point.round);
  if (existing >= 0) state.metrics[existing] = point;
  else state.metrics.push(point);
  state.metrics.sort((a, b) => a.round - b.round);

  if (chartRecall) {
    chartRecall.data.labels = state.metrics.map((x) => x.round);
    chartRecall.data.datasets[0].data = state.metrics.map((x) => (Number.isFinite(x.recall20) ? x.recall20 : null));
    chartRecall.update('none');
  }

  let p50 = null;
  let p95 = null;
  if (latency && typeof latency === 'object') {
    p50 = latency.p50 ?? latency.p50_ms ?? null;
    p95 = latency.p95 ?? latency.p95_ms ?? null;
  }
  p50 = typeof p50 === 'number' && Number.isFinite(p50) ? p50 : null;
  p95 = typeof p95 === 'number' && Number.isFinite(p95) ? p95 : null;

  // Ưu tiên percentile tính từ tick THẬT của đúng vòng này
  const bucket = state.latenciesByRound.get(point.round);
  if (bucket && bucket.size) {
    const sorted = [...bucket.values()].sort((a, b) => a - b);
    p50 = p50 !== null ? p50 : percentile(sorted, 0.5);
    p95 = p95 !== null ? p95 : percentile(sorted, 0.95);
  } else if (typeof latency === 'number' && Number.isFinite(latency)) {
    // /ws/train chỉ gửi một con số -> dùng cho cả hai, chờ tick đến để chính xác hơn
    p50 = p50 !== null ? p50 : latency;
    p95 = p95 !== null ? p95 : latency;
  }

  if (p50 !== null || p95 !== null) setLatencyPoint(point.round, p50, p95);

  $('roRound').textContent = String(point.round);
  $('roRecall').textContent = Number.isFinite(point.recall20) ? point.recall20.toFixed(4) : '—';
  $('roNdcg').textContent = Number.isFinite(point.ndcg20) ? point.ndcg20.toFixed(4) : '—';
  $('roLoss').textContent = Number.isFinite(point.loss) ? point.loss.toFixed(4) : '—';
}

/* Ghi/cập nhật một điểm latency của vòng, giữ nửa nào đã có nếu lần này thiếu. */
function setLatencyPoint(round, p50, p95) {
  const idx = state.latencySeries.findIndex((x) => x.round === round);
  if (idx >= 0) {
    const cur = state.latencySeries[idx];
    state.latencySeries[idx] = {
      round,
      p50: p50 !== null ? p50 : cur.p50,
      p95: p95 !== null ? p95 : cur.p95,
    };
  } else {
    state.latencySeries.push({ round, p50, p95 });
  }
  state.latencySeries.sort((a, b) => a.round - b.round);
  if (chartLatency) {
    chartLatency.data.labels = state.latencySeries.map((x) => x.round);
    chartLatency.data.datasets[0].data = state.latencySeries.map((x) => x.p50);
    chartLatency.data.datasets[1].data = state.latencySeries.map((x) => x.p95);
    chartLatency.update('none');
  }
  const last = state.latencySeries[state.latencySeries.length - 1];
  $('roP50').textContent = fmtMs(last.p50);
  $('roP95').textContent = fmtMs(last.p95);
}

/* Vẽ p50/p95 theo vòng. Chỉ vòng đã chốt (có message type='round') mới là điểm
   chính thức; nếu backend chưa gửi message vòng nào thì hiện tạm vòng đang chạy. */
function refreshLatencySeries() {
  const rounds = [...state.latenciesByRound.keys()].sort((a, b) => a - b);
  const official = rounds.filter((r) => state.completedRounds.has(r));
  const shown = official.length ? official : rounds.slice(-1);
  shown.forEach((round) => {
    const bucket = state.latenciesByRound.get(round);
    if (!bucket || !bucket.size) return;
    const sorted = [...bucket.values()].sort((a, b) => a - b);
    setLatencyPoint(round, percentile(sorted, 0.5), percentile(sorted, 0.95));
  });
}

/* ------------------------------------------------------------------ */
/* WebSocket                                                           */
/* ------------------------------------------------------------------ */

let wsRetryLatency = null;
let wsRetryTrain = null;
let wantLatencySocket = false;
let wantTrainSocket = false;

function setWsBadge() {
  const latOpen = state.wsLatency && state.wsLatency.readyState === WebSocket.OPEN;
  const trainOpen = state.wsTrain && state.wsTrain.readyState === WebSocket.OPEN;
  if (latOpen || trainOpen) {
    const which = latOpen && trainOpen ? 'live · 2 kênh' : 'live';
    setBadge($('wsBadge'), 'ok', which);
  } else if (state.mode === 'demo') {
    setBadge($('wsBadge'), 'warn', 'demo');
  } else {
    setBadge($('wsBadge'), 'bad', 'disconnected');
  }
}

function connectLatencySocket() {
  if (state.mode !== 'live') return;
  wantLatencySocket = true;
  if (state.wsLatency && (state.wsLatency.readyState === WebSocket.OPEN || state.wsLatency.readyState === WebSocket.CONNECTING)) return;
  let sock;
  try {
    sock = new WebSocket(wsUrl('/ws/latency'));
  } catch (err) {
    logEvent(`Không mở được WS /ws/latency: ${err.message}`, 'lg-error');
    scheduleLatencyRetry();
    return;
  }
  state.wsLatency = sock;
  $('wsUrlLabel').textContent = wsUrl('/ws/latency');

  sock.onopen = () => {
    setWsBadge();
    logEvent('WebSocket /ws/latency đã kết nối.', 'lg-dim');
  };
  sock.onmessage = (ev) => {
    let msg;
    try {
      msg = JSON.parse(ev.data);
    } catch (err) {
      return;
    }
    handleLatencyMessage(msg);
  };
  sock.onclose = () => {
    setWsBadge();
    if (wantLatencySocket) {
      logEvent('WS /ws/latency mất kết nối — thử lại sau 3s.', 'lg-error');
      checkHealth({ silent: true });
      scheduleLatencyRetry();
    }
  };
  sock.onerror = () => setWsBadge();
}

function scheduleLatencyRetry() {
  clearTimeout(wsRetryLatency);
  wsRetryLatency = setTimeout(() => {
    if (wantLatencySocket && state.mode === 'live') connectLatencySocket();
  }, WS_RETRY_MS);
}

function connectTrainSocket() {
  if (state.mode !== 'live' || !state.run) return;
  wantTrainSocket = true;
  const path = `/ws/train/${encodeURIComponent(state.run.run_id)}`;
  if (state.wsTrain && state.wsTrain.readyState === WebSocket.OPEN) state.wsTrain.close();
  let sock;
  try {
    sock = new WebSocket(wsUrl(path));
  } catch (err) {
    logEvent(`Không mở được WS ${path}: ${err.message}`, 'lg-error');
    scheduleTrainRetry();
    return;
  }
  state.wsTrain = sock;
  sock.onopen = () => {
    setWsBadge();
    logEvent(`WebSocket ${path} đã kết nối.`, 'lg-dim');
  };
  sock.onmessage = (ev) => {
    let msg;
    try {
      msg = JSON.parse(ev.data);
    } catch (err) {
      return;
    }
    handleTrainMessage(msg);
  };
  sock.onclose = () => {
    setWsBadge();
    if (wantTrainSocket) scheduleTrainRetry();
  };
  sock.onerror = () => setWsBadge();
}

function scheduleTrainRetry() {
  clearTimeout(wsRetryTrain);
  wsRetryTrain = setTimeout(() => {
    if (wantTrainSocket && state.mode === 'live' && state.run && state.runStatus === 'running') connectTrainSocket();
  }, WS_RETRY_MS);
}

function closeSockets() {
  wantLatencySocket = false;
  wantTrainSocket = false;
  clearTimeout(wsRetryLatency);
  clearTimeout(wsRetryTrain);
  if (state.wsLatency) {
    try { state.wsLatency.close(); } catch (e) { /* noop */ }
    state.wsLatency = null;
  }
  if (state.wsTrain) {
    try { state.wsTrain.close(); } catch (e) { /* noop */ }
    state.wsTrain = null;
  }
  setWsBadge();
}

function handleLatencyMessage(msg) {
  if (!msg || typeof msg !== 'object') return;
  if (msg.type === 'tick' || msg.latency_ms !== undefined) {
    const clientId = Number(msg.client_id);
    const latency = Number(msg.latency_ms);
    const roundNo = Number(msg.round ?? state.runRound);
    logTick({
      round: msg.round ?? state.runRound,
      clientId: msg.client_id,
      latency,
      bytesUp: msg.bytes_up,
      bytesDown: msg.bytes_down,
      ts: msg.ts,
    });
    if (state.run && msg.run_id && String(msg.run_id) !== String(state.run.run_id)) {
      // tick của lượt chạy khác: vẫn log nhưng không bôi màu lưới
      return;
    }
    if (state.run) {
      paintNode(clientId, latency);
      // gom latency theo đúng vòng của tick để p50/p95 mỗi vòng không lẫn nhau
      if (!state.latenciesByRound.has(roundNo)) state.latenciesByRound.set(roundNo, new Map());
      state.latenciesByRound.get(roundNo).set(clientId, latency);
      state.bytesTotal += (Number(msg.bytes_up) || 0) + (Number(msg.bytes_down) || 0);
      updateNodeFoot();
      refreshLatencySeries();
      // --- phần giải thích: ghi trace riêng của node + đẩy sơ đồ 5 bước ---
      ncTraceRecord(clientId, roundNo, latency, msg.bytes_up, msg.bytes_down);
      ncFlowOnTick(roundNo);
      ncRefresh();
    }
    return;
  }
  if (msg.type === 'round') {
    handleTrainMessage(msg);
  }
}

function handleTrainMessage(msg) {
  if (!msg || typeof msg !== 'object') return;

  if (msg.type === 'round' || msg.round !== undefined) {
    const round = Number(msg.round);
    state.runRound = Number.isFinite(round) ? round : state.runRound + 1;
    pushMetric(state.runRound, msg.metrics, msg.latency_ms);
    state.completedRounds.add(state.runRound);
    refreshLatencySeries();
    const bucket = state.latenciesByRound.get(state.runRound);
    const sorted = bucket ? [...bucket.values()].sort((a, b) => a - b) : [];
    const p50 = percentile(sorted, 0.5);
    const p95 = percentile(sorted, 0.95);
    if (p50 !== null) {
      logEvent(
        `vòng ${state.runRound}/${state.run ? state.run.total_rounds : '?'} — p50 ${p50.toFixed(1)} ms · p95 ${(p95 ?? 0).toFixed(1)} ms`,
        'lg-dim',
      );
    }
    updateNodeFoot();
    $('runRound').textContent = state.run ? `${state.runRound} / ${state.run.total_rounds}` : String(state.runRound);
    ncFlowOnRound(state.runRound);
    ncRefresh();
    if (state.run && state.run.total_rounds && state.runRound >= state.run.total_rounds) {
      logEvent('Đã tới vòng cuối — chờ backend chốt trạng thái.', 'lg-dim');
      setTimeout(() => refreshRunStatus(), 900);
    }
    return;
  }
  if (msg.type === 'status') {
    setRunStatus(msg.status, msg.detail);
  }
}

/* ------------------------------------------------------------------ */
/* Lượt chạy                                                           */
/* ------------------------------------------------------------------ */

function setRunStatus(status, detail) {
  const prev = state.runStatus;
  state.runStatus = status;
  if ((status === 'done' || status === 'completed' || status === 'failed') && (prev === 'done' || prev === 'completed' || prev === 'failed')) {
    // đã chốt rồi: không log/không vẽ lại
    return;
  }
  const tone = status === 'running' ? 'warn' : status === 'done' || status === 'completed' ? 'ok' : status === 'failed' ? 'bad' : '';
  const text = status === 'running' ? 'đang chạy' : status === 'done' || status === 'completed' ? 'hoàn tất' : status === 'failed' ? 'lỗi' : 'idle';
  setBadge($('runBadge'), tone, text);
  $('runStatus').textContent = detail ? `${text} (${detail})` : text;
  $('startBtn').disabled = status === 'running';
  $('startBtnTop').disabled = status === 'running';
  $('stopBtn').disabled = status !== 'running';
  $('nClients').disabled = status === 'running';
  $('rounds').disabled = status === 'running';
  $('algorithm').disabled = status === 'running';
  $('localEpochs').disabled = status === 'running';
  // sơ đồ 5 bước bám theo trạng thái lượt chạy
  if (status === 'running') {
    if (ncState.step === 0) ncFlowStart(state.runRound || 0);
  } else {
    ncFlowStop(status);
  }
  ncRefresh();
}

function resetRun({ keepLog = false } = {}) {
  wantTrainSocket = false;
  if (state.wsTrain) {
    try { state.wsTrain.close(); } catch (e) { /* noop */ }
    state.wsTrain = null;
  }
  state.run = null;
  state.runRound = 0;
  state.metrics = [];
  state.latencySeries = [];
  state.roundLatencies = [];
  state.latenciesByRound = new Map();
  state.completedRounds = new Set();
  state.finishing = false;
  state.bytesTotal = 0;
  state.nodes.clear();
  $('nodeGrid').innerHTML =
    '<div class="node-empty">Bấm <strong>Start Training</strong> để tạo lưới node.<br />Mỗi ô vuông là một client (nhà tuyển dụng) trong lượt chạy; màu đổi theo độ trễ vòng hiện tại.</div>';
  $('nodeNote').textContent = 'chưa có lượt chạy';
  $('runId').textContent = '—';
  $('runRound').textContent = '—';
  $('runStatus').textContent = 'chưa chạy';
  $('runAlgo').textContent = '—';
  $('nodeReported').textContent = '0/0';
  ['nodeP50', 'nodeP95', 'nodeMax', 'nodeBytes'].forEach((id) => {
    $(id).textContent = '—';
  });
  setRunStatus('idle');
  resetCharts();
  // reset phần giải thích: trace cũ của lượt trước không được dính sang lượt mới
  ncState.traceRounds.clear();
  ncState.stepBytes = { up: null, down: null };
  ncState.roundTicks = 0;
  ncState.lastTickRound = 0;
  ncFlowStop('idle');
  ncRenderStay();
  if (ncState.traceId !== null) ncRenderTrace();
  if (!keepLog) logClear();
}

function participantIds(n) {
  const sorted = [...state.clients].sort((a, b) => (Number(b.n_apps) || 0) - (Number(a.n_apps) || 0));
  return sorted.slice(0, n).map((c) => Number(c.client_id));
}

async function startTraining() {
  const nClients = Number($('nClients').value);
  const rounds = Number($('rounds').value);
  const algorithm = $('algorithm').value;
  const localEpochs = Number($('localEpochs').value);

  resetRun({ keepLog: true });
  $('startBtn').disabled = true;
  $('startBtnTop').disabled = true;
  setRunStatus('running', 'đang khởi động');

  const participants = participantIds(nClients);
  if (participants.length && participants.length < nClients) {
    logEvent(
      `Chỉ có ${participants.length} client trong dữ liệu — dùng ${participants.length}/${nClients} client đã chọn.`,
      'lg-error',
    );
  }
  if (!participants.length) {
    // chưa tải xong client: dùng dải id liên tiếp để lưới vẫn hiện
    for (let i = 0; i < nClients; i += 1) participants.push(1000 + i);
  }
  state.run = { run_id: 'pending', total_rounds: rounds, participants, algorithm };
  buildNodeGrid(participants);
  // sơ đồ 5 bước bắt đầu từ BƯỚC 1 ngay khi bấm Start
  ncFlowStart(0);
  ncRenderStay();
  $('runAlgo').textContent = `${algorithm === 'fedprox' ? 'FedProx' : 'FedAvg'} · ${localEpochs} epoch`;
  logEvent(`Bắt đầu: ${nClients} client · ${rounds} vòng · ${algorithm} · local_epochs=${localEpochs}`, 'lg-event');

  if (state.mode === 'demo') {
    startDemoTraining({ nClients, rounds, algorithm, participants });
    return;
  }

  try {
    const resp = await apiFetch('/api/train/start', {
      method: 'POST',
      body: { n_clients: nClients, rounds, algorithm, local_epochs: localEpochs },
      timeout: 15000,
    });
    state.run.run_id = resp.run_id;
    $('runId').textContent = resp.run_id;
    // Dùng danh sách client THẬT do backend chọn (không đoán từ trang client
    // đang tải) -> lưới node khớp đúng số node sẽ báo cáo.
    if (Array.isArray(resp.participants) && resp.participants.length) {
      state.run.participants = resp.participants.map(Number);
      buildNodeGrid(state.run.participants);
      if (state.run.participants.length !== participants.length) {
        logEvent(
          `Backend chọn ${state.run.participants.length} client (giao diện ước ${participants.length}).`,
          'lg-dim',
        );
      }
    }
    logEvent(`run_id = ${resp.run_id}`, 'lg-event');
    connectLatencySocket();
    connectTrainSocket();
    // lấy trạng thái ban đầu một lần (không polling)
    setTimeout(() => refreshRunStatus({ announce: false }), 600);
  } catch (err) {
    logEvent(`POST /api/train/start lỗi: ${err.message}`, 'lg-error');
    setRunStatus('failed', err.message);
    if (typeof err.message === 'string' && /Failed to fetch|NetworkError|abort/i.test(err.message)) {
      enterDemoMode(`Không gọi được ${API_BASE}/api/train/start — đang hiển thị dữ liệu giả lập để xem giao diện.`);
      startDemoTraining({ nClients, rounds, algorithm, participants });
    }
  }
}

async function refreshRunStatus({ announce = true } = {}) {
  if (!state.run || state.mode === 'demo') return;
  if (state.finishing) return;
  try {
    const s = await apiFetch(`/api/train/status/${encodeURIComponent(state.run.run_id)}`, { timeout: 10000 });
    if (Array.isArray(s.metrics) && s.metrics.length) {
      s.metrics.forEach((m) => pushMetric(m.round, m, null));
    }
    if (Number.isFinite(Number(s.round))) {
      state.runRound = Number(s.round);
      $('runRound').textContent = `${state.runRound} / ${s.total_rounds ?? state.run.total_rounds}`;
    }
    if (s.total_rounds) state.run.total_rounds = s.total_rounds;
    if (Number.isFinite(Number(s.bytes_total))) {
      state.bytesTotal = Number(s.bytes_total);
      $('nodeBytes').textContent = fmtBytes(state.bytesTotal);
    }
    const status = String(s.status || '').toLowerCase();
    if (status === 'done' || status === 'completed') {
      if (state.finishing) return;
      state.finishing = true;
      setRunStatus('done');
      logEvent(`Hoàn tất lượt chạy: Recall@20 cuối = ${fmtNum(s.metrics?.at(-1)?.recall20, 4)} · p50 ${fmtMs(s.latency_p50_ms)} · p95 ${fmtMs(s.latency_p95_ms)} · ${fmtBytes(s.bytes_total)}`, 'lg-event');
      wantTrainSocket = false;
    } else if (status === 'failed') {
      if (state.finishing) return;
      state.finishing = true;
      setRunStatus('failed');
      logEvent('Backend báo lượt chạy thất bại.', 'lg-error');
      wantTrainSocket = false;
    } else if (status === 'running') {
      setRunStatus('running');
      if (announce) logEvent(`Đang chạy vòng ${state.runRound}/${state.run.total_rounds}…`, 'lg-dim');
    }
  } catch (err) {
    if (announce) logEvent(`GET /api/train/status lỗi: ${err.message}`, 'lg-error');
  }
}

function stopTraining() {
  if (!state.run) return;
  stopDemoLoop();
  wantTrainSocket = false;
  if (state.wsTrain) {
    try { state.wsTrain.close(); } catch (e) { /* noop */ }
    state.wsTrain = null;
  }
  setWsBadge();
  setRunStatus('stopped', 'client ngắt theo dõi');
  logEvent('Đã dừng theo dõi lượt chạy ở phía UI (hợp đồng API chưa có endpoint stop phía server).', 'lg-error');
  $('startBtn').disabled = false;
  $('startBtnTop').disabled = false;
  $('stopBtn').disabled = true;
}

/* ------------------------------------------------------------------ */
/* Mô phỏng cục bộ (DEMO MODE)                                         */
/* ------------------------------------------------------------------ */

function startDemoTraining({ nClients, rounds, algorithm, participants }) {
  stopDemoLoop();
  const runId = `demo-${Date.now().toString(36)}`;
  state.run.run_id = runId;
  $('runId').textContent = runId;
  setRunStatus('running', 'demo');
  $('runAlgo').textContent = `${algorithm === 'fedprox' ? 'FedProx' : 'FedAvg'} · demo`;
  logEvent(`DEMO: mô phỏng ${nClients} client · ${rounds} vòng cục bộ.`, 'lg-event');

  let round = 0;
  let baseP50 = 38;
  let recall = 0.31;
  const rnd = makeRng(9917);
  const nextRound = () => {
    round += 1;
    state.runRound = round;
    let idx = 0;

    const tickTimer = setInterval(() => {
      if (idx >= nClients) {
        clearInterval(tickTimer);
        return;
      }
      const cid = participants[idx];
      // vài client mạng chậm để thấy đủ 3 màu
      const slow = rnd() > 0.86 ? 3.6 : 1;
      const latency = Math.max(6, baseP50 * (0.55 + rnd() * 0.95) * slow);
      // đúng dải đã đo trên backend thật: up 12,5–15,5 KB · down 92,0–95,6 KB
      const bytesUp = 12800 + Math.round(rnd() * 3072);
      const bytesDown = 94208 + Math.round(rnd() * 3692);
      handleLatencyMessage({
        type: 'tick',
        run_id: runId,
        round,
        client_id: cid,
        latency_ms: Number(latency.toFixed(1)),
        bytes_up: bytesUp,
        bytes_down: bytesDown,
        ts: Date.now(),
      });
      idx += 1;
      if (idx >= nClients) {
        clearInterval(tickTimer);
        const recallNext = Math.min(0.62, recall + (0.62 - recall) * 0.24 + (rnd() - 0.5) * 0.012);
        recall = recallNext;
        const ndcg = recall * 0.56 + (rnd() - 0.5) * 0.01;
        const loss = Math.max(0.09, 1.55 * Math.exp(-0.22 * round) + (rnd() - 0.5) * 0.03);
        handleTrainMessage({
          type: 'round',
          round,
          metrics: { round, recall20: recall, ndcg20: ndcg, mrr20: ndcg * 1.02, loss },
          latency_ms: Number((baseP50 * (1.02 + rnd() * 0.12)).toFixed(1)),
        });
        baseP50 = 34 + rnd() * 26;
        if (round < rounds) {
          setTimeout(nextRound, 900);
        } else {
          setRunStatus('done', 'demo');
          logEvent(`DEMO: hoàn tất ${rounds} vòng · Recall@20 = ${recall.toFixed(4)}.`, 'lg-event');
          wantLatencySocket = false;
        }
      }
    }, Math.max(12, Math.round(1400 / Math.max(nClients, 20))));

    state.demo = { ticks: tickTimer, round };
  };

  setTimeout(nextRound, 350);
}

/* ================================================================== */
/* PHẦN GIẢI THÍCH (nc-*): một node là gì, 5 bước một vòng,           */
/* cái gì ở lại / truyền đi, trace chi tiết một node.                 */
/* Toàn bộ trạng thái suy ra từ sự kiện WS thật — không bịa số.       */
/* ================================================================== */

const NC_STEP_TEXT = {
  0: 'chưa chạy vòng nào',
  1: 'BƯỚC 1 · server gửi embedding xuống node',
  2: 'BƯỚC 2 · các node huấn luyện cục bộ',
  3: 'BƯỚC 3 · node gửi Δ embedding lên server',
  4: 'BƯỚC 4 · server cộng trung bình (FedAvg)',
  5: 'BƯỚC 5 · server gửi mô hình mới xuống',
};

const ncState = {
  step: 0,
  stepTimers: [],
  traceId: null,
  traceRounds: new Map(),   // client_id -> Map(round -> {train, up, down})
  traceSeen: new Map(),     // client_id -> Set(round) — đếm vòng thật
  roundTicks: 0,            // số node đã báo cáo trong vòng hiện tại
  lastTickRound: 0,
  lastTickAt: 0,
  stepBytes: { up: null, down: null },
};

/* ---------------- (1) "Một node là gì?" ---------------- */

function ncRenderWhat() {
  const totalEl = $('ncTotalNodes');
  const liveTotal = state.mode === 'live' ? (state.summary?.n_clients || state.clientsTotal) : 0;
  if (totalEl) totalEl.textContent = fmtInt(liveTotal || 9116);

  // Node ví dụ: client lớn nhất trong /api/clients (thật), fallback randstad.
  let top = state.clients && state.clients.length
    ? state.clients.reduce((a, b) => ((Number(b.n_apps) || 0) > (Number(a.n_apps) || 0) ? b : a), state.clients[0])
    : null;
  const isReal = state.mode === 'live' && top && top.name;
  if (!isReal) {
    top = { name: 'randstad', n_apps: 4745, n_users: 4215, n_jobs: 603 };
  }
  $('ncEmpName').textContent = top.name || '—';
  $('ncEmpApps').textContent = fmtInt(top.n_apps);
  $('ncEmpUsers').textContent = fmtInt(top.n_users);
  $('ncEmpJobs').textContent = fmtInt(top.n_jobs);
  $('ncEmpSource').textContent = isReal
    ? `số liệu thật từ /api/clients · client_id ${top.client_id ?? '—'}`
    : 'ví dụ mẫu — backend chưa kết nối (DEMO MODE)';
}

/* ---------------- (2) Sơ đồ 5 bước ---------------- */

function ncSetStep(step, note) {
  ncState.step = step;
  $$('.nc-step').forEach((el) => {
    el.classList.toggle('active', Number(el.dataset.step) === step);
  });
  const label = $('ncRoundState');
  if (label) label.textContent = note || NC_STEP_TEXT[step] || NC_STEP_TEXT[0];
}

/* Backend mô phỏng bắn hết tick của một vòng gần như tức thì: nếu đổi khối phát
   sáng ngay theo từng message thì BƯỚC 3 chỉ loé lên vài ms, người xem không kịp
   thấy. ncGoStep giữ mỗi bước tối thiểu một nhịp để sơ đồ "đi" đọc được. */
const NC_STEP_MIN_MS = 260;
const ncPace = { timer: null, pending: null, shownAt: 0 };

function ncGoStep(step, note) {
  clearTimeout(ncPace.timer);
  ncPace.timer = null;
  const wait = Math.max(0, NC_STEP_MIN_MS - (Date.now() - ncPace.shownAt));
  if (wait === 0) {
    ncPace.pending = null;
    ncPace.shownAt = Date.now();
    ncSetStep(step, note);
    return;
  }
  // đổi liên tiếp trong cùng một nhịp: chỉ giữ bước CUỐI, tránh nhấp nháy
  ncPace.pending = { step, note };
  ncPace.timer = setTimeout(() => {
    ncPace.timer = null;
    const p = ncPace.pending;
    ncPace.pending = null;
    if (!p) return;
    ncPace.shownAt = Date.now();
    ncSetStep(p.step, p.note);
  }, wait);
}

function ncClearStepTimers() {
  ncState.stepTimers.forEach((t) => clearTimeout(t));
  ncState.stepTimers = [];
  clearTimeout(ncPace.timer);
  ncPace.timer = null;
  ncPace.pending = null;
}

function ncLater(fn, ms) {
  const t = setTimeout(fn, ms);
  ncState.stepTimers.push(t);
  return t;
}

/* Bắt đầu lượt chạy / bắt đầu một vòng mới: server đang gửi embedding xuống. */
function ncFlowStart(round) {
  ncClearStepTimers();
  ncState.roundTicks = 0;
  ncState.lastTickRound = 0;
  const r = round ? `vòng ${round} · ` : '';
  ncGoStep(1, `${r}BƯỚC 1 · server gửi embedding xuống node`);
}

/* Tick của một node: node vừa train cục bộ xong và gửi Δ lên. */
function ncFlowOnTick(round) {
  if (round !== ncState.lastTickRound) {
    ncState.lastTickRound = round;
    ncState.roundTicks = 0;
  }
  ncState.roundTicks += 1;
  ncState.lastTickAt = Date.now();
  const expected = state.run && state.run.participants ? state.run.participants.length : 0;
  const r = `vòng ${round} · `;
  if (expected && ncState.roundTicks >= expected) {
    ncGoStep(3, `${r}BƯỚC 3 · đã nhận Δ embedding của ${fmtInt(ncState.roundTicks)} node`);
  } else if (ncState.step < 2 || ncState.step > 3) {
    ncGoStep(2, `${r}BƯỚC 2 · node huấn luyện cục bộ (${fmtInt(ncState.roundTicks)}/${fmtInt(expected || ncState.roundTicks)})`);
  }
  ncUpdateStepBytes();
}

/* Message type='round': server đã cộng trung bình xong -> bước 4 rồi bước 5. */
function ncFlowOnRound(round) {
  ncClearStepTimers();
  const total = state.run && state.run.total_rounds ? Number(state.run.total_rounds) : 0;
  const isLast = total > 0 && Number(round) >= total;
  const r = `vòng ${round} · `;
  ncGoStep(4, `${r}BƯỚC 4 · FedAvg cộng ${fmtInt(state.run?.participants?.length || ncState.roundTicks)} Δ embedding`);
  if (isLast) {
    // vòng cuối: không được hứa "chờ vòng N+1" vì không có vòng nào nữa
    ncLater(() => {
      ncSetStep(5, `vòng ${round}/${total} · BƯỚC 5 · mô hình cuối đã về server`);
    }, 650);
    return;
  }
  ncLater(() => {
    if (state.runStatus !== 'running') return;
    ncGoStep(5, `${r}BƯỚC 5 · gửi mô hình mới xuống, chờ vòng ${Number(round) + 1}`);
  }, 650);
  ncLater(() => {
    if (state.runStatus !== 'running') return;
    ncSetStep(1, `vòng ${Number(round) + 1} · BƯỚC 1 · server gửi embedding xuống node`);
  }, 1500);
}

function ncFlowStop(status) {
  ncClearStepTimers();
  if (status === 'done' || status === 'completed') {
    ncSetStep(5, `hoàn tất ${state.runRound} vòng · mô hình cuối đã ở trên server`);
  } else if (status === 'failed') {
    ncSetStep(0, 'lượt chạy lỗi — dừng sơ đồ');
  } else if (status === 'stopped') {
    ncSetStep(0, 'đã dừng theo dõi');
  } else if (status === 'idle') {
    ncSetStep(0, 'chưa chạy vòng nào');
  }
}

/* Kích thước thật lấy từ WS: bytes_down (server → node) và bytes_up (node → server).
   Giá trị đo trên bản chạy thật đã biết: up 12,5–15,5 KB · down 92,0–95,6 KB mỗi
   node mỗi vòng. Khi có tick thật thì hiện đúng số đo được của lượt này. */
function ncUpdateStepBytes() {
  const ups = [];
  const downs = [];
  ncState.traceRounds.forEach((rounds) => {
    rounds.forEach((rec) => {
      if (Number.isFinite(rec.up) && rec.up > 0) ups.push(rec.up);
      if (Number.isFinite(rec.down) && rec.down > 0) downs.push(rec.down);
    });
  });
  if (!ups.length && !downs.length) return;
  const range = (arr) => {
    if (!arr.length) return null;
    let lo = Infinity;
    let hi = 0;
    arr.forEach((v) => {
      lo = Math.min(lo, v);
      hi = Math.max(hi, v);
    });
    return lo === hi ? fmtBytes(lo) : `${fmtBytes(lo)} – ${fmtBytes(hi)}`;
  };
  const upTxt = range(ups);
  const downTxt = range(downs);
  if (upTxt) $('ncStep3Bytes').textContent = `${upTxt} / node (đo từ WS)`;
  if (downTxt) {
    $('ncStep1Bytes').textContent = `${downTxt} / node (đo từ WS)`;
    $('ncStep5Bytes').textContent = `${downTxt} / node (đo từ WS)`;
  }
}

/* ---------------- (3) Ở LẠI MÁY / TRUYỀN ĐI ---------------- */

function ncSelectedClient() {
  const id = ncState.traceId ?? state.selectedClientId;
  if (id === null || id === undefined) return null;
  return state.clients.find((c) => Number(c.client_id) === Number(id)) || null;
}

function ncTraceRecs(clientId) {
  const map = ncState.traceRounds.get(Number(clientId));
  if (!map) return [];
  return [...map.values()].sort((a, b) => a.round - b.round);
}

function ncRenderStay() {
  const c = ncSelectedClient();
  const recs = c ? ncTraceRecs(c.client_id) : [];
  const last = recs.length ? recs[recs.length - 1] : null;

  // --- Ở LẠI MÁY: số dòng thật của node đang chọn (rỗng = chưa chọn) ---
  const rows = {
    users: c ? fmtInt(c.n_users) : '—',
    jobs: c ? fmtInt(c.n_jobs) : '—',
    apps: c ? fmtInt(c.n_apps) : '—',
  };
  $$('#ncStayList [data-row]').forEach((el) => {
    el.textContent = rows[el.dataset.row] || '—';
  });
  // tổng dòng thô = application + user + job (không cộng trùng rating/lịch sử vì
  // hai thứ đó là cột nằm TRONG bảng application)
  const totalRows = c ? (Number(c.n_apps) || 0) + (Number(c.n_users) || 0) + (Number(c.n_jobs) || 0) : 0;
  $('ncStayRows').textContent = c ? fmtInt(totalRows) : '—';
  $('ncStayBreak').textContent = c
    ? `${fmtInt(c.n_apps)} application + ${fmtInt(c.n_users)} user + ${fmtInt(c.n_jobs)} job`
    : '—';

  // --- TRUYỀN ĐI: độ lớn embedding + byte thật từ WS ---
  let dim = 64;
  if (c) dim = Math.min(256, Math.max(32, (Number(c.n_users) || 0) + (Number(c.n_jobs) || 0)));
  const nNodes = state.run && state.run.participants ? state.run.participants.length : 0;
  $('ncSendShape').textContent = c
    ? `${fmtInt(dim)} × 1 (node này${nNodes ? ` trong ${fmtInt(nNodes)} node` : ''})`
    : nNodes
      ? `${fmtInt(64)} × ${fmtInt(nNodes)}`
      : 'dim × node';

  $('ncSendUp').textContent = last && Number.isFinite(last.up) ? fmtBytes(last.up) : '—';
  $('ncSendDown').textContent = last && Number.isFinite(last.down) ? fmtBytes(last.down) : '—';
  const trueRounds = c ? ncTraceRoundCount(c.client_id) : 0;
  $('ncSendRounds').textContent = trueRounds ? `${fmtInt(trueRounds)} vòng` : '0';
  $('ncSendTotal').textContent = state.bytesTotal ? fmtBytes(state.bytesTotal) : '—';

  const badge = $('ncStayBadge');
  if (state.runStatus === 'running') {
    setBadge(badge, 'warn', 'đang chạy');
    $('ncStayNote').textContent = c ? `node ${c.name || c.client_id}` : 'đang đổ số liệu theo vòng';
  } else if (state.runStatus === 'done' || state.runStatus === 'completed') {
    setBadge(badge, 'ok', 'hoàn tất');
    $('ncStayNote').textContent = c ? `node ${c.name || c.client_id}` : 'số liệu vòng cuối';
  } else {
    setBadge(badge, '', 'chưa chạy');
    $('ncStayNote').textContent = c ? `node ${c.name || c.client_id}` : 'số liệu của node đang chọn';
  }

  $('ncSendFoot').innerHTML = recs.length
    ? `Node này đã trao đổi <b>${fmtInt(recs.length)}</b> vòng · mỗi vòng gửi vài chục KB tham số, không gửi dòng dữ liệu nào.`
    : 'Bấm <b>Start Training</b> để xem số byte thật của từng vòng.';
}

/* ---------------- (4) Trace một node ---------------- */

function ncTraceSelect(clientId) {
  if (clientId === null || clientId === undefined) return;
  ncState.traceId = Number(clientId);
  const panel = $('ncTracePanel');
  panel.classList.remove('is-off');
  $('ncTraceEmpty').classList.add('is-off');
  $('ncTraceContent').classList.remove('is-off');
  $$('#nodeGrid .node').forEach((el) => {
    el.dataset.trace = Number(el.dataset.client) === ncState.traceId ? '1' : '0';
  });
  // tải chi tiết client (nếu live) để có tên + số app/user/job; lỗi thì dùng dữ liệu bảng
  const local = state.clients.find((c) => Number(c.client_id) === ncState.traceId);
  ncRenderTrace(local);
  ncRenderStay();
  if (state.mode === 'live' && ncState.traceId !== null) {
    apiFetch(`/api/clients/${encodeURIComponent(ncState.traceId)}`, { timeout: 8000 })
      .then((d) => {
        if (Number(d?.client_id) === ncState.traceId) ncRenderTrace(d);
      })
      .catch(() => { /* giữ dữ liệu từ bảng, không làm hỏng trace */ });
  }
}

function ncTraceClose() {
  ncState.traceId = null;
  $('ncTracePanel').classList.add('is-off');
  $('ncTraceEmpty').classList.remove('is-off');
  $('ncTraceContent').classList.add('is-off');
  $$('#nodeGrid .node').forEach((el) => {
    el.dataset.trace = '0';
  });
  ncRenderStay();
}

function ncNodeState() {
  // client_id có thể là 0 (randstad) -> phải so sánh với null, không dùng truthy
  if (ncState.traceId === null || ncState.traceId === undefined) return 'idle';
  if (state.runStatus !== 'running') return 'idle';
  const recs = ncTraceRecs(ncState.traceId);
  const last = recs.length ? recs[recs.length - 1] : null;
  // chưa có tick nào trong vòng hiện tại -> node đang train cục bộ
  if (!last || last.round < state.runRound) return 'training';
  // vừa nhận tick của node -> nó đang đẩy Δ embedding lên
  if (Date.now() - ncState.lastTickAt < 420) return 'uploading';
  // đã gửi xong, chờ server FedAvg rồi phát vòng mới
  return 'waiting';
}

const NC_STATE_DESC = {
  idle: 'chưa có vòng nào — node đang chờ lệnh Start',
  training: 'đang chạy SGD trên dữ liệu CỦA MÌNH — chưa gửi gì ra ngoài',
  uploading: 'đang gửi Δ embedding lên server (chỉ tham số, không phải dữ liệu)',
  waiting: 'đã gửi xong — chờ server FedAvg và gửi vòng mới xuống',
};

function ncRenderTrace(client) {
  const id = ncState.traceId;
  if (id === null || id === undefined) return;
  const c = client || state.clients.find((x) => Number(x.client_id) === Number(id)) || null;
  $('ncTraceName').textContent = c && c.name ? c.name : `client ${id}`;
  const boardId = c && c.client_id !== undefined ? c.client_id : id;
  $('ncTraceId').textContent = `client_id #${boardId}${c && c.status ? ` · ${c.status}` : ''}`;
  $('ncTraceCounts').textContent = c
    ? `${fmtInt(c.n_apps)} application · ${fmtInt(c.n_users)} ứng viên · ${fmtInt(c.n_jobs)} tin tuyển dụng`
    : 'chưa có số liệu client (backend chưa trả)';

  const recs = ncTraceRecs(id);
  const trueRounds = ncTraceRoundCount(id);
  const last = recs.length ? recs[recs.length - 1] : null;
  $('ncTraceTrain').textContent = last && Number.isFinite(last.train) ? fmtMs(last.train) : '—';
  $('ncTraceUp').textContent = last && Number.isFinite(last.up) ? fmtBytes(last.up) : '—';
  $('ncTraceDown').textContent = last && Number.isFinite(last.down) ? fmtBytes(last.down) : '—';

  // loss: backend chỉ công bố loss toàn cục theo vòng -> ghi rõ nguồn
  const metric = state.metrics.find((m) => m.round === (last ? last.round : state.runRound));
  $('ncTraceLoss').textContent = metric && Number.isFinite(metric.loss) ? metric.loss.toFixed(4) : '—';

  const st = ncNodeState();
  const stEl = $('ncTraceState');
  stEl.dataset.state = st;
  stEl.innerHTML = `<span class="dot"></span><b>${st}</b>`;
  $('ncTraceStateDesc').textContent = NC_STATE_DESC[st] || '';

  $('ncTraceRounds').textContent = `${fmtInt(trueRounds)} vòng`;
  const tl = $('ncTraceTimeline');
  const recent = recs.slice(-5).reverse();
  if (!recent.length) {
    tl.innerHTML = '<div class="nc-trace-tl-empty">Chưa có vòng nào. Bấm <b>Start Training</b> để node này bắt đầu làm việc.</div>';
  } else {
    tl.innerHTML = recent
      .map((rec) => {
        const lossAt = state.metrics.find((m) => m.round === rec.round);
        const loss = lossAt && Number.isFinite(lossAt.loss) ? ` · loss ${lossAt.loss.toFixed(3)}` : '';
        return `<div class="nc-tl-row">
          <span class="nc-tl-round">vòng ${esc(rec.round)}</span>
          <span class="nc-tl-main">train <b>${fmtMs(rec.train)}</b>${loss}</span>
          <span class="nc-tl-bytes">${fmtBytes(rec.up)}↑ ${fmtBytes(rec.down)}↓</span>
        </div>`;
      })
      .join('');
  }
}

function ncTraceRecord(clientId, round, latency, bytesUp, bytesDown) {
  const key = Number(clientId);
  if (!ncState.traceRounds.has(key)) ncState.traceRounds.set(key, new Map());
  const map = ncState.traceRounds.get(key);
  const r = Number(round);
  map.set(r, {
    round: r,
    train: Number(latency),
    up: Number(bytesUp),
    down: Number(bytesDown),
  });
  // đếm số vòng THẬT node đã tham gia (kể cả khi đã cắt bớt lịch sử để nhẹ RAM)
  if (!ncState.traceSeen.has(key)) ncState.traceSeen.set(key, new Set());
  ncState.traceSeen.get(key).add(r);
  // giữ tối đa 200 vòng gần nhất mỗi node (backend chặn rounds <= 200)
  if (map.size > 200) {
    const oldest = [...map.keys()].sort((a, b) => a - b)[0];
    map.delete(oldest);
  }
}

/* Số vòng THẬT node đã chạy — không phải số dòng đang lưu trong lịch sử. */
function ncTraceRoundCount(clientId) {
  const s = ncState.traceSeen.get(Number(clientId));
  return s ? s.size : 0;
}

/* Gọi lại mọi phần phụ thuộc trạng thái (dùng sau mỗi sự kiện). */
function ncRefresh({ trace = false } = {}) {
  ncRenderWhat();
  ncRenderStay();
  if (trace || ncState.traceId !== null) ncRenderTrace();
}

/* ------------------------------------------------------------------ */
/* Gắn sự kiện                                                         */
/* ------------------------------------------------------------------ */

function bindControls() {
  const traceCloseBtn = $('ncTraceClose');
  if (traceCloseBtn) traceCloseBtn.addEventListener('click', ncTraceClose);
  $('nClients').addEventListener('input', (e) => {
    $('nClientsVal').textContent = e.target.value;
  });
  $('rounds').addEventListener('input', (e) => {
    $('roundsVal').textContent = e.target.value;
  });
  $('localEpochs').addEventListener('input', (e) => {
    $('localEpochsVal').textContent = e.target.value;
  });
  $('algorithm').addEventListener('change', (e) => {
    $('algorithmVal').textContent = e.target.value === 'fedprox' ? 'FedProx' : 'FedAvg';
  });

  const start = () => startTraining();
  $('startBtn').addEventListener('click', start);
  $('startBtnTop').addEventListener('click', start);
  $('stopBtn').addEventListener('click', stopTraining);

  $('demoRunBtn').addEventListener('click', () => {
    if (state.mode !== 'demo') {
      enterDemoMode('Bạn đã chọn chạy thử giao diện bằng dữ liệu giả lập (DEMO MODE).');
    }
    startTraining();
  });

  $('modeBtn').addEventListener('click', () => {
    if (state.mode === 'demo') {
      logEvent('Chuyển sang chế độ backend thật…');
      enterLiveMode({});
    } else {
      enterDemoMode('Bạn đã chuyển sang DEMO MODE để xem giao diện.');
    }
  });

  $('retryBackendBtn').addEventListener('click', async () => {
    const ok = await checkHealth({ silent: true });
    if (ok) {
      enterLiveMode({});
      await loadLiveData();
    } else {
      $('demoReason').textContent = `Vẫn không kết nối được ${API_BASE}. Kiểm tra backend đã chạy chưa (uvicorn api.main:app --port 8000).`;
    }
  });

  $('refreshBtn').addEventListener('click', () => {
    if (state.mode === 'demo') {
      buildDemoClients();
      renderTable();
      return;
    }
    loadClients();
  });

  $('prevPage').addEventListener('click', async () => {
    if (state.page <= 0) return;
    state.page -= 1;
    if (state.serverPaged) await loadClientPage();
    else renderTable();
  });
  $('nextPage').addEventListener('click', async () => {
    const pages = Math.max(1, Math.ceil((state.clientsTotal || state.clients.length) / state.pageSize));
    if (state.page + 1 >= pages) return;
    state.page += 1;
    if (state.serverPaged) await loadClientPage();
    else renderTable();
  });
  $('pageSize').addEventListener('change', async (e) => {
    state.pageSize = Number(e.target.value) || 50;
    state.page = 0;
    if (state.serverPaged) await loadClientPage();
    else renderTable();
  });

  $$('.th-sort').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const key = btn.dataset.sort;
      if (state.sort.key === key) state.sort.dir = state.sort.dir === 'desc' ? 'asc' : 'desc';
      else {
        state.sort.key = key;
        state.sort.dir = key === 'name' ? 'asc' : 'desc';
      }
      state.page = 0;
      if (state.serverPaged) await loadClientPage();
      else {
        sortClients();
        renderTable();
      }
    });
  });

  $('clientBody').addEventListener('click', (e) => {
    const tr = e.target.closest('tr[data-client]');
    if (tr) selectClientRow(Number(tr.dataset.client));
  });
  $('clientBody').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const tr = e.target.closest('tr[data-client]');
    if (tr) {
      e.preventDefault();
      selectClientRow(Number(tr.dataset.client));
    }
  });

  $('clearLogBtn').addEventListener('click', () => {
    logClear();
    logEvent('Đã xoá log.', 'lg-dim');
  });

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && state.mode === 'live' && state.run && state.runStatus === 'running') {
      if (!state.wsTrain || state.wsTrain.readyState !== WebSocket.OPEN) connectTrainSocket();
      if (!state.wsLatency || state.wsLatency.readyState !== WebSocket.OPEN) connectLatencySocket();
    }
  });
}

/* ------------------------------------------------------------------ */
/* Khởi động                                                           */
/* ------------------------------------------------------------------ */

function loadChartJsFallback() {
  if (typeof Chart !== 'undefined') return;
  const s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
  s.onload = () => {
    initCharts();
    renderAll();
  };
  s.onerror = () => logEvent('Không tải được Chart.js từ local lẫn CDN — biểu đồ tắt.', 'lg-error');
  document.head.appendChild(s);
}

function renderAll() {
  renderTable();
  if (state.summary) renderSummary(state.summary);
  updateNodeFoot();
  ncRefresh();
}

function boot() {
  $('apiUrlLabel').textContent = API_BASE;
  $('wsUrlLabel').textContent = wsUrl('/ws/latency');

  initCharts();
  loadChartJsFallback();
  bindControls();
  setRunStatus('idle');
  setWsBadge();
  // 4 khối giải thích phải hiện NGAY, kể cả khi backend tắt (DEMO MODE)
  ncRenderWhat();
  ncRenderStay();
  ncSetStep(0);

  logEvent('FL Node Console khởi động. API base: ' + API_BASE, 'lg-dim');

  checkHealth({ silent: true }).then((ok) => {
    if (ok) {
      loadLiveData();
      connectLatencySocket();
    }
  });

  // heartbeat health mỗi 15s: chỉ để cập nhật badge, không phải polling dữ liệu train
  setInterval(() => {
    if (state.mode === 'live') checkHealth({ silent: true });
  }, 15000);

  // nhịp 250ms: chỉ vẽ lại trạng thái trace (training/uploading/waiting) khi panel
  // đang mở và lượt chạy đang chạy — không gọi API, không polling dữ liệu.
  setInterval(() => {
    if (ncState.traceId !== null && state.runStatus === 'running') ncRenderTrace();
  }, 250);

  initTactile3D();
}

function initTactile3D() {
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const shell = document.querySelector('.shell');
  if (!shell) return;
  let rafId = 0;
  let lastEvt = null;
  let lastSheen = null;
  let lastTilt = null;

  function resetCard(el, clearTilt) {
    if (!el) return;
    el.style.setProperty('--mx', '-999px');
    el.style.setProperty('--my', '-999px');
    if (clearTilt) el.style.transform = '';
  }

  shell.addEventListener('pointermove', (e) => {
    lastEvt = e;
    if (rafId) return;
    rafId = requestAnimationFrame(() => {
      rafId = 0;
      if (!lastEvt) return;
      const target = lastEvt.target;
      const sheenEl = target && target.closest ? target.closest('.panel, .nc-employer-card') : null;
      const tiltEl = target && target.closest ? target.closest('.nc-employer-card, .chart-panel') : null;

      if (lastSheen && lastSheen !== sheenEl) resetCard(lastSheen, false);
      if (lastTilt && lastTilt !== tiltEl) lastTilt.style.transform = '';
      lastSheen = sheenEl;
      lastTilt = tiltEl;

      if (sheenEl) {
        const r = sheenEl.getBoundingClientRect();
        sheenEl.style.setProperty('--mx', `${Math.round(lastEvt.clientX - r.left)}px`);
        sheenEl.style.setProperty('--my', `${Math.round(lastEvt.clientY - r.top)}px`);
      }
      if (tiltEl) {
        const r = tiltEl.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
          const nx = (lastEvt.clientX - r.left) / r.width - 0.5;
          const ny = (lastEvt.clientY - r.top) / r.height - 0.5;
          const rx = (-ny * 5).toFixed(2);
          const ry = (nx * 5).toFixed(2);
          tiltEl.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg)`;
        }
      }
    });
  }, { passive: true });

  shell.addEventListener('pointerleave', () => {
    resetCard(lastSheen, false);
    if (lastTilt) lastTilt.style.transform = '';
    lastSheen = null;
    lastTilt = null;
  });
}

document.addEventListener('DOMContentLoaded', boot);

