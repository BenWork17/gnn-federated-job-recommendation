import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Copy,
  Check,
  ExternalLink,
  BookOpen,
} from 'lucide-react';
import { api, type ConclusionsResponse } from '../lib/api';
import {
  ErrorPanel,
  GlassCard,
  GlassExpander,
  LoadingPanel,
  PageHeader,
  StatusBadge,
} from '../components/ui/Primitives';

const VALID_ROUTES = new Set(['/', '/do-thi', '/lien-bang', '/giam-sat-node', '/ket-luan']);

export const ConclusionsPage: React.FC = () => {
  const [data, setData] = useState<ConclusionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.conclusions();
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Không tải được dữ liệu kết luận V3.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleCopy = async () => {
    if (!data?.reproducibility?.script) return;
    try {
      await navigator.clipboard.writeText(data.reproducibility.script);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // ignore clipboard restrictions
    }
  };

  if (loading) {
    return (
      <div className="space-y-5">
        <PageHeader
          kicker="05 // CONCLUSIONS & LIMITATIONS · V3"
          title="Kết luận và hạn chế"
          subtitle="Đối chiếu trung thực 6 tiêu chí trên CareerBuilder + O*NET (V3), các điểm đã đạt, hạn chế và hướng tái lập."
        />
        <LoadingPanel label="Đang tải bảng đối chiếu kết quả V3 từ /api/dashboard/conclusions..." />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-5">
        <PageHeader
          kicker="05 // CONCLUSIONS & LIMITATIONS · V3"
          title="Kết luận và hạn chế"
          subtitle="Đối chiếu trung thực từng yêu cầu của đề bài trên CareerBuilder + O*NET (V3)."
        />
        <ErrorPanel message={error ?? 'Không có dữ liệu.'} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        kicker="05 // CONCLUSIONS & LIMITATIONS · V3"
        title="Kết luận và hạn chế"
        subtitle="Đối chiếu trung thực từng yêu cầu của đề bài với số đo thực nghiệm CareerBuilder + O*NET (V3), ranh giới dữ liệu và các hạn chế còn tồn tại."
        actions={
          <StatusBadge tone="green">
            {data.summary.passed}/{data.summary.total} yêu cầu đạt · {data.summary.failed} chưa đạt
          </StatusBadge>
        }
      />

      {/* Full-Width 6-Row Verification Matrix */}
      <GlassCard padding="md" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="kicker-label">1. Ma trận kiểm chứng yêu cầu đề bài (V3)</div>
            <h2 className="font-display text-lg font-bold text-[#0F172A]">
              6 tiêu chí đánh giá thực đo trên CareerBuilder + O*NET
            </h2>
          </div>
          <span className="font-mono-tech text-xs text-[#64748B]">
            Mọi chỉ số đều kèm Evaluation Scope và benchmark protocol cụ thể
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-[0.84rem]">
            <thead>
              <tr className="border-b border-slate-200 font-mono-tech uppercase text-[0.68rem] text-[#64748B]">
                <th className="py-2.5 pr-4">Yêu cầu</th>
                <th className="py-2.5 pr-4">Cách đo</th>
                <th className="py-2.5 pr-4">Thực đo</th>
                <th className="py-2.5 pr-3 text-center">Kết luận</th>
                <th className="py-2.5 text-right">Bằng chứng</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/70">
              {data.matrix.map((row) => {
                const target = VALID_ROUTES.has(row.page) ? row.page : '/';
                return (
                  <tr key={row.requirement} className="hover:bg-[#FFF7ED]/45 transition-colors">
                    <td className="py-3 pr-4 font-semibold text-[#0F172A]">{row.requirement}</td>
                    <td className="py-3 pr-4 text-[#475569]">{row.method}</td>
                    <td className="py-3 pr-4 font-mono-tech text-xs font-semibold text-[#0F172A]">
                      {row.evidence}
                    </td>
                    <td className="py-3 pr-3 text-center whitespace-nowrap">
                      {row.passed ? (
                        <StatusBadge tone="green">
                          <CheckCircle2 size={12} /> {row.status}
                        </StatusBadge>
                      ) : (
                        <StatusBadge tone="red">
                          <XCircle size={12} /> {row.status}
                        </StatusBadge>
                      )}
                    </td>
                    <td className="py-3 text-right whitespace-nowrap">
                      <Link
                        to={target}
                        className="inline-flex items-center gap-1 font-mono-tech text-xs font-semibold text-[#C2410C] hover:underline"
                      >
                        <span>Xem</span>
                        <ExternalLink size={12} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* 2-Column Editorial Summary Glass Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        {/* Achievements */}
        <GlassCard padding="lg" className="space-y-3.5">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-2.5">
            <div>
              <div className="kicker-label">2. Điểm đã đạt</div>
              <h3 className="font-display text-lg font-bold text-[#0F172A]">Điều đã làm được</h3>
            </div>
            <CheckCircle2 size={18} className="text-emerald-600" />
          </div>

          <div className="space-y-3">
            {data.achievements.map((item) => (
              <div
                key={item.title}
                className="rounded-[10px] border border-emerald-200/80 border-l-4 border-l-[#10B981] bg-white/80 p-3.5"
              >
                <div className="font-semibold text-[0.9rem] text-[#0F172A]">{item.title}</div>
                <p className="text-[0.84rem] text-[#475569] mt-1 leading-relaxed">{item.detail}</p>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* Limitations */}
        <GlassCard padding="lg" className="space-y-3.5">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-2.5">
            <div>
              <div className="kicker-label">3. Hạn chế thực tế</div>
              <h3 className="font-display text-lg font-bold text-[#0F172A]">
                Điều chưa làm được — nói thẳng
              </h3>
            </div>
            <AlertTriangle size={18} className="text-amber-500" />
          </div>

          <div className="space-y-2.5">
            {data.limitations.map((item) => {
              const isBad = item.tone === 'bad';
              return (
                <div
                  key={item.title}
                  className={`rounded-[10px] border border-l-4 bg-white/80 p-3.5 ${
                    isBad
                      ? 'border-rose-200/80 border-l-[#EF4444]'
                      : 'border-amber-200/80 border-l-[#F59E0B]'
                  }`}
                >
                  <div className="font-semibold text-[0.9rem] text-[#0F172A]">{item.title}</div>
                  <p className="text-[0.84rem] text-[#475569] mt-1 leading-relaxed">{item.detail}</p>
                </div>
              );
            })}
          </div>
        </GlassCard>
      </div>

      {/* Lessons Learned */}
      {data.lessons?.length > 0 && (
        <GlassCard padding="md" className="space-y-3">
          <div className="flex items-center gap-2">
            <BookOpen size={15} className="text-[#EA580C]" />
            <span className="kicker-label">Bài học phương pháp trên V3</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.lessons.map((l) => (
              <div
                key={l.title}
                className="rounded-[10px] border border-slate-200/80 bg-white/80 p-3.5"
              >
                <div className="font-semibold text-sm text-[#0F172A]">{l.title}</div>
                <p className="text-xs text-[#475569] mt-1 leading-relaxed">{l.detail}</p>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Collapsed Accordions: Next Steps & Reproducibility */}
      <div className="space-y-3">
        <GlassExpander title="4. Hướng phát triển nếu có thêm thời gian" badge="ROADMAP">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 font-mono-tech uppercase text-[0.68rem] text-[#64748B]">
                  <th className="py-2 pr-4">Hướng cải tiến</th>
                  <th className="py-2 pr-4">Lý do kỹ thuật trên V3</th>
                  <th className="py-2 text-right">Ước lượng</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70">
                {data.next_steps.map((ns) => (
                  <tr key={ns.direction}>
                    <td className="py-2.5 pr-4 font-semibold text-[#0F172A]">{ns.direction}</td>
                    <td className="py-2.5 pr-4 text-[#475569]">{ns.reason}</td>
                    <td className="py-2.5 text-right font-mono-tech text-[#C2410C] font-semibold whitespace-nowrap">
                      {ns.estimate}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassExpander>

        <GlassExpander title="5. Cách tái lập toàn bộ dữ liệu V3, PostgreSQL & báo cáo" badge="CLI">
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-[#475569]">
                Chạy từ thư mục gốc đồ án để tái tạo artifacts V3, nạp PostgreSQL và chạy WebAPI + React:
              </span>
              <button type="button" onClick={handleCopy} className="btn-secondary py-1 px-2.5 text-xs">
                {copied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
                <span>{copied ? 'Đã sao chép' : 'Sao chép lệnh'}</span>
              </button>
            </div>
            <pre className="rounded-[10px] bg-[#0F172A] text-slate-100 p-4 text-xs font-mono-tech overflow-x-auto leading-relaxed">
              {data.reproducibility.script}
            </pre>
          </div>
        </GlassExpander>
      </div>
    </div>
  );
};
