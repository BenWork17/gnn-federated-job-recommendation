import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Layers, GitBranch, Database } from 'lucide-react';
import { api, type OverviewResponse } from '../lib/api';
import { FederatedGlassConstellation } from '../components/three';
import {
  BorderBeamCard,
  ErrorPanel,
  GlassCard,
  GlassExpander,
  LoadingPanel,
  PageHeader,
  StatTile,
  StatusBadge,
} from '../components/ui/Primitives';

export const OverviewPage: React.FC = () => {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.overview();
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Không tải được dữ liệu tổng quan V3.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="space-y-5">
        <PageHeader
          kicker="DSS · ĐỒ ÁN CUỐI KỲ · CAREERBUILDER + O*NET (V3)"
          title="GNN + Federated Learning cho gợi ý việc làm"
          subtitle="Vì sao không thể gom dữ liệu của 9.116 nhà tuyển dụng về một máy chủ, và đồ thị tri thức 264.995 nút giải quyết thế nào?"
        />
        <LoadingPanel label="Đang tải số liệu CareerBuilder + O*NET (V3) từ /api/dashboard/overview..." />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-5">
        <PageHeader
          kicker="DSS · ĐỒ ÁN CUỐI KỲ · CAREERBUILDER + O*NET (V3)"
          title="GNN + Federated Learning cho gợi ý việc làm"
          subtitle="Vì sao không thể gom dữ liệu tuyển dụng về một máy chủ, và đồ thị giúp gì?"
        />
        <ErrorPanel message={error ?? 'Không có dữ liệu.'} onRetry={load} />
      </div>
    );
  }

  const m = data.meta;
  const fl = data.fl_universe;
  const lat = data.latency;

  const maxR = Math.max(fl.lightgcn, 1e-6);
  const tracks = [
    { label: 'Popularity', value: fl.popularity, color: '#94A3B8', textClass: 'text-[#64748B]', isFl: false },
    { label: 'FedAvg (50N)', value: fl.fedavg_50, color: '#FB923C', textClass: 'text-[#C2410C]', isFl: true },
    { label: 'FedAvg (20N)', value: fl.fedavg_20_fixed, color: '#FF5A1F', textClass: 'text-[#C2410C]', isFl: true },
    { label: 'FedAvg (O*NET)', value: fl.fedavg_20_occ, color: '#EA580C', textClass: 'text-[#C2410C]', isFl: true },
    { label: 'GraphSAGE', value: fl.graphsage, color: '#0EA5E9', textClass: 'text-[#0369A1]', isFl: false },
    { label: 'LightGCN', value: fl.lightgcn, color: '#0F172A', textClass: 'text-[#0F172A]', isFl: false },
  ];

  const pubPct = m.public_edge_pct ?? (m.public_edges / Math.max(m.n_edges, 1)) * 100;
  const privPct = m.private_edge_pct ?? 100 - pubPct;

  return (
    <div className="space-y-5">
      <PageHeader
        kicker="DSS · ĐỒ ÁN CUỐI KỲ · PHAN GIA BẢO 102220265 · NGUYỄN VĂN CHƯƠNG 102220267 · V3"
        title="GNN + Federated Learning cho gợi ý việc làm"
        subtitle="Đồ thị tri thức CareerBuilder + O*NET (264.995 nút · 764.364 cạnh) cho 9.116 nhà tuyển dụng độc lập."
        actions={
          <Link to="/lien-bang" className="btn-primary">
            <span>Mô phỏng FL</span>
            <ArrowRight size={15} />
          </Link>
        }
      />

      {/* Asymmetric 7:5 Bento Hero */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
        {/* Left: ThreeUI FederatedGlassConstellation */}
        <GlassCard
          padding="none"
          sheen={false}
          className="lg:col-span-7 overflow-hidden min-h-[380px] flex"
        >
          <FederatedGlassConstellation
            nClients={m.n_clients}
            recallScore={fl.fedavg_20_occ}
            className="w-full min-h-[380px]"
          />
        </GlassCard>

        {/* Right: Border Beam Hero KPI Card */}
        <BorderBeamCard padding="lg" className="lg:col-span-5 flex flex-col justify-between min-h-[380px]">
          <div className="flex flex-col justify-between h-full gap-4">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
                <span className="kicker-label">01 // FL CATALOG BENCHMARK (RECALL@20)</span>
                <StatusBadge tone="orange" pulse className="whitespace-nowrap shrink-0">
                  7,2–10,6× Popularity
                </StatusBadge>
              </div>
              <div className="flex items-baseline gap-3">
                <span className="font-display text-[3.1rem] leading-none font-bold tracking-[-0.045em] tabular-nums text-[#0F172A]">
                  {fl.fedavg_20_occ.toFixed(4)}
                </span>
                <span className="font-mono-tech text-xs font-semibold text-[#C2410C]">
                  FedAvg · O*NET
                </span>
              </div>
              <p className="mt-2 text-[0.83rem] leading-relaxed text-[#475569]">
                <strong className="text-[#0F172A]">FedAvg</strong> đạt{' '}
                <strong className="text-[#C2410C] font-mono-tech">{fl.fedavg_20_occ.toFixed(4)}</strong> (956 tin có nghề O*NET),{' '}
                <strong className="text-[#C2410C] font-mono-tech">{fl.fedavg_20_fixed.toFixed(4)}</strong> (20N · 4.511 tin) và{' '}
                <strong className="text-[#C2410C] font-mono-tech">{fl.fedavg_50.toFixed(4)}</strong> (50N · 9.058 tin) so với mốc tập trung{' '}
                <strong className="text-[#0F172A] font-mono-tech">LightGCN {fl.lightgcn.toFixed(4)}</strong>.
              </p>
            </div>

            {/* Proportional Comparison Bars */}
            <div className="space-y-2.5 pt-3 border-t border-slate-200/80">
              {tracks.map((tr) => {
                const w = Math.min(100, (tr.value / maxR) * 100);
                return (
                  <div key={tr.label} className="grid grid-cols-[106px_1fr_54px] items-center gap-2.5">
                    <span className={`text-[0.76rem] font-semibold truncate ${tr.textClass}`}>
                      {tr.label}
                    </span>
                    <div
                      className={`h-2 w-full rounded-full overflow-hidden ${
                        tr.isFl ? 'bg-[#FFF7ED] ring-1 ring-[#FED7AA]' : 'bg-slate-200/75'
                      }`}
                    >
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${w.toFixed(1)}%`, backgroundColor: tr.color }}
                      />
                    </div>
                    <span className={`font-mono-tech text-[0.74rem] font-bold text-right ${tr.textClass}`}>
                      {tr.value.toFixed(4)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </BorderBeamCard>
      </div>

      {/* Three Compact V3 Glass Metric Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatTile
          kicker="02 // QUY MÔ ĐỒ THỊ V3"
          value={`${m.n_nodes.toLocaleString('vi-VN')} nút`}
          accent="ink"
          badge={<StatusBadge tone="slate">{m.n_edges.toLocaleString('vi-VN')} cạnh</StatusBadge>}
          sub={
            <>
              <strong className="text-[#0F172A] font-mono-tech">{m.n_users.toLocaleString('vi-VN')}</strong> ứng viên ·{' '}
              <strong className="text-[#0F172A] font-mono-tech">{m.n_jobs.toLocaleString('vi-VN')}</strong> tin ·{' '}
              <strong className="text-[#0F172A] font-mono-tech">{m.n_occupations}</strong> nghề O*NET ·{' '}
              <strong className="text-[#0F172A] font-mono-tech">{m.n_skills.toLocaleString('vi-VN')}</strong> KN.
            </>
          }
        />

        <StatTile
          kicker="03 // CROSS-SILO FL (0 B RAW DATA)"
          value={`${m.n_clients.toLocaleString('vi-VN')} Node FL`}
          accent="orange"
          liveDot
          badge={
            <StatusBadge tone="green">
              <ShieldCheck size={12} /> Verified
            </StatusBadge>
          }
          sub={
            <>
              <strong className="text-[#0F172A] font-mono-tech">{m.pct_users_multi_client.toFixed(2)}%</strong> ứng viên nộp đa công ty (TB{' '}
              <strong className="text-[#0F172A] font-mono-tech">{m.mean_clients_per_user}</strong> client/user) · chỉ{' '}
              <strong className="text-[#0F172A] font-mono-tech">{m.pct_same_client_test.toFixed(2)}%</strong> test cùng silo.
            </>
          }
        />

        <StatTile
          kicker="04 // THỰC NGHIỆM & ĐỘ TRỄ"
          value={`${m.n_test_uj.toLocaleString('vi-VN')} cạnh test`}
          accent="sky"
          badge={<StatusBadge tone="slate">p50 {Math.round(lat.p50_ms)}ms</StatusBadge>}
          sub={
            <>
              Train <strong className="text-[#0F172A] font-mono-tech">{m.n_train_uj.toLocaleString('vi-VN')}</strong> · Test sạch{' '}
              <strong className="text-[#0F172A] font-mono-tech">{m.n_test_clean.toLocaleString('vi-VN')}</strong> · Độ trễ vòng{' '}
              <strong className="text-[#0F172A] font-mono-tech">p95 = {lat.p95_ms.toFixed(1)} ms</strong>.
            </>
          }
        />
      </div>

      {/* Two Editorial Narrative Glass Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <GlassCard tilt padding="lg" className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="kicker-label">VÌ SAO CẦN FEDERATED GRAPH TRÊN CAREERBUILDER + O*NET</span>
            <Layers size={16} className="text-[#EA580C]" />
          </div>
          <p className="text-[0.9rem] leading-[1.6] text-[#334155]">
            Mỗi nhà tuyển dụng trong <strong className="text-[#0F172A] font-mono-tech">{m.n_clients.toLocaleString('vi-VN')} silo</strong> chỉ thấy lượt ứng tuyển vào tin của chính mình, trong khi{' '}
            <strong className="text-[#0F172A] font-mono-tech">{m.pct_users_multi_client.toFixed(2)}%</strong> ứng viên ({m.n_users_multi_client.toLocaleString('vi-VN')} người) nộp đơn đa công ty và{' '}
            <strong className="text-[#C2410C] font-mono-tech">{(100 - m.pct_same_client_test).toFixed(2)}%</strong> lượt ứng tuyển kiểm thử rơi sang nhà tuyển dụng khác.{' '}
            <strong className="text-[#0F172A]">Federated GNN</strong> kết nối tri thức chéo qua cầu nối công khai{' '}
            <strong className="text-[#0F172A]">Nghề O*NET – Kỹ năng</strong> mà giữ nguyên 0 dòng dữ liệu thô rời client.
          </p>
        </GlassCard>

        <GlassCard tilt padding="lg" className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="kicker-label">PHÂN TÁCH CÔNG KHAI / RIÊNG TƯ &amp; POSTGRESQL</span>
            <GitBranch size={16} className="text-[#0F172A]" />
          </div>

          <div className="h-3 w-full rounded-full overflow-hidden flex bg-slate-200/80 ring-1 ring-slate-200">
            <div
              className="h-full bg-[#FF5A1F]"
              style={{ width: `${Math.max(pubPct, 4).toFixed(1)}%` }}
              title={`Công khai: ${pubPct.toFixed(2)}%`}
            />
            <div
              className="h-full bg-[#0F172A]"
              style={{ width: `${(100 - Math.max(pubPct, 4)).toFixed(1)}%` }}
              title={`Riêng tư: ${privPct.toFixed(2)}%`}
            />
          </div>

          <p className="text-[0.9rem] leading-[1.6] text-[#334155]">
            <strong className="text-[#C2410C] font-mono-tech">
              {m.public_edges.toLocaleString('vi-VN')} cạnh công khai ({pubPct.toFixed(1)}%)
            </strong>{' '}
            trên Server ({m.e_job_occ.toLocaleString('vi-VN')} tin–nghề + {m.e_occ_skill.toLocaleString('vi-VN')} nghề–kỹ năng) ·{' '}
            <strong className="text-[#0F172A] font-mono-tech">
              {m.private_edges.toLocaleString('vi-VN')} cạnh riêng tư ({privPct.toFixed(1)}%)
            </strong>{' '}
            khóa kín tại Client ({m.e_user_job.toLocaleString('vi-VN')} user–job + {m.e_user_occ.toLocaleString('vi-VN')} user–nghề).
          </p>
          <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-[#475569]">
            <Database size={13} className="text-[#EA580C] shrink-0" />
            <span>
              PostgreSQL <code className="font-mono-tech text-[#0F172A]">dss_jobs</code>:{' '}
              <strong className="font-mono-tech text-[#0F172A]">
                {(m.pg_job_skills / 1_000_000).toFixed(2)}M
              </strong>{' '}
              <code>job_skills</code> ·{' '}
              <strong className="font-mono-tech text-[#0F172A]">
                {(m.pg_user_skills / 1_000_000).toFixed(2)}M
              </strong>{' '}
              <code>user_skills</code>
            </span>
          </div>
        </GlassCard>
      </div>

      {/* 7-Model Benchmark Table (Global Universe + FL Universe) */}
      <GlassCard padding="md" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="kicker-label">ĐỐI CHIẾU 7 HỆ THỐNG GỢI Ý TRÊN CAREERBUILDER + O*NET (V3)</div>
            <h2 className="font-display text-lg font-bold text-[#0F172A]">
              Global Catalog (82.876 tin) vs FL Catalog ({fl.n_jobs_fl.toLocaleString('vi-VN')} tin)
            </h2>
          </div>
          <StatusBadge tone="slate">800 test users · CI 95%</StatusBadge>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 font-mono-tech uppercase text-[0.68rem] text-[#64748B]">
                <th className="py-2 pr-4">Mô hình</th>
                <th className="py-2 pr-4 text-right">Recall@20 (FL)</th>
                <th className="py-2 pr-4 text-right">Recall@20 (Toàn cục)</th>
                <th className="py-2 pr-4 text-right">NDCG@20</th>
                <th className="py-2 pr-4 text-right">MRR@20</th>
                <th className="py-2 text-right">Thời gian</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/70">
              {data.global_universe.map((row) => {
                const isFl = row.model === 'FedAvg';
                const isBest = row.model === 'LightGCN';
                return (
                  <tr
                    key={row.model}
                    className={
                      isFl
                        ? 'bg-[#FFF7ED]/85 font-semibold'
                        : isBest
                          ? 'bg-slate-50/90 font-semibold'
                          : 'hover:bg-slate-50/60'
                    }
                  >
                    <td className={`py-2.5 pr-4 ${isFl ? 'text-[#C2410C] font-bold' : 'text-[#0F172A]'}`}>
                      {row.model}
                    </td>
                    <td className={`py-2.5 pr-4 text-right font-mono-tech ${isFl ? 'text-[#C2410C] font-bold' : ''}`}>
                      {row.recall20_fl.toFixed(4)}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono-tech font-semibold text-[#0F172A]">
                      {row.recall20.toFixed(4)}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono-tech text-[#475569]">
                      {row.ndcg20.toFixed(4)}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-mono-tech text-[#475569]">
                      {row.mrr20.toFixed(4)}
                    </td>
                    <td className="py-2.5 text-right font-mono-tech text-[#64748B]">
                      {row.seconds.toFixed(1)}s
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* Collapsed Quick Guide */}
      <GlassExpander title="Cách xem bộ demo CareerBuilder + O*NET (V3)" badge="?">
        <ol className="list-decimal list-inside space-y-1.5 text-[0.88rem] text-[#334155]">
          <li>
            <Link to="/do-thi" className="font-semibold text-[#C2410C] hover:underline">
              Đồ thị việc làm
            </Link>{' '}
            — tương tác trực tiếp với đồ thị 4 thực thể (Người dùng · Tin · Nghề O*NET · Kỹ năng) và đường ranh giới Công khai / Riêng tư.
          </li>
          <li>
            <Link to="/lien-bang" className="font-semibold text-[#C2410C] hover:underline">
              Mô phỏng FL
            </Link>{' '}
            — theo dõi 5 kịch bản FedAvg (5 → 50 node), Ablation Study (15 variants) và Client Scaling.
          </li>
          <li>
            <Link to="/giam-sat-node" className="font-semibold text-[#C2410C] hover:underline">
              Giám sát node FL
            </Link>{' '}
            — phòng thí nghiệm trực tuyến theo dõi độ trễ p50/p95, Non-IID drift, dropout/compression và so sánh A/B run qua WebSocket.
          </li>
          <li>
            <Link to="/ket-luan" className="font-semibold text-[#C2410C] hover:underline">
              Kết luận &amp; hạn chế
            </Link>{' '}
            — bảng kiểm chứng 6 tiêu chí (5/6 Đạt), phân tích trung thực hạn chế V3 và lệnh tái lập.
          </li>
        </ol>
      </GlassExpander>
    </div>
  );
};
