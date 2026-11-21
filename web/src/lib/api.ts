import type { GraphEdge3D, GraphNode3D } from '../components/three/types';

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? '';

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function wsUrl(path: string): string {
  if (API_BASE) {
    return `${API_BASE.replace(/^http/, 'ws')}${path}`;
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}${path}`;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status}${text ? `: ${text.slice(0, 160)}` : ''}`);
  }
  return (await res.json()) as T;
}

/* -------------------------------------------------------------------------- */
/* Core FL Live API Types (api/main.py)                                       */
/* -------------------------------------------------------------------------- */
export interface HealthResponse {
  status: string;
  db: boolean;
  artifacts: boolean;
}

export interface ClientRow {
  client_id: number;
  name?: string;
  n_apps: number;
  n_users: number;
  n_jobs: number;
}

export interface ClientsResponse {
  total: number;
  items: ClientRow[];
  data_source: string;
}

export interface TrainStartPayload {
  n_clients: number;
  rounds: number;
  algorithm: 'fedavg' | 'fedprox';
  local_epochs?: number;
}

export interface TrainStartResponse {
  run_id: string;
  status: string;
  n_clients: number;
  rounds: number;
  algorithm: 'fedavg' | 'fedprox';
  data_source: string;
  simulated_metrics: boolean;
  participants: number[];
  note: string;
}

export interface TrainStopResponse {
  run_id: string;
  status: string;
  stopped_at_round: number;
  already_stopped: boolean;
}

export interface RoundMetric {
  round: number;
  recall20: number;
  ndcg20: number;
  mrr20: number;
  loss: number;
}

export interface LatencyTickEvent {
  type: 'tick';
  run_id: string;
  round: number;
  client_id: number;
  latency_ms: number;
  bytes_up: number;
  bytes_down: number;
  ts: string;
}

export interface TrainRoundEvent {
  type: 'round';
  run_id: string;
  round: number;
  metrics: RoundMetric;
  latency_ms: number;
  status?: 'running' | 'done' | 'stopped' | 'failed';
  stopped?: boolean;
  stopped_at_round?: number;
}

/* -------------------------------------------------------------------------- */
/* V3 Dashboard API Types (CareerBuilder + O*NET — api/dashboard.py)          */
/* -------------------------------------------------------------------------- */
export interface V3Meta {
  n_nodes: number;
  n_users: number;
  n_jobs: number;
  n_occupations: number;
  n_skills: number;
  n_edges: number;
  public_edges: number;
  private_edges: number;
  public_edge_pct: number;
  private_edge_pct: number;
  e_user_job: number;
  e_job_occ: number;
  e_occ_skill: number;
  e_user_occ: number;
  n_train_uj: number;
  n_test_uj: number;
  n_test_clean: number;
  pg_job_skills: number;
  pg_user_skills: number;
  n_clients: number;
  pct_users_multi_client: number;
  n_users_multi_client: number;
  mean_clients_per_user: number;
  pct_same_client_test: number;
}

export interface V3FlUniverse {
  n_jobs_fl: number;
  n_jobs_fixed: number;
  n_jobs_occ: number;
  lightgcn: number;
  graphsage: number;
  item_knn: number;
  fedavg_20_fixed: number;
  fedavg_20_occ: number;
  fedavg_50: number;
  popularity: number;
  fedavg_20_ndcg: number;
  fedavg_20_mrr: number;
  fedavg_50_ndcg: number;
  fedavg_50_mrr: number;
  fedavg_20_occ_ndcg: number;
  fedavg_20_occ_mrr: number;
  fedavg_50_ci95?: number[];
}

export interface V3GlobalModelRow {
  model: string;
  kind: string;
  recall20: number;
  ndcg20: number;
  mrr20: number;
  recall20_fl: number;
  recall20_ci95?: number[];
  seconds: number;
}

export interface V3Latency {
  p50_ms: number;
  p95_ms: number;
  mean_ms?: number;
  n_samples?: number;
}

export interface V3Employer {
  client_id: number;
  name: string;
  n_apps: number;
  n_jobs: number;
  n_users: number;
}

export interface OverviewResponse {
  dataset: string;
  meta: V3Meta;
  fl_universe: V3FlUniverse;
  global_universe: V3GlobalModelRow[];
  latency: V3Latency;
  top_employers: V3Employer[];
}

export interface GraphNodeRich extends GraphNode3D {
  kind_label: string;
}

export interface GraphEdgeRich extends GraphEdge3D {
  edge_label: string;
}

export interface GraphHit {
  id: string;
  kind: 'user' | 'job' | 'occupation' | 'skill';
  kind_label: string;
  label: string;
  degree: number;
}

export interface GraphResponse {
  summary: {
    total_nodes: number;
    total_edges: number;
    public_edges: number;
    private_edges: number;
    n_users: number;
    n_jobs: number;
    n_occupations: number;
    n_skills: number;
    e_user_job: number;
    e_job_occ: number;
    e_occ_skill: number;
    e_user_occ: number;
    sampled_nodes: number;
    sampled_edges: number;
    sampled_public_edges: number;
    sampled_private_edges: number;
    kind_counts: Record<'user' | 'job' | 'occupation' | 'skill', number>;
  };
  nodes: GraphNodeRich[];
  edges: GraphEdgeRich[];
  hits: GraphHit[];
  hit_ids: string[];
  query: { limit: number; q: string; kind: string };
}

export interface FlScenarioMetric {
  recall20: number;
  ndcg20: number;
  mrr20: number;
  coverage: number;
  seconds: number;
}

export interface FlScenarioCurvePoint {
  round: number;
  fl_recall20: number;
  fl_ndcg20: number;
  fl_mrr20: number;
  global_recall20: number;
  global_ndcg20: number;
  global_mrr20: number;
  loss: number;
  round_seconds: number;
}

export interface FlScenario {
  key: '20_fixed' | '20_occ' | '50_main' | '10_node' | '5_node' | string;
  label: string;
  short: string;
  n_clients: number;
  catalog_label: string;
  fl: FlScenarioMetric;
  global: FlScenarioMetric;
  curve: FlScenarioCurvePoint[];
}

export interface FlAblationRow {
  variant: string;
  note: string;
  recall10: number;
  recall20: number;
  ndcg20: number;
  mrr20: number;
  coverage: number;
  seconds: number;
  n_shard?: number;
  n_catalog?: number;
  universe?: string;
}

export interface FlSweepRow {
  n_clients: number;
  dim: number;
  layers: number;
  local_epochs: number;
  recall10: number;
  recall20: number;
  ndcg20: number;
  mrr20: number;
  coverage: number;
  seconds: number;
}

export interface FlSimResponse {
  scenarios: FlScenario[];
  baselines_fl: {
    lightgcn: number;
    graphsage: number;
    item_knn: number;
    popularity: number;
  };
  baselines_global: {
    item_knn: number;
    lightgcn: number;
    graphsage: number;
    gat: number;
    bpr_mf: number;
    popularity: number;
  };
  ablation: FlAblationRow[];
  sweep: FlSweepRow[];
  cross_silo: {
    n_clients: number;
    pct_users_multi_client: number;
    n_users_multi_client: number;
    mean_clients_per_user: number;
    pct_same_client_test: number;
    n_train_uj: number;
    n_test_uj: number;
  };
  latency: V3Latency;
  top_clients: V3Employer[];
}

export interface ConclusionRow {
  requirement: string;
  method: string;
  evidence: string;
  status: 'Đạt' | 'Chưa' | string;
  passed: boolean;
  page: string;
}

export interface ConclusionsResponse {
  summary: {
    total: number;
    passed: number;
    failed: number;
  };
  matrix: ConclusionRow[];
  achievements: Array<{ title: string; detail: string; tone: string }>;
  limitations: Array<{ title: string; detail: string; tone: 'warn' | 'bad' | string }>;
  next_steps: Array<{ direction: string; reason: string; estimate: string }>;
  lessons: Array<{ title: string; detail: string }>;
  reproducibility: {
    one_liner: string;
    steps: Array<{ command: string; description: string }>;
    script: string;
  };
}

/* -------------------------------------------------------------------------- */
/* API Functions                                                              */
/* -------------------------------------------------------------------------- */
export const api = {
  health: () => fetchJson<HealthResponse>('/health'),
  clients: (limit = 220, offset = 0) =>
    fetchJson<ClientsResponse>(
      `/api/clients?limit=${limit}&offset=${offset}&sort=n_apps&order=desc`
    ),
  trainStart: (payload: TrainStartPayload) =>
    fetchJson<TrainStartResponse>('/api/train/start', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  trainStop: (runId: string) =>
    fetchJson<TrainStopResponse>(`/api/train/stop/${encodeURIComponent(runId)}`, {
      method: 'POST',
    }),

  overview: () => fetchJson<OverviewResponse>('/api/dashboard/overview'),

  graph: async (params?: { limit?: number; q?: string; kind?: string }): Promise<GraphResponse> => {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.q) qs.set('q', params.q);
    if (params?.kind && params.kind !== 'all') qs.set('kind', params.kind);
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    const raw = await fetchJson<
      Omit<GraphResponse, 'nodes' | 'edges' | 'hits' | 'hit_ids'> & {
        nodes: Array<Omit<GraphNodeRich, 'id'> & { id: string | number }>;
        edges: Array<Omit<GraphEdgeRich, 'source' | 'target'> & { source: string | number; target: string | number }>;
        hits: Array<Omit<GraphHit, 'id'> & { id: string | number }>;
        hit_ids: Array<string | number>;
      }
    >(`/api/dashboard/graph${suffix}`);

    return {
      ...raw,
      nodes: raw.nodes.map((n) => ({
        ...n,
        id: String(n.id),
      })),
      edges: raw.edges.map((e) => ({
        ...e,
        source: String(e.source),
        target: String(e.target),
      })),
      hits: (raw.hits ?? []).map((h) => ({ ...h, id: String(h.id) })),
      hit_ids: (raw.hit_ids ?? []).map(String),
    };
  },

  flSim: () => fetchJson<FlSimResponse>('/api/dashboard/fl-sim'),

  conclusions: () => fetchJson<ConclusionsResponse>('/api/dashboard/conclusions'),
};
