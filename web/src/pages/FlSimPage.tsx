import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Play, Pause, Server, ArrowRight, Radio, Layers, TrendingUp } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
  Legend,
  ReferenceLine,
  Cell,
} from 'recharts';
import { api, type FlSimResponse } from '../lib/api';
import {
  ErrorPanel,
  GlassCard,
  GlassExpander,
  LoadingPanel,
  PageHeader,
  SegmentedTabs,
  StatTile,
  StatusBadge,
} from '../components/ui/Primitives';

const TOOLTIP_STYLE = {
  background: 'rgba(255,255,255,0.94)',
  backdropFilter: 'blur(12px)',
  border: '1px solid #E2E8F0',
  borderRadius: '10px',
  fontSize: '12px',
  boxShadow: '0 8px 24px rgba(15,23,42,0.08)',
};

export const FlSimPage: React.FC = () => {
  const [data, setData] = useState<FlSimResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [scenarioKey, setScenarioKey] = useState<string>('20_fixed');
  const [universe, setUniverse] = useState<'fl' | 'global'>('fl');
  const [autoplay, setAutoplay] = useState(false);
  const [speed, setSpeed] = useState<'slow' | 'med' | 'fast'>('med');
  const [uptoRound, setUptoRound] = useState<number>(6);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.flSim();
      setData(res);
      if (res.scenarios.length) {
        const def = res.scenarios.find((s) => s.key === '20_fixed') ?? res.scenarios[0];
        setScenarioKey(def.key);
        setUptoRound(def.curve.length || 6);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Không tải được dữ liệu mô phỏng FL (V3).');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const activeScenario = useMemo(() => {
    if (!data?.scenarios.length) return null;
    return data.scenarios.find((s) => s.key === scenarioKey) ?? data.scenarios[0];
  }, [data, scenarioKey]);

  const maxRound = activeScenario?.curve.length || 6;

  useEffect(() => {
    if (activeScenario) {
      setUptoRound(activeScenario.curve.length || 6);
      setAutoplay(false);
    }
  }, [activeScenario?.key]);

  useEffect(() => {
    if (!autoplay || maxRound <= 1) return;
    const ms = speed === 'slow' ? 950 : speed === 'med' ? 540 : 280;
    const id = window.setInterval(() => {
      setUptoRound((r) => (r >= maxRound ? 1 : r + 1));
    }, ms);
    return () => window.clearInterval(id);
  }, [autoplay, speed, maxRound]);

  const visibleCurve = useMemo(() => {
    if (!activeScenario) return [];
    return activeScenario.curve
      .filter((pt) => pt.round <= uptoRound)
      .map((pt) => ({
        round: pt.round,
        recall20: universe === 'fl' ? pt.fl_recall20 : pt.global_recall20,
        ndcg20: universe === 'fl' ? pt.fl_ndcg20 : pt.global_ndcg20,
        loss: pt.loss,
      }));
  }, [activeScenario, uptoRound, universe]);

  // Highlighted Ablation Study comparison bar data
  const ablationHighlights = useMemo(() => {
    if (!data?.ablation.length) return [];
    const pickOrder: Array<{ match: string; short: string; color: string }> = [
      { match: '(b) bỏ lớp occupation', short: 'Bỏ Occ+Skill', color: '#94A3B8' },
      { match: '(a) bỏ lớp skill', short: 'Bỏ Skill', color: '#64748B' },
      { match: '(d) FedProx', short: 'FedProx', color: '#0EA5E9' },
      { match: '(d) FedAvg unweighted', short: 'Unweighted', color: '#334155' },
      { match: '(base) đầy đủ', short: 'Occ+Skill (Base)', color: '#FF5A1F' },
      { match: '(f1) base: nghề + kỹ năng', short: 'Catalog O*NET', color: '#EA580C' },
    ];
    const items: Array<{ name: string; recall20: number; ndcg20: number; color: string; variant: string }> = [];
    for (const p of pickOrder) {
      const found = data.ablation.find((r) => r.variant.includes(p.match));
      if (found) {
        items.push({
          name: p.short,
          recall20: Number(found.recall20.toFixed(4)),
          ndcg20: Number(found.ndcg20.toFixed(4)),
          color: p.color,
          variant: found.variant,
        });
      }
    }
    return items;
  }, [data]);

  // Client Scaling 5 -> 10 -> 20 nodes bar data
  const scalingBars = useMemo(() => {
    if (!data?.scenarios.length) return [];
    const keys = ['5_node', '10_node', '20_fixed'];
    return keys
      .map((k) => data.scenarios.find((s) => s.key === k))
      .filter((s): s is NonNullable<typeof s> => Boolean(s))
      .map((s) => ({
        name: `${s.n_clients} Node`,
        recall20: Number(s.fl.recall20.toFixed(4)),
        ndcg20: Number(s.fl.ndcg20.toFixed(4)),
        coveragePct: Number((s.fl.coverage * 100).toFixed(1)),
      }));
  }, [data]);

  if (loading) {
    return (
      <div className="space-y-5">
        <PageHeader
          kicker="03 // FEDERATED LEARNING SIMULATION · V3"
          title="Mô phỏng Federated Learning"
          subtitle="Đối chiếu 5 kịch bản FedAvg, Ablation Study (15 variants) và Client Scaling trên CareerBuilder + O*NET (V3)."
        />
        <LoadingPanel label="Đang tải dữ liệu thực nghiệm V3 từ /api/dashboard/fl-sim..." />
      </div>
    );
  }

  if (error || !data || !activeScenario) {
    return (
      <div className="space-y-5">
        <PageHeader
          kicker="03 // FEDERATED LEARNING SIMULATION · V3"
          title="Mô phỏng Federated Learning"
          subtitle="Đối chiếu kịch bản FedAvg/FedProx và Ablation trên CareerBuilder + O*NET (V3)."
        />
        <ErrorPanel message={error ?? 'Không có dữ liệu.'} onRetry={load} />
      </div>
    );
  }

  const activeMetric = universe === 'fl' ? activeScenario.fl : activeScenario.global;
  const refLightGCN = universe === 'fl' ? data.baselines_fl.lightgcn : data.baselines_global.lightgcn;
  const refGraphSAGE = universe === 'fl' ? data.baselines_fl.graphsage : data.baselines_global.graphsage;
  const refPopularity = universe === 'fl' ? data.baselines_fl.popularity : data.baselines_global.popularity;
  const yMax = Math.min(1, Math.max(refLightGCN, activeMetric.recall20) * 1.16);

  return (
    <div className="space-y-5">
      <PageHeader
        kicker="03 // FEDERATED LEARNING SIMULATION · V3"
        title="Mô phỏng Federated Learning"
        subtitle={`Cross-Silo FL trên ${data.cross_silo.n_clients.toLocaleString('vi-VN')} nhà tuyển dụng CareerBuilder (${data.cross_silo.pct_users_multi_client.toFixed(2)}% ứng viên đa công ty · 0 B raw data rời silo).`}
        actions={
          <Link to="/giam-sat-node" className="btn-primary">
            <Server size={15} />
            <span>Mở Giám sát node FL</span>
            <ArrowRight size={14} />
          </Link>
        }
      />

      {/* Single-Row Control Bar */}
      <GlassCard padding="sm" className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <label className="flex items-center gap-2 text-xs font-semibold text-[#475569]">
            <span className="font-mono-tech uppercase text-[0.68rem]">Kịch bản</span>
            <select
              value={scenarioKey}
              onChange={(e) => setScenarioKey(e.target.value)}
              className="input-control py-1.5 text-xs font-semibold max-w-[300px]"
            >
              {data.scenarios.map((sc) => (
                <option key={sc.key} value={sc.key}>
                  {sc.label}
                </option>
              ))}
            </select>
          </label>

          <SegmentedTabs
            layoutId="flsim-universe-tab"
            size="sm"
            value={universe}
            onChange={setUniverse}
            options={[
              { id: 'fl', label: 'FL Catalog' },
              { id: 'global', label: 'Global (82.876)' },
            ]}
          />

          <button
            type="button"
            onClick={() => {
              if (!autoplay && uptoRound >= maxRound) setUptoRound(1);
              setAutoplay((v) => !v);
            }}
            className={autoplay ? 'btn-primary py-1.5 px-3 text-xs' : 'btn-secondary py-1.5 px-3 text-xs'}
          >
            {autoplay ? <Pause size={13} /> : <Play size={13} fill="currentColor" />}
            <span>{autoplay ? 'Tạm dừng' : 'Tự chạy'}</span>
          </button>

          <select
            value={speed}
            disabled={!autoplay}
            onChange={(e) => setSpeed(e.target.value as typeof speed)}
            aria-label="Tốc độ phát"
            className="input-control py-1.5 text-xs font-semibold disabled:opacity-50"
          >
            <option value="slow">Chậm</option>
            <option value="med">Vừa</option>
            <option value="fast">Nhanh</option>
          </select>
        </div>

        {/* Round Slider */}
        <div className="flex items-center gap-3 min-w-[200px] flex-1 sm:flex-initial sm:min-w-[230px]">
          <span className="font-mono-tech text-xs font-bold text-[#C2410C] shrink-0">
            Vòng {uptoRound}/{maxRound}
          </span>
          <input
            type="range"
            min={1}
            max={maxRound}
            value={uptoRound}
            onChange={(e) => {
              setAutoplay(false);
              setUptoRound(Number(e.target.value));
            }}
            className="range-orange w-full"
          />
        </div>
      </GlassCard>

      {/* 4 V3 KPI Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <StatTile
          kicker="Recall@20 kịch bản chọn"
          accent="orange"
          value={activeMetric.recall20.toFixed(4)}
          sub={activeScenario.catalog_label}
        />
        <StatTile
          kicker="NDCG@20 / MRR@20"
          accent="ink"
          value={`${activeMetric.ndcg20.toFixed(4)} / ${activeMetric.mrr20.toFixed(4)}`}
          sub={`Coverage ${(activeMetric.coverage * 100).toFixed(1)}% · ${activeMetric.seconds.toFixed(1)}s`}
        />
        <StatTile
          kicker="Cross-Silo CareerBuilder"
          accent="sky"
          value={`${data.cross_silo.pct_users_multi_client.toFixed(2)}%`}
          sub={`TB ${data.cross_silo.mean_clients_per_user} client/user · chỉ ${data.cross_silo.pct_same_client_test.toFixed(2)}% test cùng silo`}
        />
        <StatTile
          kicker="Độ trễ vòng thực đo"
          accent="green"
          value={`${data.latency.p50_ms.toFixed(0)} / ${data.latency.p95_ms.toFixed(0)} ms`}
          sub={`p50 / p95 (${data.latency.n_samples ?? 300} mẫu perf_counter)`}
        />
      </div>

      {/* Main 6-Round Convergence Chart with Reference Lines */}
      <GlassCard padding="md">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div>
            <div className="kicker-label">Hội tụ 6 vòng FedAvg vs Baselines tập trung</div>
            <h2 className="font-display text-lg font-bold text-[#0F172A]">
              {activeScenario.short} — {universe === 'fl' ? 'FL Catalog' : 'Global Catalog (82.876 tin)'}
            </h2>
          </div>
          <StatusBadge tone="orange" pulse={autoplay}>
            <Radio size={12} /> Vòng 1 → {uptoRound}
          </StatusBadge>
        </div>

        <div className="h-[310px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={visibleCurve} margin={{ top: 14, right: 24, left: -6, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis
                dataKey="round"
                tick={{ fontSize: 11, fill: '#64748B' }}
                stroke="#CBD5E1"
                label={{ value: 'Vòng FL', position: 'insideBottomRight', offset: -4, fontSize: 11, fill: '#64748B' }}
              />
              <YAxis
                domain={[0, Number(yMax.toFixed(2))]}
                tick={{ fontSize: 11, fill: '#64748B' }}
                stroke="#CBD5E1"
              />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />

              <ReferenceLine
                y={refLightGCN}
                stroke="#0F172A"
                strokeDasharray="6 4"
                label={{
                  value: `LightGCN (${refLightGCN.toFixed(4)})`,
                  position: 'insideTopRight',
                  fill: '#0F172A',
                  fontSize: 11,
                  fontWeight: 600,
                }}
              />
              <ReferenceLine
                y={refGraphSAGE}
                stroke="#0EA5E9"
                strokeDasharray="4 4"
                label={{
                  value: `GraphSAGE (${refGraphSAGE.toFixed(4)})`,
                  position: 'insideTopLeft',
                  fill: '#0369A1',
                  fontSize: 11,
                }}
              />
              <ReferenceLine
                y={refPopularity}
                stroke="#94A3B8"
                strokeDasharray="3 3"
                label={{
                  value: `Popularity (${refPopularity.toFixed(4)})`,
                  position: 'insideBottomRight',
                  fill: '#64748B',
                  fontSize: 11,
                }}
              />

              <Line
                type="monotone"
                dataKey="recall20"
                name="FedAvg Recall@20"
                stroke="#FF5A1F"
                strokeWidth={3}
                dot={{ r: 4, fill: '#FF5A1F' }}
                activeDot={{ r: 6 }}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="ndcg20"
                name="FedAvg NDCG@20"
                stroke="#C2410C"
                strokeWidth={2}
                strokeDasharray="4 3"
                dot={{ r: 3, fill: '#C2410C' }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </GlassCard>

      {/* Side-by-Side: Ablation Study Chart & Client Scaling Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <GlassCard padding="md">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="kicker-label flex items-center gap-1.5">
                <Layers size={13} /> Ablation Study (15 variants)
              </div>
              <h3 className="font-display text-base font-bold text-[#0F172A]">
                Đóng góp cầu nối O*NET + Skill &amp; Thuật toán FL (Recall@20)
              </h3>
            </div>
            <StatusBadge tone="orange">+9,0% R@20</StatusBadge>
          </div>
          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ablationHighlights} margin={{ top: 8, right: 12, left: -12, bottom: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 10.5, fill: '#475569' }}
                  interval={0}
                  angle={-15}
                  textAnchor="end"
                  stroke="#CBD5E1"
                />
                <YAxis domain={[0, 0.65]} tick={{ fontSize: 11, fill: '#64748B' }} stroke="#CBD5E1" />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="recall20" name="Recall@20" radius={[6, 6, 0, 0]}>
                  {ablationHighlights.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        <GlassCard padding="md">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="kicker-label flex items-center gap-1.5">
                <TrendingUp size={13} /> Co giãn quy mô Silo (Client Scaling)
              </div>
              <h3 className="font-display text-base font-bold text-[#0F172A]">
                Tăng số nhà tuyển dụng tham gia: 5 → 10 → 20 Node
              </h3>
            </div>
            <StatusBadge tone="green">×2,02 Recall@20</StatusBadge>
          </div>
          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scalingBars} margin={{ top: 8, right: 12, left: -12, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#475569' }} stroke="#CBD5E1" />
                <YAxis domain={[0, 0.55]} tick={{ fontSize: 11, fill: '#64748B' }} stroke="#CBD5E1" />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="recall20" name="Recall@20 (FL)" fill="#FF5A1F" radius={[6, 6, 0, 0]} />
                <Bar dataKey="ndcg20" name="NDCG@20 (FL)" fill="#0F172A" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
      </div>

      {/* Collapsed Full Tables: 15-Variant Ablation, 8-Config Sweep, Top 20 Employers */}
      <div className="space-y-3">
        <GlassExpander
          title={`Bảng đầy đủ ${data.ablation.length} biến thể Ablation Study`}
          badge="ABLATION"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 font-mono-tech uppercase text-[0.68rem] text-[#64748B]">
                  <th className="py-2 pr-4">Biến thể</th>
                  <th className="py-2 pr-3 text-right">Recall@20</th>
                  <th className="py-2 pr-3 text-right">NDCG@20</th>
                  <th className="py-2 pr-3 text-right">MRR@20</th>
                  <th className="py-2 pr-3 text-right">Coverage</th>
                  <th className="py-2 text-right">Giây</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70">
                {data.ablation.map((row) => {
                  const isBase = row.variant.includes('(base)') || row.variant.includes('(f1)');
                  return (
                    <tr
                      key={row.variant}
                      className={isBase ? 'bg-[#FFF7ED]/75 font-semibold' : 'hover:bg-slate-50/70'}
                    >
                      <td className="py-2 pr-4 text-[#0F172A]">
                        <div>{row.variant}</div>
                        {row.note && <div className="text-[0.72rem] text-[#64748B] font-normal">{row.note}</div>}
                      </td>
                      <td className={`py-2 pr-3 text-right font-mono-tech font-bold ${isBase ? 'text-[#C2410C]' : ''}`}>
                        {row.recall20.toFixed(4)}
                      </td>
                      <td className="py-2 pr-3 text-right font-mono-tech">{row.ndcg20.toFixed(4)}</td>
                      <td className="py-2 pr-3 text-right font-mono-tech">{row.mrr20.toFixed(4)}</td>
                      <td className="py-2 pr-3 text-right font-mono-tech">
                        {(row.coverage * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 text-right font-mono-tech text-[#64748B]">
                        {row.seconds.toFixed(1)}s
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </GlassExpander>

        <GlassExpander
          title={`Bảng Sweep siêu tham số (${data.sweep.length} cấu hình n_clients / dim / layers / local_epochs)`}
          badge="SWEEP"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 font-mono-tech uppercase text-[0.68rem] text-[#64748B]">
                  <th className="py-2 pr-3">n_clients</th>
                  <th className="py-2 pr-3">dim</th>
                  <th className="py-2 pr-3">layers</th>
                  <th className="py-2 pr-3">local_epochs</th>
                  <th className="py-2 pr-3 text-right">Recall@20 (Toàn cục)</th>
                  <th className="py-2 pr-3 text-right">NDCG@20</th>
                  <th className="py-2 text-right">Giây</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70">
                {data.sweep.map((row, idx) => (
                  <tr key={idx} className="hover:bg-[#FFF7ED]/50">
                    <td className="py-2 pr-3 font-mono-tech font-semibold">{row.n_clients}</td>
                    <td className="py-2 pr-3 font-mono-tech">{row.dim}</td>
                    <td className="py-2 pr-3 font-mono-tech">{row.layers}</td>
                    <td className="py-2 pr-3 font-mono-tech">{row.local_epochs}</td>
                    <td className="py-2 pr-3 text-right font-mono-tech font-bold text-[#C2410C]">
                      {row.recall20.toFixed(4)}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono-tech">{row.ndcg20.toFixed(4)}</td>
                    <td className="py-2 text-right font-mono-tech text-[#64748B]">{row.seconds.toFixed(1)}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassExpander>

        <GlassExpander
          title={`Top ${data.top_clients.length} nhà tuyển dụng lớn nhất (CareerBuilder Silos)`}
          badge="CLIENTS"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 font-mono-tech uppercase text-[0.68rem] text-[#64748B]">
                  <th className="py-2 pr-3">Client ID</th>
                  <th className="py-2 pr-4">Nhà tuyển dụng</th>
                  <th className="py-2 pr-3 text-right">Đơn ứng tuyển</th>
                  <th className="py-2 pr-3 text-right">Số tin</th>
                  <th className="py-2 text-right">Số ứng viên</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70">
                {data.top_clients.map((cl) => (
                  <tr key={cl.client_id} className="hover:bg-[#FFF7ED]/50">
                    <td className="py-2 pr-3 font-mono-tech text-[#64748B]">#{cl.client_id}</td>
                    <td className="py-2 pr-4 font-semibold text-[#0F172A]">{cl.name}</td>
                    <td className="py-2 pr-3 text-right font-mono-tech font-bold text-[#C2410C]">
                      {cl.n_apps.toLocaleString('vi-VN')}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono-tech">
                      {cl.n_jobs.toLocaleString('vi-VN')}
                    </td>
                    <td className="py-2 text-right font-mono-tech">
                      {cl.n_users.toLocaleString('vi-VN')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassExpander>
      </div>
    </div>
  );
};
