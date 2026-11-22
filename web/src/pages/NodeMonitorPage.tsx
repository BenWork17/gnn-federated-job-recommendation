import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Play,
  Square,
  RotateCcw,
  ShieldCheck,
  Activity,
  Cpu,
  HardDriveUpload,
  Terminal,
  Download,
  Pin,
  Trash2,
  GitCompareArrows,
  Sparkles,
  Scale,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  AreaChart,
  Area,
  Legend,
  ScatterChart,
  Scatter,
  ZAxis,
  Cell,
} from 'recharts';
import {
  api,
  wsUrl,
  type ClientRow,
  type LatencyTickEvent,
  type TrainRoundEvent,
} from '../lib/api';
import { LiveFlTopology3D } from '../components/three';
import {
  GlassCard,
  PageHeader,
  SegmentedTabs,
  StatTile,
  StatusBadge,
} from '../components/ui/Primitives';

type StragglerPolicy = 'sync' | 'deadline65';
type CompressionMode = 'fp32' | 'fp16' | 'top20';

const COMPRESSION_META: Record<
  CompressionMode,
  { label: string; ratio: number; recallPenalty: number }
> = {
  fp32: { label: 'FP32 (100%)', ratio: 1.0, recallPenalty: 0.0 },
  fp16: { label: 'FP16 (50%)', ratio: 0.5, recallPenalty: 0.004 },
  top20: { label: 'Top-20% (20%)', ratio: 0.2, recallPenalty: 0.015 },
};

interface ExperimentPreset {
  id: string;
  label: string;
  hint: string;
  nClients: number;
  rounds: number;
  algorithm: 'fedavg' | 'fedprox';
  dropoutPct: 0 | 15 | 30;
  stragglerPolicy: StragglerPolicy;
  compression: CompressionMode;
}

const EXPERIMENT_PRESETS: ExperimentPreset[] = [
  {
    id: 'baseline',
    label: 'Preset 1 · Baseline FedAvg',
    hint: '100 clients · 8 vòng · 0% dropout · Sync · FP32',
    nClients: 100,
    rounds: 8,
    algorithm: 'fedavg',
    dropoutPct: 0,
    stragglerPolicy: 'sync',
    compression: 'fp32',
  },
  {
    id: 'stress',
    label: 'Preset 2 · Stress 30% Drop + Deadline',
    hint: '100 clients · 8 vòng · FedProx · 30% dropout · cắt 65ms',
    nClients: 100,
    rounds: 8,
    algorithm: 'fedprox',
    dropoutPct: 30,
    stragglerPolicy: 'deadline65',
    compression: 'fp32',
  },
  {
    id: 'compress',
    label: 'Preset 3 · Nén 80% băng thông (Top-20%)',
    hint: '100 clients · 8 vòng · FedProx · 15% dropout · Top-20% ΔW',
    nClients: 100,
    rounds: 8,
    algorithm: 'fedprox',
    dropoutPct: 15,
    stragglerPolicy: 'deadline65',
    compression: 'top20',
  },
];

type ClientTier = 'large' | 'medium' | 'small' | 'offline';

const SCATTER_TIER_COLOR: Record<ClientTier, string> = {
  large: '#0F172A',
  medium: '#FF5A1F',
  small: '#0EA5E9',
  offline: '#94A3B8',
};

const SCATTER_TIER_LABEL: Record<ClientTier, string> = {
  large: 'Top 10% Large',
  medium: 'Medium',
  small: 'Long-Tail Small',
  offline: 'Offline (Dropout)',
};

interface NodeCellState {
  clientId: number;
  name: string;
  nUsers: number;
  nJobs: number;
  nApps: number;
  weightSharePct: number;
  drift: number;
  latencyMs: number | null;
  bytesUp: number;
  bytesDown: number;
  lastRound: number;
  history: number[];
  pulsing: boolean;
  isStraggler?: boolean;
  isDropped?: boolean;
}

interface RoundPoint {
  round: number;
  recall20: number;
  ndcg20: number;
  loss: number;
  p50: number;
  p95: number;
  payloadMb: number;
  activeClients: number;
  meanDrift: number;
}

interface SavedRun {
  label: string;
  algorithm: 'fedavg' | 'fedprox';
  dropoutPct: number;
  stragglerPolicy: StragglerPolicy;
  compression: CompressionMode;
  points: RoundPoint[];
}

interface LogEntry {
  id: number;
  ts: string;
  kind: 'SYS' | 'ROUND' | 'TICK' | 'WS';
  text: string;
}

function percentile(values: number[], p: number): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(
    sorted.length - 1,
    Math.max(0, Math.ceil((p / 100) * sorted.length) - 1),
  );
  return Number(sorted[idx].toFixed(2));
}

function nowStamp(): string {
  return new Date().toTimeString().slice(0, 8);
}

/** Deterministic Non-IID client drift estimate based on data skew & FedProx regularization */
function computeClientDrift(
  nApps: number,
  meanApps: number,
  algorithm: 'fedavg' | 'fedprox',
  roundProgress = 0,
): number {
  const skew = Math.abs(Math.log1p(Math.max(1, nApps)) - Math.log1p(Math.max(1, meanApps)));
  const raw = Math.min(0.95, 0.16 + skew * 0.24);
  const proxDamp = algorithm === 'fedprox' ? 0.68 : 1.0;
  const decay = 1 - roundProgress * 0.25;
  return Number(Math.max(0.08, Math.min(0.95, raw * proxDamp * decay)).toFixed(3));
}

function hydrateWeightAndDrift(
  list: Omit<NodeCellState, 'weightSharePct' | 'drift'>[],
  algorithm: 'fedavg' | 'fedprox',
  roundProgress = 0,
): NodeCellState[] {
  const totalApps = Math.max(
    1,
    list.reduce((s, n) => s + Math.max(1, n.nApps), 0),
  );
  const meanApps = totalApps / Math.max(1, list.length);
  return list.map((n) => ({
    ...n,
    weightSharePct: Number(((Math.max(1, n.nApps) / totalApps) * 100).toFixed(2)),
    drift: computeClientDrift(n.nApps, meanApps, algorithm, roundProgress),
  }));
}

function makeFallbackNodes(count: number, algorithm: 'fedavg' | 'fedprox'): NodeCellState[] {
  const raw = Array.from({ length: count }, (_, idx) => {
    const cid = 1001 + idx;
    // Realistic Power-Law / Long-Tail CareerBuilder distribution
    const apps = Math.max(4, Math.round(1800 / Math.pow(idx + 1, 0.92) + ((idx * 17) % 13)));
    return {
      clientId: cid,
      name: `Employer #${cid}`,
      nUsers: Math.max(3, Math.round(apps * 0.64)),
      nJobs: Math.max(1, Math.round(apps * 0.22)),
      nApps: apps,
      latencyMs: null,
      bytesUp: 0,
      bytesDown: 0,
      lastRound: 0,
      history: [],
      pulsing: false,
      isStraggler: false,
      isDropped: false,
    };
  });
  return hydrateWeightAndDrift(raw, algorithm);
}

function cellColorClass(
  ms: number | null,
  selected: boolean,
  pulsing: boolean,
  dropped?: boolean,
): string {
  let base = 'bg-slate-200/80 border-slate-300/70';
  if (dropped) {
    base = 'bg-slate-100 border-dashed border-slate-400 opacity-50';
  } else if (ms !== null) {
    if (ms < 35) base = 'bg-emerald-500 border-emerald-600/40';
    else if (ms < 65) base = 'bg-amber-400 border-amber-500/40';
    else base = 'bg-rose-500 border-rose-600/40';
  }
  const ring = selected
    ? 'ring-2 ring-[#0F172A] ring-offset-1 scale-110 z-10'
    : pulsing
      ? 'ring-2 ring-[#FF5A1F]/70'
      : 'hover:scale-110 hover:ring-2 hover:ring-[#FF5A1F]/60';
  return `${base} ${ring}`;
}

export const NodeMonitorPage: React.FC = () => {
  const [mode, setMode] = useState<'checking' | 'live' | 'demo'>('checking');
  const [nClients, setNClients] = useState<number>(100);
  const [rounds, setRounds] = useState<number>(12);
  const [algorithm, setAlgorithm] = useState<'fedavg' | 'fedprox'>('fedavg');
  const [dropoutPct, setDropoutPct] = useState<0 | 15 | 30>(0);
  const [stragglerPolicy, setStragglerPolicy] = useState<StragglerPolicy>('sync');
  const [compression, setCompression] = useState<CompressionMode>('fp32');

  const [running, setRunning] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [currentRound, setCurrentRound] = useState(0);
  const [activeStep, setActiveStep] = useState(-1);
  const [nodeView, setNodeView] = useState<'3d' | 'grid'>('3d');
  const [cellFilter, setCellFilter] = useState<'all' | 'active' | 'slow'>('all');
  const [xAxisMode, setXAxisMode] = useState<'round' | 'mb'>('round');
  const [scatterY, setScatterY] = useState<'drift' | 'latency'>('drift');

  const [nodes, setNodes] = useState<NodeCellState[]>(() => makeFallbackNodes(100, 'fedavg'));
  const [selectedClientId, setSelectedClientId] = useState<number | null>(1001);
  const [roundPoints, setRoundPoints] = useState<RoundPoint[]>([]);
  const [baselineRun, setBaselineRun] = useState<SavedRun | null>(null);
  const [totalBytes, setTotalBytes] = useState(0);
  const [logs, setLogs] = useState<LogEntry[]>([
    { id: 1, ts: nowStamp(), kind: 'SYS', text: 'Khởi tạo FL Research Console — kiểm tra /health...' },
  ]);

  const apiClientsRef = useRef<ClientRow[]>([]);
  const wsTrainRef = useRef<WebSocket | null>(null);
  const wsLatencyRef = useRef<WebSocket | null>(null);
  const demoTimerRef = useRef<number | null>(null);
  const stepTimerRef = useRef<number | null>(null);
  const logIdRef = useRef(2);
  const roundLatenciesRef = useRef<number[]>([]);
  const cumulativeBytesRef = useRef<number>(0);

  // Live experiment refs for WS/demo handlers
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;
  const expCfgRef = useRef({ algorithm, dropoutPct, stragglerPolicy, compression, rounds });
  expCfgRef.current = { algorithm, dropoutPct, stragglerPolicy, compression, rounds };

  const currentRunLabel = `${algorithm.toUpperCase()} · drop ${dropoutPct}% · ${
    stragglerPolicy === 'deadline65' ? 'Deadline 65ms' : 'Sync'
  } · ${compression.toUpperCase()}`;

  const hasSimulatedFaults =
    dropoutPct > 0 ||
    stragglerPolicy !== 'sync' ||
    compression !== 'fp32' ||
    nodes.some((n) => n.isStraggler || n.isDropped);

  const appendLog = useCallback((kind: LogEntry['kind'], text: string) => {
    const id = logIdRef.current++;
    setLogs((prev) => [{ id, ts: nowStamp(), kind, text }, ...prev].slice(0, 60));
  }, []);

  const closeSocketsAndTimers = useCallback(() => {
    if (wsTrainRef.current) {
      wsTrainRef.current.close();
      wsTrainRef.current = null;
    }
    if (wsLatencyRef.current) {
      wsLatencyRef.current.close();
      wsLatencyRef.current = null;
    }
    if (demoTimerRef.current !== null) {
      window.clearInterval(demoTimerRef.current);
      demoTimerRef.current = null;
    }
    if (stepTimerRef.current !== null) {
      window.clearInterval(stepTimerRef.current);
      stepTimerRef.current = null;
    }
  }, []);

  useEffect(() => () => closeSocketsAndTimers(), [closeSocketsAndTimers]);

  // Initial /health + /api/clients probe
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const h = await api.health();
        if (!alive) return;
        if (h.status === 'ok') {
          setMode('live');
          appendLog(
            'SYS',
            `Kết nối FastAPI live (db=${h.db ? 'ok' : 'dry-run'}, artifacts=${h.artifacts ? 'ready' : 'demo'}).`,
          );
          try {
            const cl = await api.clients(220, 0);
            if (!alive) return;
            apiClientsRef.current = cl.items;
            const raw = cl.items.slice(0, nClients).map((c) => ({
              clientId: c.client_id,
              name: c.name || `Employer #${c.client_id}`,
              nUsers: c.n_users,
              nJobs: c.n_jobs,
              nApps: c.n_apps,
              latencyMs: null,
              bytesUp: 0,
              bytesDown: 0,
              lastRound: 0,
              history: [],
              pulsing: false,
              isStraggler: false,
              isDropped: false,
            }));
            if (raw.length) {
              const hydrated = hydrateWeightAndDrift(raw, 'fedavg');
              setNodes(hydrated);
              setSelectedClientId(hydrated[0].clientId);
            }
          } catch {
            // keep fallback
          }
          return;
        }
      } catch {
        // fallback to demo
      }
      if (!alive) return;
      setMode('demo');
      appendLog(
        'SYS',
        'API nền chưa bật — tự động chuyển sang Demo Simulator (mô phỏng Non-IID + Dropout + Straggler).',
      );
    })();
    return () => {
      alive = false;
    };
  }, [appendLog]);

  // Update drift estimates smoothly when switching algorithm while idle
  useEffect(() => {
    if (running) return;
    setNodes((prev) => hydrateWeightAndDrift(prev, algorithm, currentRound / Math.max(1, rounds)));
  }, [algorithm]);

  // Resize grid ONLY when nClients changes while idle (preserve final round colors when training finishes)
  const prevNClientsRef = useRef(nClients);
  useEffect(() => {
    if (running) return;
    if (prevNClientsRef.current === nClients) return;
    prevNClientsRef.current = nClients;
    if (apiClientsRef.current.length > 0) {
      const slice = apiClientsRef.current.slice(0, nClients).map((c) => ({
        clientId: c.client_id,
        name: c.name || `Employer #${c.client_id}`,
        nUsers: c.n_users,
        nJobs: c.n_jobs,
        nApps: c.n_apps,
        latencyMs: null,
        bytesUp: 0,
        bytesDown: 0,
        lastRound: 0,
        history: [],
        pulsing: false,
        isStraggler: false,
        isDropped: false,
      }));
      const hydrated = hydrateWeightAndDrift(
        slice.length < nClients
          ? [...slice, ...makeFallbackNodes(nClients - slice.length, algorithm)]
          : slice,
        algorithm,
      );
      setNodes(hydrated);
      setSelectedClientId(hydrated[0]?.clientId ?? null);
    } else {
      const next = makeFallbackNodes(nClients, algorithm);
      setNodes(next);
      setSelectedClientId(next[0]?.clientId ?? null);
    }
  }, [nClients, running, algorithm]);

  // Freeze the exact config of the active/last-completed run so Baseline A keeps Run A's real metadata
  const lastRunMetaRef = useRef<Omit<SavedRun, 'points'> | null>(null);

  // Helper: auto-pin previous completed run as Baseline Run A using its frozen metadata
  const autoSaveBaselineIfUseful = useCallback(() => {
    if (roundPoints.length >= 2 && lastRunMetaRef.current) {
      const meta = lastRunMetaRef.current;
      setBaselineRun((prev) =>
        prev
          ? prev
          : {
              ...meta,
              points: roundPoints,
            },
      );
    }
  }, [roundPoints]);

  const handlePinBaseline = () => {
    if (roundPoints.length === 0) return;
    const meta = lastRunMetaRef.current ?? {
      label: currentRunLabel,
      algorithm,
      dropoutPct,
      stragglerPolicy,
      compression,
    };
    setBaselineRun({
      ...meta,
      points: [...roundPoints],
    });
    appendLog('SYS', `Đã ghim Baseline Run A: ${meta.label} (${roundPoints.length} vòng).`);
  };

  const handleExportCsv = () => {
    if (roundPoints.length === 0) return;
    const header =
      'run_label,algorithm,dropout_pct,straggler_policy,compression,round,recall_at_20,ndcg_at_20,loss,p50_ms,p95_ms,payload_mb,active_clients,mean_drift';
    const rows = roundPoints.map((pt) =>
      [
        `"${currentRunLabel}"`,
        algorithm,
        dropoutPct,
        stragglerPolicy,
        compression,
        pt.round,
        pt.recall20,
        pt.ndcg20,
        pt.loss,
        pt.p50,
        pt.p95,
        pt.payloadMb,
        pt.activeClients,
        pt.meanDrift,
      ].join(','),
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fedgraph_fl_${algorithm}_drop${dropoutPct}_${compression}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    appendLog('SYS', `Đã xuất CSV (${roundPoints.length} vòng) phục vụ báo cáo thực nghiệm.`);
  };

  const applyResearchEffects = (
    rawRecall: number,
    rawNdcg: number,
    rawLoss: number,
    rawP50: number,
    rawP95: number,
    roundIdx: number,
  ) => {
    const cfg = expCfgRef.current;
    const liveNodes = nodesRef.current;
    const comp = COMPRESSION_META[cfg.compression];
    const manualDropped = liveNodes.filter((n) => n.isDropped).length;
    const manualStragglers = liveNodes.filter((n) => n.isStraggler && !n.isDropped).length;

    const effectiveDropFrac = Math.min(
      0.6,
      cfg.dropoutPct / 100 + manualDropped / Math.max(1, liveNodes.length),
    );
    const activeClients = Math.max(1, Math.round(liveNodes.length * (1 - effectiveDropFrac)));

    // FedProx resists Non-IID + partial participation better than FedAvg
    const dropPenalty =
      effectiveDropFrac * (cfg.algorithm === 'fedprox' ? 0.045 : 0.095) * (1 - (roundIdx / (cfg.rounds * 2)));
    const deadlinePenalty = cfg.stragglerPolicy === 'deadline65' ? 0.008 : 0;

    const recall20 = Number(
      Math.max(0.05, Math.min(0.95, rawRecall - dropPenalty - comp.recallPenalty - deadlinePenalty)).toFixed(4),
    );
    const ndcg20 = Number(Math.max(0.04, recall20 * (rawRecall > 0 ? rawNdcg / rawRecall : 0.78)).toFixed(4));
    const loss = Number(Math.max(0.08, rawLoss + dropPenalty * 0.9 + comp.recallPenalty * 0.6).toFixed(4));

    const stragglerBoost = manualStragglers > 0 ? 115 : 0;
    const p50 = Number(rawP50.toFixed(2));
    const rawTail = rawP95 + stragglerBoost;
    const p95 =
      cfg.stragglerPolicy === 'deadline65'
        ? Number(Math.min(65, rawTail).toFixed(2))
        : Number(rawTail.toFixed(2));

    const meanDrift = Number(
      (
        liveNodes.reduce((s, n) => s + (n.isDropped ? 0 : n.drift), 0) /
        Math.max(1, liveNodes.filter((n) => !n.isDropped).length)
      ).toFixed(3),
    );

    return { recall20, ndcg20, loss, p50, p95, activeClients, meanDrift };
  };

  const startDemoRun = useCallback(() => {
    closeSocketsAndTimers();
    autoSaveBaselineIfUseful();
    lastRunMetaRef.current = {
      label: currentRunLabel,
      algorithm,
      dropoutPct,
      stragglerPolicy,
      compression,
    };

    // Preserve user's manual straggler/dropout flags while clearing round latencies
    const curNodes = nodesRef.current;
    const baseNodes = curNodes.length === nClients ? curNodes : makeFallbackNodes(nClients, algorithm);
    const resetNodes = baseNodes.map((n, idx) => ({
      ...n,
      latencyMs: null,
      bytesUp: 0,
      bytesDown: 0,
      lastRound: 0,
      history: [],
      pulsing: false,
      isDropped: n.isDropped || (dropoutPct > 0 && (idx * 17) % 100 < dropoutPct),
    }));

    setNodes(resetNodes);
    setSelectedClientId(resetNodes[0]?.clientId ?? null);
    setRoundPoints([]);
    setTotalBytes(0);
    cumulativeBytesRef.current = 0;
    setCurrentRound(0);
    setActiveStep(0);
    setRunning(true);

    const fakeId = `demo-${Date.now().toString(36).slice(-5)}`;
    setRunId(fakeId);
    appendLog('SYS', `[Demo Simulator] Khởi chạy ${currentRunLabel} (${nClients} nodes, ${rounds} vòng).`);

    let r = 0;
    let stepTick = 0;
    stepTimerRef.current = window.setInterval(() => {
      stepTick = (stepTick + 1) % 5;
      setActiveStep(stepTick);
    }, 170);

    const runOneRound = () => {
      r += 1;
      const cfg = expCfgRef.current;
      const comp = COMPRESSION_META[cfg.compression];
      const progress = r / cfg.rounds;
      const baseRec = cfg.algorithm === 'fedprox' ? 0.325 : 0.305;
      const gain = 1 - Math.exp(-3.1 * progress);
      const rawRecall = Math.min(0.92, (baseRec + (0.625 - baseRec) * gain) * (0.985 + Math.random() * 0.03));
      const rawNdcg = rawRecall * 0.78;
      const rawLoss = 1.82 * Math.exp(-2.55 * progress) + 0.24 + (Math.random() - 0.5) * 0.02;

      const latencies: number[] = [];
      let roundBytes = 0;

      setNodes((prev) => {
        const updated = prev.map((node, i) => {
          if (node.isDropped) {
            return { ...node, latencyMs: null, pulsing: false };
          }
          const heavy = node.isStraggler ? 122 : i % 13 === 0 ? 48 : i % 5 === 0 ? 18 : 0;
          const ms = Number(
            (14 + heavy + Math.random() * 28 + (cfg.algorithm === 'fedprox' ? 3 : 0)).toFixed(1),
          );
          const up = Math.round((46000 + Math.random() * 14000) * comp.ratio);
          const down = Math.round(92000 * (cfg.compression === 'fp16' ? 0.5 : 1));
          if (cfg.stragglerPolicy === 'deadline65' && ms > 65) {
            latencies.push(65);
          } else {
            latencies.push(ms);
            roundBytes += up + down;
          }
          return {
            ...node,
            latencyMs: ms,
            bytesUp: node.bytesUp + up,
            bytesDown: node.bytesDown + down,
            lastRound: r,
            history: [...node.history.slice(-11), ms],
            pulsing: i % 4 === r % 4,
          };
        });
        return hydrateWeightAndDrift(updated, cfg.algorithm, progress);
      });

      const rawP50 = percentile(latencies, 50);
      const rawP95 = percentile(latencies, 95);
      const adj = applyResearchEffects(rawRecall, rawNdcg, rawLoss, rawP50, rawP95, r);

      const deterministicRoundBytes = Math.round(adj.activeClients * 92 * 1024 * 2 * comp.ratio);
      cumulativeBytesRef.current += Math.max(roundBytes, deterministicRoundBytes);
      const payloadMb = Number((cumulativeBytesRef.current / (1024 * 1024)).toFixed(2));
      setCurrentRound(r);
      setTotalBytes(cumulativeBytesRef.current);
      setRoundPoints((prev) => [
        ...prev,
        {
          round: r,
          recall20: adj.recall20,
          ndcg20: adj.ndcg20,
          loss: adj.loss,
          p50: adj.p50,
          p95: adj.p95,
          payloadMb,
          activeClients: adj.activeClients,
          meanDrift: adj.meanDrift,
        },
      ]);
      appendLog(
        'ROUND',
        `Vòng ${r}/${cfg.rounds} · Recall@20=${adj.recall20.toFixed(3)} · p95=${adj.p95}ms · ${payloadMb} MB`,
      );

      if (r >= cfg.rounds) {
        closeSocketsAndTimers();
        setRunning(false);
        setActiveStep(4);
        appendLog('SYS', `Hoàn tất phiên ${fakeId} (${cfg.rounds} vòng · 0 B raw data).`);
      }
    };

    runOneRound();
    demoTimerRef.current = window.setInterval(runOneRound, 800);
  }, [algorithm, appendLog, autoSaveBaselineIfUseful, closeSocketsAndTimers, currentRunLabel, dropoutPct, nClients, rounds]);

  const handleStart = async () => {
    if (mode !== 'live') {
      startDemoRun();
      return;
    }

    closeSocketsAndTimers();
    autoSaveBaselineIfUseful();
    lastRunMetaRef.current = {
      label: currentRunLabel,
      algorithm,
      dropoutPct,
      stragglerPolicy,
      compression,
    };
    setRoundPoints([]);
    setTotalBytes(0);
    cumulativeBytesRef.current = 0;
    setCurrentRound(0);
    setActiveStep(0);
    roundLatenciesRef.current = [];

    // Remember manual straggler / dropout sets
    const manualStragglerIds = new Set(nodes.filter((n) => n.isStraggler).map((n) => n.clientId));
    const manualDroppedIds = new Set(nodes.filter((n) => n.isDropped).map((n) => n.clientId));

    try {
      const res = await api.trainStart({
        n_clients: nClients,
        rounds,
        algorithm,
        local_epochs: 1,
      });

      setRunId(res.run_id);
      setRunning(true);
      appendLog(
        'SYS',
        `Khởi chạy live ${currentRunLabel} · ${res.n_clients} clients · ${res.rounds} vòng (${res.run_id.slice(0, 8)}).`,
      );

      const byId = new Map(apiClientsRef.current.map((c) => [c.client_id, c]));
      const rawParticipants = (
        res.participants.length ? res.participants : Array.from({ length: nClients }, (_, i) => i)
      ).map((cid, idx) => {
        const info = byId.get(cid);
        const droppedByRate = dropoutPct > 0 && (idx * 17) % 100 < dropoutPct;
        return {
          clientId: cid,
          name: info?.name || `Employer #${cid}`,
          nUsers: info?.n_users ?? 12,
          nJobs: info?.n_jobs ?? 5,
          nApps: info?.n_apps ?? 24,
          latencyMs: null,
          bytesUp: 0,
          bytesDown: 0,
          lastRound: 0,
          history: [],
          pulsing: false,
          isStraggler: manualStragglerIds.has(cid),
          isDropped: manualDroppedIds.has(cid) || droppedByRate,
        };
      });
      const hydrated = hydrateWeightAndDrift(rawParticipants, algorithm);
      setNodes(hydrated);
      setSelectedClientId(hydrated[0]?.clientId ?? null);

      let stepTick = 0;
      stepTimerRef.current = window.setInterval(() => {
        stepTick = (stepTick + 1) % 5;
        setActiveStep(stepTick);
      }, 180);

      // Connect /ws/latency
      const latWs = new WebSocket(wsUrl('/ws/latency'));
      wsLatencyRef.current = latWs;
      latWs.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as LatencyTickEvent;
          if (msg.type !== 'tick' || msg.run_id !== res.run_id) return;
          const cfg = expCfgRef.current;
          const comp = COMPRESSION_META[cfg.compression];

          setNodes((prev) =>
            prev.map((n) => {
              if (n.clientId !== msg.client_id) {
                return n.pulsing && n.lastRound < msg.round ? { ...n, pulsing: false } : n;
              }
              if (n.isDropped) return n;
              const adjMs = Number((msg.latency_ms + (n.isStraggler ? 120 : 0)).toFixed(2));
              const up = Math.round(msg.bytes_up * comp.ratio);
              const down = Math.round(msg.bytes_down * comp.ratio);
              roundLatenciesRef.current.push(
                cfg.stragglerPolicy === 'deadline65' ? Math.min(65, adjMs) : adjMs,
              );
              return {
                ...n,
                latencyMs: adjMs,
                bytesUp: n.bytesUp + up,
                bytesDown: n.bytesDown + down,
                lastRound: msg.round,
                history: [...n.history.slice(-11), adjMs],
                pulsing: true,
              };
            }),
          );
        } catch {
          // ignore
        }
      };

      // Connect /ws/train/{run_id}
      const trainWs = new WebSocket(wsUrl(`/ws/train/${encodeURIComponent(res.run_id)}`));
      wsTrainRef.current = trainWs;
      trainWs.onopen = () =>
        appendLog('WS', `Kết nối /ws/train/${res.run_id.slice(0, 8)} & /ws/latency.`);
      trainWs.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as TrainRoundEvent;
          if (msg.type !== 'round') return;
          if (msg.status === 'done' || msg.status === 'stopped') {
            closeSocketsAndTimers();
            setRunning(false);
            setActiveStep(4);
            appendLog(
              'SYS',
              msg.status === 'stopped'
                ? `Đã dừng tại vòng ${msg.stopped_at_round ?? msg.round}.`
                : `Hoàn tất ${msg.round} vòng FL (${currentRunLabel}).`,
            );
            return;
          }
          const lats = roundLatenciesRef.current;
          const rawP50 = lats.length ? percentile(lats, 50) : Number(msg.latency_ms.toFixed(2));
          const rawP95 = lats.length ? percentile(lats, 95) : Number((msg.latency_ms * 1.45).toFixed(2));
          roundLatenciesRef.current = [];

          const adj = applyResearchEffects(
            msg.metrics?.recall20 ?? 0,
            msg.metrics?.ndcg20 ?? 0,
            msg.metrics?.loss ?? 0,
            rawP50,
            rawP95,
            msg.round,
          );
          const compRatio = COMPRESSION_META[expCfgRef.current.compression].ratio;
          const roundBytes = Math.round(adj.activeClients * 92 * 1024 * 2 * compRatio);
          cumulativeBytesRef.current += roundBytes;
          setTotalBytes(cumulativeBytesRef.current);
          const payloadMb = Number((cumulativeBytesRef.current / (1024 * 1024)).toFixed(2));
          setCurrentRound(msg.round);
          setRoundPoints((prev) => {
            if (prev.some((pt) => pt.round === msg.round)) return prev;
            return [
              ...prev,
              {
                round: msg.round,
                recall20: adj.recall20,
                ndcg20: adj.ndcg20,
                loss: adj.loss,
                p50: adj.p50,
                p95: adj.p95,
                payloadMb,
                activeClients: adj.activeClients,
                meanDrift: adj.meanDrift,
              },
            ];
          });
          appendLog(
            'ROUND',
            `Vòng ${msg.round}/${res.rounds} · Recall@20=${adj.recall20.toFixed(3)} · p95=${adj.p95}ms · ${payloadMb} MB`,
          );
        } catch {
          // ignore
        }
      };
      trainWs.onerror = () => {
        appendLog('WS', 'WebSocket gián đoạn — chuyển sang Demo Simulator.');
        setMode('demo');
        startDemoRun();
      };
    } catch {
      appendLog('SYS', 'Không gọi được /api/train/start — chuyển sang Demo Simulator.');
      setMode('demo');
      startDemoRun();
    }
  };

  const handleStop = async () => {
    if (mode === 'live' && runId && !runId.startsWith('demo-')) {
      try {
        await api.trainStop(runId);
      } catch {
        // ignore
      }
    }
    closeSocketsAndTimers();
    setRunning(false);
    appendLog('SYS', 'Đã dừng phiên thực nghiệm.');
  };

  const handleReset = () => {
    closeSocketsAndTimers();
    setRunning(false);
    setRunId(null);
    setCurrentRound(0);
    setActiveStep(-1);
    setRoundPoints([]);
    setTotalBytes(0);
    cumulativeBytesRef.current = 0;
    setNodes((prev) =>
      hydrateWeightAndDrift(
        prev.map((n) => ({
          ...n,
          latencyMs: null,
          bytesUp: 0,
          bytesDown: 0,
          lastRound: 0,
          history: [],
          pulsing: false,
          isStraggler: false,
          isDropped: false,
        })),
        algorithm,
      ),
    );
    appendLog('SYS', 'Đã đặt lại bảng điều khiển về trạng thái chờ.');
  };

  const handleToggleStraggler = useCallback(
    (clientId: number) => {
      setNodes((prev) =>
        prev.map((n) => {
          if (n.clientId !== clientId || n.isDropped) return n;
          const nextSlow = !n.isStraggler;
          const base = n.latencyMs ?? 18;
          const nextMs = nextSlow
            ? Number(Math.max(128, base + 120).toFixed(1))
            : Number(Math.max(9.5, base - 120).toFixed(1));
          return {
            ...n,
            isStraggler: nextSlow,
            latencyMs: nextMs,
            history: [...n.history.slice(-11), nextMs],
          };
        }),
      );
      const target = nodesRef.current.find((n) => n.clientId === clientId);
      if (target) {
        appendLog(
          'TICK',
          !target.isStraggler
            ? `Tiêm trễ straggler +120ms lên ${target.name} (#${clientId}) — sẽ tác động lên p95.`
            : `Khôi phục tốc độ cho ${target.name} (#${clientId}).`,
        );
      }
    },
    [appendLog],
  );

  const handleToggleDropout = useCallback(
    (clientId: number) => {
      setNodes((prev) =>
        prev.map((n) => {
          if (n.clientId !== clientId) return n;
          const nextDropped = !n.isDropped;
          return {
            ...n,
            isDropped: nextDropped,
            isStraggler: nextDropped ? false : n.isStraggler,
          };
        }),
      );
      const target = nodesRef.current.find((n) => n.clientId === clientId);
      if (target) {
        appendLog(
          'SYS',
          !target.isDropped
            ? `Dropout: ngắt ${target.name} (#${clientId}) khỏi vòng tổng hợp FL.`
            : `Kết nối lại ${target.name} (#${clientId}) vào mạng FL.`,
        );
      }
    },
    [appendLog],
  );

  const latestRound = roundPoints[roundPoints.length - 1];
  const latestBaseline = baselineRun?.points[baselineRun.points.length - 1];
  const reportedCount = useMemo(
    () => nodes.filter((n) => n.latencyMs !== null && !n.isDropped).length,
    [nodes],
  );
  const activeCount = useMemo(() => nodes.filter((n) => !n.isDropped).length, [nodes]);
  const meanDrift = useMemo(() => {
    const active = nodes.filter((n) => !n.isDropped);
    if (!active.length) return 0;
    return active.reduce((s, n) => s + n.drift, 0) / active.length;
  }, [nodes]);

  const visibleNodes = useMemo(() => {
    if (cellFilter === 'active') return nodes.filter((n) => n.latencyMs !== null && !n.isDropped);
    if (cellFilter === 'slow') return nodes.filter((n) => (n.latencyMs ?? 0) >= 65 && !n.isDropped);
    return nodes;
  }, [cellFilter, nodes]);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.clientId === selectedClientId) ?? nodes[0] ?? null,
    [nodes, selectedClientId],
  );

  // Merge Current Run B + Baseline Run A for side-by-side overlaid charts
  const chartSeries = useMemo(() => {
    const maxLen = Math.max(roundPoints.length, baselineRun?.points.length ?? 0);
    const out: Array<{
      round: number;
      xVal: number;
      recall20?: number;
      ndcg20?: number;
      p50?: number;
      p95?: number;
      baseRecall20?: number;
      baseP95?: number;
      payloadMb?: number;
    }> = [];
    for (let i = 0; i < maxLen; i++) {
      const cur = roundPoints[i];
      const base = baselineRun?.points[i];
      const r = cur?.round ?? base?.round ?? i + 1;
      out.push({
        round: r,
        xVal: xAxisMode === 'mb' ? (cur?.payloadMb ?? base?.payloadMb ?? 0) : r,
        recall20: cur?.recall20,
        ndcg20: cur?.ndcg20,
        p50: cur?.p50,
        p95: cur?.p95,
        payloadMb: cur?.payloadMb,
        baseRecall20: base?.recall20,
        baseP95: base?.p95,
      });
    }
    return out;
  }, [roundPoints, baselineRun, xAxisMode]);

  const applyPreset = (preset: ExperimentPreset) => {
    if (running) return;
    setNClients(preset.nClients);
    setRounds(preset.rounds);
    setAlgorithm(preset.algorithm);
    setDropoutPct(preset.dropoutPct);
    setStragglerPolicy(preset.stragglerPolicy);
    setCompression(preset.compression);
    appendLog('SYS', `Áp dụng kịch bản nhanh: ${preset.label} (${preset.hint}).`);
  };

  // Non-IID Fairness & Drift Scatter data (coordinated brushing with 3D Topology & Node Inspector)
  const { scatterData, fairnessStats } = useMemo(() => {
    const sortedApps = [...nodes].map((n) => n.nApps).sort((a, b) => a - b);
    const p90 = sortedApps[Math.floor(sortedApps.length * 0.9)] ?? 100;
    const p50 = sortedApps[Math.floor(sortedApps.length * 0.5)] ?? 20;

    const pts = nodes.map((n) => {
      const tier: ClientTier = n.isDropped
        ? 'offline'
        : n.nApps >= p90
          ? 'large'
          : n.nApps >= p50
            ? 'medium'
            : 'small';
      return {
        clientId: n.clientId,
        name: n.name,
        nApps: n.nApps,
        logApps: Number(Math.log10(Math.max(1, n.nApps)).toFixed(2)),
        yVal: scatterY === 'drift' ? n.drift : (n.latencyMs ?? 0),
        drift: n.drift,
        latencyMs: n.latencyMs,
        weightSharePct: n.weightSharePct,
        tier,
        zSize: Math.max(36, Math.min(180, Math.round(n.weightSharePct * 42 + 44))),
      };
    });

    const largeActive = pts.filter((p) => p.tier === 'large');
    const smallActive = pts.filter((p) => p.tier === 'small');
    const avgLargeDrift = largeActive.length
      ? largeActive.reduce((s, p) => s + p.drift, 0) / largeActive.length
      : 0;
    const avgSmallDrift = smallActive.length
      ? smallActive.reduce((s, p) => s + p.drift, 0) / smallActive.length
      : 0;

    return {
      scatterData: pts,
      fairnessStats: {
        avgLargeDrift: Number(avgLargeDrift.toFixed(3)),
        avgSmallDrift: Number(avgSmallDrift.toFixed(3)),
        gap: Number(Math.abs(avgSmallDrift - avgLargeDrift).toFixed(3)),
      },
    };
  }, [nodes, scatterY]);

  const formattedBytes =
    totalBytes >= 1024 * 1024
      ? `${(totalBytes / (1024 * 1024)).toFixed(2)} MB`
      : `${(totalBytes / 1024).toFixed(0)} KB`;

  const provenanceLabel =
    mode === 'live'
      ? hasSimulatedFaults
        ? 'Live FastAPI + Mô phỏng lỗi'
        : 'Artifacts thật · perf_counter'
      : 'Demo Simulator';

  return (
    <div className="space-y-4">
      <PageHeader
        kicker="04 // FEDERATED LEARNING RESEARCH WORKBENCH"
        title="Giám sát & Thực nghiệm Node FL"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge
              tone={mode === 'live' ? (hasSimulatedFaults ? 'warn' : 'green') : 'orange'}
              pulse={mode === 'live' || running}
            >
              {provenanceLabel}
            </StatusBadge>
            <button
              type="button"
              disabled={roundPoints.length === 0}
              onClick={handleExportCsv}
              className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-45 disabled:cursor-not-allowed"
              title="Tải lịch sử thực nghiệm dạng CSV để đưa vào báo cáo"
            >
              <Download size={13} />
              <span>Xuất CSV</span>
            </button>
          </div>
        }
      />

      {/* Compact Research Experiment Control Bar */}
      <GlassCard padding="sm" className="space-y-2.5">
        {/* 1-Click Experiment Presets Strip */}
        <div className="flex flex-wrap items-center gap-1.5 pb-2 border-b border-slate-200/75">
          <span className="inline-flex items-center gap-1 font-mono-tech text-[10px] font-bold uppercase tracking-wider text-[#C2410C] mr-1">
            <Sparkles size={11} />
            Kịch bản mẫu:
          </span>
          {EXPERIMENT_PRESETS.map((preset) => {
            const isMatched =
              nClients === preset.nClients &&
              rounds === preset.rounds &&
              algorithm === preset.algorithm &&
              dropoutPct === preset.dropoutPct &&
              stragglerPolicy === preset.stragglerPolicy &&
              compression === preset.compression;
            return (
              <button
                key={preset.id}
                type="button"
                disabled={running}
                onClick={() => applyPreset(preset)}
                title={preset.hint}
                className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-all cursor-pointer disabled:opacity-45 disabled:cursor-not-allowed ${
                  isMatched
                    ? 'border-[#FF5A1F] bg-[#FFF7ED] text-[#C2410C] shadow-2xs'
                    : 'border-slate-200 bg-white/85 text-slate-600 hover:border-orange-300 hover:text-[#0F172A]'
                }`}
              >
                {preset.label}
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <label className="flex items-center gap-1.5 text-xs font-semibold text-[#475569]">
              <span className="font-mono-tech uppercase text-[0.68rem]">Clients</span>
              <select
                value={nClients}
                disabled={running}
                onChange={(e) => setNClients(Number(e.target.value))}
                className="input-control py-1 text-xs font-mono-tech font-semibold"
              >
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={220}>220</option>
              </select>
            </label>

            <label className="flex items-center gap-1.5 text-xs font-semibold text-[#475569]">
              <span className="font-mono-tech uppercase text-[0.68rem]">Rounds</span>
              <select
                value={rounds}
                disabled={running}
                onChange={(e) => setRounds(Number(e.target.value))}
                className="input-control py-1 text-xs font-mono-tech font-semibold"
              >
                <option value={8}>8</option>
                <option value={12}>12</option>
                <option value={20}>20</option>
              </select>
            </label>

            <SegmentedTabs
              layoutId="monitor-algo-tab"
              size="sm"
              value={algorithm}
              onChange={(v) => !running && setAlgorithm(v)}
              options={[
                { id: 'fedavg', label: 'FedAvg' },
                { id: 'fedprox', label: 'FedProx (μ)' },
              ]}
            />

            <label className="flex items-center gap-1.5 text-xs font-semibold text-[#475569]">
              <span className="font-mono-tech uppercase text-[0.68rem]">Dropout</span>
              <select
                value={dropoutPct}
                disabled={running}
                onChange={(e) => setDropoutPct(Number(e.target.value) as 0 | 15 | 30)}
                className="input-control py-1 text-xs font-mono-tech font-semibold"
              >
                <option value={0}>0%</option>
                <option value={15}>15%</option>
                <option value={30}>30%</option>
              </select>
            </label>

            <label className="flex items-center gap-1.5 text-xs font-semibold text-[#475569]">
              <span className="font-mono-tech uppercase text-[0.68rem]">Straggler</span>
              <select
                value={stragglerPolicy}
                disabled={running}
                onChange={(e) => setStragglerPolicy(e.target.value as StragglerPolicy)}
                className="input-control py-1 text-xs font-mono-tech font-semibold"
              >
                <option value="sync">Chờ hết (Sync)</option>
                <option value="deadline65">Cắt 65ms (Deadline)</option>
              </select>
            </label>

            <label className="flex items-center gap-1.5 text-xs font-semibold text-[#475569]">
              <span className="font-mono-tech uppercase text-[0.68rem]">Nén ΔW</span>
              <select
                value={compression}
                disabled={running}
                onChange={(e) => setCompression(e.target.value as CompressionMode)}
                className="input-control py-1 text-xs font-mono-tech font-semibold"
              >
                <option value="fp32">FP32 (100%)</option>
                <option value="fp16">FP16 (50%)</option>
                <option value="top20">Top-20% (20%)</option>
              </select>
            </label>
          </div>

          <div className="flex items-center gap-1.5">
            {!running ? (
              <button type="button" onClick={handleStart} className="btn-primary py-1.5 px-3.5 text-xs">
                <Play size={13} fill="currentColor" />
                <span>Bắt đầu chạy</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleStop}
                className="inline-flex items-center gap-1.5 rounded-[8px] border border-rose-300 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 cursor-pointer"
              >
                <Square size={13} fill="currentColor" />
                <span>Dừng</span>
              </button>
            )}

            <button
              type="button"
              disabled={running || roundPoints.length === 0}
              onClick={handlePinBaseline}
              className="btn-secondary py-1.5 px-2.5 text-xs disabled:opacity-45 disabled:cursor-not-allowed"
              title="Ghim lần chạy hiện tại làm Baseline Run A để so sánh A/B với lần chạy tiếp theo"
            >
              <Pin size={13} />
              <span className="hidden md:inline">Ghim Baseline</span>
            </button>

            <button
              type="button"
              onClick={handleReset}
              disabled={running}
              className="btn-secondary py-1.5 px-2.5 text-xs disabled:opacity-45"
              title="Đặt lại phiên chạy"
            >
              <RotateCcw size={13} />
            </button>
          </div>
        </div>

        {/* Active A/B Comparison Strip (visible whenever a Baseline Run A is pinned) */}
        {baselineRun && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-orange-200/80 bg-[#FFF7ED]/80 px-3 py-1.5 text-xs">
            <div className="flex flex-wrap items-center gap-2 text-[#0F172A]">
              <GitCompareArrows size={14} className="text-[#FF5A1F] shrink-0" />
              <span className="font-mono-tech text-[11px] font-bold text-[#C2410C]">
                SO SÁNH A/B:
              </span>
              <span className="font-mono-tech text-[11px] text-slate-600">
                A (nét đứt) = {baselineRun.label}
              </span>
              {latestRound && latestBaseline && (
                <span className="inline-flex flex-wrap items-center gap-2 font-mono-tech text-[11px] font-semibold">
                  <span className="rounded bg-white/90 px-1.5 py-0.5 text-slate-900 border border-slate-200">
                    ΔRecall@20:{' '}
                    <span
                      className={
                        latestRound.recall20 - latestBaseline.recall20 >= 0
                          ? 'text-emerald-700'
                          : 'text-rose-700'
                      }
                    >
                      {latestRound.recall20 - latestBaseline.recall20 >= 0 ? '+' : ''}
                      {(latestRound.recall20 - latestBaseline.recall20).toFixed(3)}
                    </span>
                  </span>
                  <span className="rounded bg-white/90 px-1.5 py-0.5 text-slate-900 border border-slate-200">
                    Δp95:{' '}
                    <span
                      className={
                        latestRound.p95 - latestBaseline.p95 <= 0
                          ? 'text-emerald-700'
                          : 'text-rose-700'
                      }
                    >
                      {latestRound.p95 - latestBaseline.p95 >= 0 ? '+' : ''}
                      {(latestRound.p95 - latestBaseline.p95).toFixed(1)} ms
                    </span>
                  </span>
                  <span className="rounded bg-white/90 px-1.5 py-0.5 text-slate-900 border border-slate-200">
                    ΔPayload:{' '}
                    <span
                      className={
                        latestRound.payloadMb - latestBaseline.payloadMb <= 0
                          ? 'text-emerald-700'
                          : 'text-rose-700'
                      }
                    >
                      {latestRound.payloadMb - latestBaseline.payloadMb >= 0 ? '+' : ''}
                      {(latestRound.payloadMb - latestBaseline.payloadMb).toFixed(2)} MB
                    </span>
                  </span>
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => setBaselineRun(null)}
              className="inline-flex cursor-pointer items-center gap-1 text-[11px] font-semibold text-slate-500 hover:text-rose-700"
            >
              <Trash2 size={12} />
              <span>Xóa A</span>
            </button>
          </div>
        )}
      </GlassCard>

      {/* 4 Compact Research KPI Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <StatTile
          kicker="Recall@20 · Hội tụ"
          accent="orange"
          value={latestRound ? latestRound.recall20.toFixed(3) : '—'}
          sub={
            latestRound
              ? `NDCG@20: ${latestRound.ndcg20.toFixed(3)} · Drift TB: ${meanDrift.toFixed(2)}`
              : `Chạy ${algorithm.toUpperCase()} để đo hội tụ`
          }
        />
        <StatTile
          kicker="Latency p50 / p95"
          accent="ink"
          value={latestRound ? `${latestRound.p50} / ${latestRound.p95} ms` : '—'}
          sub={
            stragglerPolicy === 'deadline65'
              ? 'Chính sách cắt ngưỡng 65ms'
              : 'Đồng bộ (chờ node chậm nhất)'
          }
        />
        <StatTile
          kicker="Client tham gia"
          accent="green"
          liveDot={running}
          value={`${reportedCount} / ${activeCount}`}
          sub={`Tổng ${nodes.length} · Dropout ${nodes.length - activeCount} node`}
        />
        <StatTile
          kicker={`Payload (${compression.toUpperCase()})`}
          accent="sky"
          value={formattedBytes}
          sub={
            <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
              <ShieldCheck size={13} /> 0 B dữ liệu ứng viên rời máy
            </span>
          }
        />
      </div>

      {/* Main Research Stage: 3D Topology (Non-IID / Latency) + Node Inspector & Event Log */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <GlassCard padding="md" className="xl:col-span-7 flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="kicker-label">
              Trực quan hóa {nodes.length} client nodes · Vòng {currentRound}/{rounds}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <SegmentedTabs
                layoutId="node-view-mode"
                size="sm"
                value={nodeView}
                onChange={setNodeView}
                options={[
                  { id: '3d', label: '3D Topology' },
                  { id: 'grid', label: 'Lưới ô 2D' },
                ]}
              />
              {nodeView === 'grid' && (
                <SegmentedTabs
                  layoutId="node-grid-filter"
                  size="sm"
                  value={cellFilter}
                  onChange={setCellFilter}
                  options={[
                    { id: 'all', label: 'Tất cả', badge: nodes.length },
                    { id: 'active', label: 'Đã báo cáo', badge: reportedCount },
                    {
                      id: 'slow',
                      label: 'Chậm ≥65ms',
                      badge: nodes.filter((n) => (n.latencyMs ?? 0) >= 65 && !n.isDropped).length,
                    },
                  ]}
                />
              )}
            </div>
          </div>

          {nodeView === '3d' ? (
            <LiveFlTopology3D
              nodes={nodes}
              running={running}
              activeStep={activeStep}
              currentRound={currentRound}
              totalRounds={rounds}
              algorithm={algorithm}
              selectedClientId={selectedNode?.clientId ?? null}
              onSelectClient={(cid) => setSelectedClientId(cid)}
              onToggleStraggler={handleToggleStraggler}
              onToggleDropout={handleToggleDropout}
            />
          ) : (
            <>
              <div className="grid grid-cols-10 sm:grid-cols-15 md:grid-cols-20 gap-1.5 p-3 rounded-[10px] bg-slate-50/90 border border-slate-200/80 min-h-[210px] content-start">
                {visibleNodes.map((node) => {
                  const selected = selectedNode?.clientId === node.clientId;
                  return (
                    <button
                      key={node.clientId}
                      type="button"
                      onClick={() => setSelectedClientId(node.clientId)}
                      title={`${node.name} · p_k=${node.weightSharePct}% · drift=${node.drift} · ${
                        node.isDropped
                          ? 'OFFLINE'
                          : node.latencyMs !== null
                            ? `${node.latencyMs} ms`
                            : 'Chờ vòng'
                      }`}
                      className={`h-6 w-full rounded-[5px] border transition-transform duration-150 cursor-pointer ${cellColorClass(
                        node.latencyMs,
                        selected,
                        node.pulsing,
                        node.isDropped,
                      )}`}
                    />
                  );
                })}
                {visibleNodes.length === 0 && (
                  <div className="col-span-full py-10 text-center text-xs text-[#64748B]">
                    Chưa có node nào khớp bộ lọc hiện tại.
                  </div>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-4 text-[0.74rem] text-[#475569] pt-1">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-xs bg-slate-300" /> Chờ / Offline
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-xs bg-emerald-500" /> Nhanh (&lt;35ms)
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-xs bg-amber-400" /> Trung bình (35–65ms)
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-xs bg-rose-500" /> Straggler (&ge;65ms)
                </span>
              </div>
            </>
          )}
        </GlassCard>

        {/* Right: Research Node Inspector + Event Log */}
        <div className="xl:col-span-5 flex flex-col gap-4">
          <GlassCard padding="md">
            <div className="flex items-center justify-between gap-2 mb-3">
              <span className="kicker-label flex items-center gap-1.5">
                <Cpu size={13} /> Hồ sơ Non-IID &amp; Độ trễ Node
              </span>
              {selectedNode && (
                <StatusBadge
                  tone={
                    selectedNode.isDropped
                      ? 'slate'
                      : selectedNode.latencyMs === null
                        ? 'slate'
                        : selectedNode.latencyMs < 35
                          ? 'green'
                          : selectedNode.latencyMs < 65
                            ? 'warn'
                            : 'red'
                  }
                >
                  {selectedNode.isDropped
                    ? 'OFFLINE'
                    : selectedNode.latencyMs !== null
                      ? `${selectedNode.latencyMs} ms`
                      : 'IDLE'}
                </StatusBadge>
              )}
            </div>

            {selectedNode ? (
              <div className="space-y-3">
                <div>
                  <div className="font-display text-lg font-bold text-[#0F172A]">
                    {selectedNode.name}
                  </div>
                  <div className="font-mono-tech text-xs text-[#64748B]">
                    client_id={selectedNode.clientId} · {selectedNode.nUsers} users · {selectedNode.nJobs} jobs · vòng {selectedNode.lastRound || '—'}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded-lg bg-white/85 border border-slate-200/80 p-2.5">
                    <div className="font-mono-tech text-[0.65rem] text-[#64748B] uppercase">
                      Trọng số p_k
                    </div>
                    <div className="font-display text-base font-bold tabular-nums text-[#0F172A]">
                      {selectedNode.weightSharePct.toFixed(2)}%
                    </div>
                  </div>
                  <div className="rounded-lg bg-white/85 border border-slate-200/80 p-2.5">
                    <div className="font-mono-tech text-[0.65rem] text-[#64748B] uppercase">
                      Client Drift
                    </div>
                    <div
                      className={`font-display text-base font-bold tabular-nums ${
                        selectedNode.drift >= 0.55
                          ? 'text-rose-600'
                          : selectedNode.drift >= 0.28
                            ? 'text-amber-600'
                            : 'text-emerald-600'
                      }`}
                    >
                      {selectedNode.drift.toFixed(2)}
                    </div>
                  </div>
                  <div className="rounded-lg bg-white/85 border border-slate-200/80 p-2.5">
                    <div className="font-mono-tech text-[0.65rem] text-[#64748B] uppercase">
                      Upload ΔW
                    </div>
                    <div className="font-display text-base font-bold tabular-nums text-[#C2410C]">
                      {(selectedNode.bytesUp / 1024).toFixed(0)} KB
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between rounded-lg bg-emerald-50/75 border border-emerald-200/80 px-3 py-2 text-xs text-emerald-800">
                  <span className="inline-flex items-center gap-1.5 font-medium">
                    <HardDriveUpload size={13} /> Chỉ gửi vector ΔW ({compression.toUpperCase()})
                  </span>
                  <span className="font-mono-tech font-bold">0 B RAW</span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-[#64748B]">Chọn một node trong mô hình bên trái.</p>
            )}
          </GlassCard>

          {/* Live Event Stream Log */}
          <GlassCard padding="md" className="flex-1 flex flex-col min-h-[190px]">
            <div className="flex items-center justify-between mb-2">
              <span className="kicker-label flex items-center gap-1.5">
                <Terminal size={13} /> Nhật ký thực nghiệm
              </span>
              <span className="font-mono-tech text-[0.68rem] text-[#64748B]">{logs.length} dòng</span>
            </div>
            <div className="flex-1 max-h-[185px] overflow-y-auto rounded-lg bg-slate-900/[0.035] border border-slate-200/80 p-2.5 space-y-1.5 font-mono-tech text-[0.72rem]">
              {logs.map((entry) => (
                <div key={entry.id} className="flex items-start gap-2 leading-snug">
                  <span className="text-[#64748B] shrink-0">{entry.ts}</span>
                  <span
                    className={`shrink-0 font-bold ${
                      entry.kind === 'ROUND'
                        ? 'text-[#C2410C]'
                        : entry.kind === 'WS'
                          ? 'text-emerald-700'
                          : 'text-[#0F172A]'
                    }`}
                  >
                    [{entry.kind}]
                  </span>
                  <span className="text-[#334155] break-words">{entry.text}</span>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>

      {/* Side-by-Side Research Telemetry Charts (with A/B Overlay + Communication Trade-off X-Axis) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <GlassCard padding="md">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <div>
              <div className="kicker-label flex items-center gap-1.5">
                <Activity size={12} className="text-[#FF5A1F]" />
                {xAxisMode === 'mb' ? 'Đánh đổi Băng thông – Chất lượng' : 'Hội tụ chất lượng gợi ý'}
              </div>
              <h3 className="font-display text-base font-bold text-[#0F172A]">
                {xAxisMode === 'mb'
                  ? 'Recall@20 theo dung lượng truyền (MB)'
                  : 'Recall@20 & NDCG@20 theo vòng'}
              </h3>
            </div>
            <SegmentedTabs
              layoutId="fl-xaxis-mode"
              size="sm"
              value={xAxisMode}
              onChange={setXAxisMode}
              options={[
                { id: 'round', label: 'Theo vòng' },
                { id: 'mb', label: 'Theo MB' },
              ]}
            />
          </div>
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartSeries} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis
                  dataKey="xVal"
                  tick={{ fontSize: 11, fill: '#64748B' }}
                  stroke="#CBD5E1"
                  unit={xAxisMode === 'mb' ? ' MB' : ''}
                />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: '#64748B' }} stroke="#CBD5E1" />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(255,255,255,0.94)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid #E2E8F0',
                    borderRadius: '10px',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Line
                  type="monotone"
                  dataKey="recall20"
                  name={`Recall@20 (${algorithm.toUpperCase()})`}
                  stroke="#FF5A1F"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: '#FF5A1F' }}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="ndcg20"
                  name="NDCG@20"
                  stroke="#0F172A"
                  strokeWidth={1.8}
                  dot={false}
                  connectNulls
                />
                {baselineRun && (
                  <Line
                    type="monotone"
                    dataKey="baseRecall20"
                    name={`Baseline A (${baselineRun.algorithm.toUpperCase()})`}
                    stroke="#64748B"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                    connectNulls
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        <GlassCard padding="md">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="kicker-label">Phân bố độ trễ &amp; tác động Straggler</div>
              <h3 className="font-display text-base font-bold text-[#0F172A]">
                Latency p50 vs p95 theo vòng (ms)
              </h3>
            </div>
            <span className="font-mono-tech text-[10px] font-semibold rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-slate-600">
              {provenanceLabel}
            </span>
          </div>
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartSeries} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="p95Grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EF4444" stopOpacity={0.22} />
                    <stop offset="95%" stopColor="#EF4444" stopOpacity={0.01} />
                  </linearGradient>
                  <linearGradient id="p50Grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.22} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0.01} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="round" tick={{ fontSize: 11, fill: '#64748B' }} stroke="#CBD5E1" />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} stroke="#CBD5E1" />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(255,255,255,0.94)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid #E2E8F0',
                    borderRadius: '10px',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Area
                  type="monotone"
                  dataKey="p95"
                  name="p95 (Straggler)"
                  stroke="#EF4444"
                  strokeWidth={2}
                  fill="url(#p95Grad)"
                  connectNulls
                />
                <Area
                  type="monotone"
                  dataKey="p50"
                  name="p50 (Median)"
                  stroke="#10B981"
                  strokeWidth={2}
                  fill="url(#p50Grad)"
                  connectNulls
                />
                {baselineRun && (
                  <Area
                    type="monotone"
                    dataKey="baseP95"
                    name={`Baseline A p95 (${baselineRun.algorithm.toUpperCase()})`}
                    stroke="#64748B"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    fill="none"
                    dot={false}
                    connectNulls
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
      </div>

      {/* Non-IID Client Fairness & Drift Scatter Plot (Coordinated Brushing) */}
      <GlassCard padding="md">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div>
            <div className="kicker-label flex items-center gap-1.5">
              <Scale size={12} className="text-[#FF5A1F]" />
              Non-IID Fairness &amp; Coordinated Brushing
            </div>
            <h3 className="font-display text-base font-bold text-[#0F172A]">
              Phân bố Quy mô dữ liệu vs{' '}
              {scatterY === 'drift' ? 'Client Drift' : 'Latency (ms)'} giữa {nodes.length} Employer Nodes
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex flex-wrap items-center gap-2 font-mono-tech text-[11px]">
              <span className="rounded-lg border border-slate-200 bg-white/85 px-2.5 py-1 text-slate-700">
                Top 10% Large Drift:{' '}
                <strong className="text-[#0F172A]">{fairnessStats.avgLargeDrift.toFixed(3)}</strong>
              </span>
              <span className="rounded-lg border border-sky-200 bg-sky-50/80 px-2.5 py-1 text-sky-900">
                Long-Tail Drift:{' '}
                <strong className="text-sky-700">{fairnessStats.avgSmallDrift.toFixed(3)}</strong>
              </span>
              <span className="rounded-lg border border-orange-200 bg-[#FFF7ED] px-2.5 py-1 text-[#C2410C]">
                Fairness Gap: <strong>Δ {fairnessStats.gap.toFixed(3)}</strong>
              </span>
            </div>

            <SegmentedTabs
              layoutId="scatter-y-axis"
              size="sm"
              value={scatterY}
              onChange={setScatterY}
              options={[
                { id: 'drift', label: 'Client Drift' },
                { id: 'latency', label: 'Latency (ms)' },
              ]}
            />
          </div>
        </div>

        <div className="h-[260px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 20, bottom: 14, left: -4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis
                type="number"
                dataKey="logApps"
                name="log10(nApps)"
                domain={['dataMin - 0.1', 'dataMax + 0.1']}
                tickFormatter={(v: number) => Number(v).toFixed(2)}
                tick={{ fontSize: 11, fill: '#64748B' }}
                stroke="#CBD5E1"
                label={{
                  value: 'Quy mô dữ liệu local: log₁₀(nApps)',
                  position: 'insideBottom',
                  offset: -8,
                  style: { fontSize: 11, fill: '#64748B', fontWeight: 600 },
                }}
              />
              <YAxis
                type="number"
                dataKey="yVal"
                name={scatterY === 'drift' ? 'Client Drift' : 'Latency (ms)'}
                domain={scatterY === 'drift' ? [0, 'dataMax + 0.12'] : ['auto', 'auto']}
                tickFormatter={(v: number) =>
                  scatterY === 'drift' ? Number(v).toFixed(2) : `${Math.round(v)}`
                }
                tick={{ fontSize: 11, fill: '#64748B' }}
                stroke="#CBD5E1"
              />
              <ZAxis type="number" dataKey="zSize" range={[40, 210]} />
              <Tooltip
                cursor={{ strokeDasharray: '3 3', stroke: '#FF5A1F' }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const pt = payload[0].payload as (typeof scatterData)[number];
                  return (
                    <div className="rounded-xl border border-slate-200 bg-white/95 p-2.5 shadow-lg backdrop-blur-md text-xs space-y-1">
                      <div className="font-display font-bold text-[#0F172A]">{pt.name}</div>
                      <div className="font-mono-tech text-[10px] text-slate-500">
                        {SCATTER_TIER_LABEL[pt.tier]} · client_id={pt.clientId}
                      </div>
                      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 pt-1 border-t border-slate-100 font-mono-tech text-[11px]">
                        <span className="text-slate-500">nApps:</span>
                        <span className="font-semibold text-slate-900">{pt.nApps}</span>
                        <span className="text-slate-500">Trọng số p_k:</span>
                        <span className="font-semibold text-slate-900">{pt.weightSharePct}%</span>
                        <span className="text-slate-500">Client Drift:</span>
                        <span className="font-semibold text-[#C2410C]">{pt.drift.toFixed(3)}</span>
                        <span className="text-slate-500">Latency:</span>
                        <span className="font-semibold text-slate-900">
                          {pt.latencyMs !== null ? `${pt.latencyMs} ms` : 'IDLE'}
                        </span>
                      </div>
                      <div className="text-[10px] text-[#C2410C] pt-0.5">
                        Click để soi node trên 3D Topology
                      </div>
                    </div>
                  );
                }}
              />
              <Scatter
                name="Employer Clients"
                data={scatterData}
                isAnimationActive={false}
                onClick={(entry) => {
                  if (entry && typeof entry.clientId === 'number') {
                    setSelectedClientId(entry.clientId);
                  }
                }}
                style={{ cursor: 'pointer' }}
              >
                {scatterData.map((entry) => {
                  const isSel = selectedNode?.clientId === entry.clientId;
                  return (
                    <Cell
                      key={entry.clientId}
                      fill={SCATTER_TIER_COLOR[entry.tier]}
                      fillOpacity={entry.tier === 'offline' ? 0.4 : isSel ? 1 : 0.78}
                      stroke={isSel ? '#0F172A' : '#ffffff'}
                      strokeWidth={isSel ? 2.6 : 1}
                    />
                  );
                })}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 text-[11.5px] text-[#475569]">
          <div className="flex flex-wrap items-center gap-3.5">
            {(['large', 'medium', 'small', 'offline'] as const).map((tier) => (
              <span key={tier} className="inline-flex items-center gap-1.5">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ background: SCATTER_TIER_COLOR[tier] }}
                />
                <span>{SCATTER_TIER_LABEL[tier]}</span>
              </span>
            ))}
          </div>
          <span className="font-mono-tech text-[11px] text-[#64748B]">
            Click vào bất kỳ điểm nào để đồng bộ chọn trên 3D Topology &amp; Node Inspector
          </span>
        </div>
      </GlassCard>
    </div>
  );
};
