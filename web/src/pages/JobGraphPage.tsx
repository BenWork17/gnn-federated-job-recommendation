import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Search, Eye, Lock, Globe, X, Sparkles, GitBranch } from 'lucide-react';
import { api, type GraphNodeRich, type GraphResponse } from '../lib/api';
import { JobGraphExplorer3D } from '../components/three';
import type { GraphNode3D } from '../components/three/types';
import {
  ErrorPanel,
  GlassCard,
  LoadingPanel,
  PageHeader,
  SegmentedTabs,
  StatTile,
  StatusBadge,
} from '../components/ui/Primitives';

const KIND_BADGE_COLOR: Record<GraphNode3D['kind'], { bg: string; dot: string; label: string }> = {
  user: { bg: 'bg-rose-50 text-rose-800 border-rose-200', dot: 'bg-[#7B241C]', label: 'Người dùng' },
  job: { bg: 'bg-[#FFF7ED] text-[#C2410C] border-[#FED7AA]', dot: 'bg-[#e8836b]', label: 'Tin tuyển dụng' },
  skill: { bg: 'bg-sky-50 text-sky-800 border-sky-200', dot: 'bg-[#0EA5E9]', label: 'Kỹ năng' },
  occupation: { bg: 'bg-emerald-50 text-emerald-800 border-emerald-200', dot: 'bg-[#10B981]', label: 'Nghề O*NET' },
};

export const JobGraphPage: React.FC = () => {
  const [data, setData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [kindFilter, setKindFilter] = useState<'all' | 'user' | 'job' | 'skill' | 'occupation'>('all');
  const [viewMode, setViewMode] = useState<'3d' | '2d'>('2d');
  const [showPublic, setShowPublic] = useState(true);
  const [showPrivate, setShowPrivate] = useState(true);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [mpActive, setMpActive] = useState(false);

  // Reset message passing highlight when clearing selection
  useEffect(() => {
    if (!selectedNodeId) setMpActive(false);
  }, [selectedNodeId]);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedQ(search.trim()), 260);
    return () => window.clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await api.graph({
        limit: 430,
        q: debouncedQ || undefined,
        kind: kindFilter === 'all' ? undefined : kindFilter,
      });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Không tải được đồ thị CareerBuilder + O*NET (V3).');
    } finally {
      setLoading(false);
    }
  }, [debouncedQ, kindFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const nodeMap = useMemo(() => {
    const m = new Map<string, GraphNodeRich>();
    data?.nodes.forEach((n) => m.set(n.id, n));
    return m;
  }, [data]);

  const selectedNode = useMemo(
    () => (selectedNodeId ? nodeMap.get(selectedNodeId) ?? null : null),
    [nodeMap, selectedNodeId]
  );

  const neighbors = useMemo(() => {
    if (!selectedNode || !data) return [];
    const list: Array<{ node: GraphNodeRich; isPublic: boolean; edgeLabel: string }> = [];
    for (const e of data.edges) {
      if (e.source === selectedNode.id) {
        const other = nodeMap.get(e.target);
        if (other) list.push({ node: other, isPublic: e.is_public, edgeLabel: e.edge_label });
      } else if (e.target === selectedNode.id) {
        const other = nodeMap.get(e.source);
        if (other) list.push({ node: other, isPublic: e.is_public, edgeLabel: e.edge_label });
      }
    }
    return list.sort((a, b) => Number(a.isPublic) - Number(b.isPublic));
  }, [data, nodeMap, selectedNode]);

  // Compute 1-Hop and 2-Hop LightGCN Ego-Subgraph around selectedNode
  const { hop1Ids, hop2Nodes, hop2Ids } = useMemo(() => {
    if (!selectedNode || !data) {
      return { hop1Ids: [] as string[], hop2Nodes: [] as GraphNodeRich[], hop2Ids: [] as string[] };
    }
    const h1 = new Set<string>(neighbors.map((n) => n.node.id));
    const h2 = new Set<string>();
    for (const e of data.edges) {
      if (h1.has(e.source) && e.target !== selectedNode.id && !h1.has(e.target)) {
        h2.add(e.target);
      } else if (h1.has(e.target) && e.source !== selectedNode.id && !h1.has(e.source)) {
        h2.add(e.source);
      }
    }
    const h2List = Array.from(h2)
      .map((id) => nodeMap.get(id))
      .filter((n): n is GraphNodeRich => Boolean(n))
      .sort((a, b) => b.degree - a.degree);
    return {
      hop1Ids: Array.from(h1),
      hop2Nodes: h2List,
      hop2Ids: h2List.map((n) => n.id),
    };
  }, [selectedNode, data, neighbors, nodeMap]);

  const highlightIds = useMemo(() => {
    if (!data) return undefined;
    if (!debouncedQ && kindFilter === 'all') return undefined;
    return data.hit_ids;
  }, [data, debouncedQ, kindFilter]);

  return (
    <div className="space-y-3.5">
      <PageHeader
        kicker="02 // CAREERBUILDER + O*NET V3 GRAPH"
        title="Đồ thị việc làm"
        subtitle=""
      />

      {/* Single-Row Interactive Toolbar */}
      <GlassCard padding="sm" className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-[260px]">
          <div className="relative flex-1 min-w-[200px] max-w-[340px]">
            <Search
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#64748B]"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm tin, ứng viên, nghề O*NET, kỹ năng..."
              style={{ paddingLeft: '2.25rem', paddingRight: '2rem' }}
              className="input-control w-full text-xs"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X size={13} />
              </button>
            )}
          </div>

          <select
            value={kindFilter}
            onChange={(e) => setKindFilter(e.target.value as typeof kindFilter)}
            className="input-control text-xs font-semibold"
          >
            <option value="all">Tất cả loại nút</option>
            <option value="job">Tin tuyển dụng</option>
            <option value="user">Người dùng (Client)</option>
            <option value="occupation">Nghề O*NET</option>
            <option value="skill">Kỹ năng</option>
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setShowPublic((v) => !v)}
            className={`inline-flex items-center gap-1.5 rounded-[8px] border px-2.5 py-1.5 text-xs font-semibold transition-colors cursor-pointer ${
              showPublic
                ? 'bg-[#FFF7ED] border-[#FDBA74] text-[#C2410C]'
                : 'bg-white border-slate-200 text-slate-500'
            }`}
          >
            <Globe size={13} />
            <span>Công khai</span>
          </button>

          <button
            type="button"
            onClick={() => setShowPrivate((v) => !v)}
            className={`inline-flex items-center gap-1.5 rounded-[8px] border px-2.5 py-1.5 text-xs font-semibold transition-colors cursor-pointer ${
              showPrivate
                ? 'bg-rose-50 border-rose-300 text-rose-700'
                : 'bg-white border-slate-200 text-slate-500'
            }`}
          >
            <Lock size={13} />
            <span>Riêng tư</span>
          </button>

          <SegmentedTabs
            layoutId="graph-dim-tabs"
            size="sm"
            value={viewMode}
            onChange={setViewMode}
            options={[
              { id: '2d', label: '2D Phẳng' },
              { id: '3d', label: '3D WebGL' },
            ]}
          />
        </div>
      </GlassCard>

      {error && <ErrorPanel message={error} onRetry={load} />}
      {loading && !data && <LoadingPanel label="Đang dựng đồ thị con 430 nút CareerBuilder + O*NET (V3)..." />}

      {data && (
        <>
          {/* Main Graph Stage + Right Glass Node Inspector (locked height, 100% above the fold) */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-stretch">
            <GlassCard
              padding="none"
              sheen={false}
              className="xl:col-span-8 overflow-hidden h-[540px] relative"
            >
              <JobGraphExplorer3D
                nodes={data.nodes}
                edges={data.edges}
                mode={viewMode}
                showPublic={showPublic}
                showPrivate={showPrivate}
                highlightIds={highlightIds}
                selectedNodeId={selectedNodeId}
                messagePassingActive={mpActive}
                hop1Ids={hop1Ids}
                hop2Ids={hop2Ids}
                onSelectNode={(n) => setSelectedNodeId(n ? n.id : null)}
                className="w-full h-full"
              />
            </GlassCard>

            {/* Right Glass Inspector Drawer */}
            <GlassCard padding="md" className="xl:col-span-4 flex flex-col gap-3.5 h-[540px]">
              <div className="flex items-center justify-between border-b border-slate-200/80 pb-2.5">
                <span className="kicker-label flex items-center gap-1.5">
                  <Eye size={13} /> Node Inspector
                </span>
                {selectedNode && (
                  <button
                    type="button"
                    onClick={() => setSelectedNodeId(null)}
                    className="text-xs font-semibold text-[#64748B] hover:text-[#0F172A] cursor-pointer"
                  >
                    Bỏ chọn
                  </button>
                )}
              </div>

              {selectedNode ? (
                <div className="flex-1 overflow-y-auto space-y-3.5 pr-1">
                  <div>
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[0.72rem] font-semibold ${
                        KIND_BADGE_COLOR[selectedNode.kind].bg
                      }`}
                    >
                      <span
                        className={`h-2 w-2 rounded-full ${KIND_BADGE_COLOR[selectedNode.kind].dot}`}
                      />
                      {selectedNode.kind_label}
                    </span>
                    <h3 className="font-display text-lg font-bold text-[#0F172A] mt-2 leading-snug">
                      {selectedNode.label}
                    </h3>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="rounded-lg bg-white/85 border border-slate-200/80 p-2.5">
                      <div className="font-mono-tech text-[0.65rem] text-[#64748B] uppercase">
                        Degree (mẫu)
                      </div>
                      <div className="font-display text-base font-bold tabular-nums">
                        {selectedNode.degree}
                      </div>
                    </div>
                    <div className="rounded-lg bg-white/85 border border-slate-200/80 p-2.5">
                      <div className="font-mono-tech text-[0.65rem] text-[#64748B] uppercase">
                        Phạm vi lưu trữ
                      </div>
                      <div className="text-xs font-bold mt-1 text-[#0F172A]">
                        {selectedNode.kind === 'user' ? 'Riêng tư (Client)' : 'Công khai (Server)'}
                      </div>
                    </div>
                  </div>

                  {/* Interactive 2-Hop LightGCN Message Passing Explainer */}
                  <div className="rounded-xl border border-orange-200/80 bg-[#FFF7ED]/70 p-2.5 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono-tech text-[0.68rem] font-bold uppercase tracking-wider text-[#C2410C] flex items-center gap-1.5">
                        <GitBranch size={12} /> LightGCN 2-Hop Explainer
                      </span>
                      <button
                        type="button"
                        onClick={() => setMpActive((v) => !v)}
                        className={`inline-flex cursor-pointer items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold transition-all ${
                          mpActive
                            ? 'bg-[#FF5A1F] text-white shadow-xs'
                            : 'bg-white text-[#C2410C] border border-orange-300 hover:bg-orange-50'
                        }`}
                      >
                        <span>{mpActive ? 'Đang phát 2-Hop' : '▶ Minh họa 2-Hop'}</span>
                      </button>
                    </div>
                    <div className="text-[11px] leading-snug text-[#7C2D12]">
                      <b>Layer 1 ({hop1Ids.length})</b> → <b>Layer 2 ({hop2Ids.length} nodes)</b> lan truyền qua Public Backbone (O*NET Occupation / Skill).
                    </div>
                    {mpActive && (
                      <div className="space-y-1.5 pt-1 border-t border-orange-200/70">
                        <div className="font-mono-tech text-[10px] text-slate-700 bg-white/85 rounded px-2 py-1 border border-orange-100">
                          eᵢ⁽ᵏ⁺¹⁾ = Σⱼ∈N(i) eⱼ⁽ᵏ⁾ / √(|N(i)|·|N(j)|)
                        </div>
                        {hop2Nodes.length > 0 && (
                          <div>
                            <div className="font-mono-tech text-[10px] font-semibold uppercase text-[#C2410C] mb-1">
                              Nút 2-Hop tiếp cận được ({hop2Nodes.length})
                            </div>
                            <div className="flex flex-wrap gap-1 max-h-[68px] overflow-y-auto">
                              {hop2Nodes.slice(0, 10).map((h2) => (
                                <button
                                  key={h2.id}
                                  type="button"
                                  onClick={() => setSelectedNodeId(h2.id)}
                                  className="inline-flex items-center gap-1 rounded-md border border-orange-200 bg-white/90 px-1.5 py-0.5 text-[10px] font-medium text-slate-800 hover:border-[#FF5A1F] cursor-pointer max-w-[140px]"
                                >
                                  <span
                                    className={`h-1.5 w-1.5 rounded-full shrink-0 ${
                                      KIND_BADGE_COLOR[h2.kind].dot
                                    }`}
                                  />
                                  <span className="truncate">{h2.label}</span>
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="font-mono-tech text-[0.68rem] uppercase text-[#64748B] font-semibold mb-1.5">
                      Neighbors ({neighbors.length})
                    </div>
                    <div className="space-y-1.5 max-h-[210px] overflow-y-auto pr-1">
                      {neighbors.slice(0, 30).map(({ node, isPublic, edgeLabel }) => (
                        <button
                          key={`${node.id}-${edgeLabel}`}
                          type="button"
                          onClick={() => setSelectedNodeId(node.id)}
                          className="w-full flex items-center justify-between gap-2 rounded-lg border border-slate-200/80 bg-white/80 hover:border-[#FDBA74] px-2.5 py-1.5 text-left transition-colors cursor-pointer"
                        >
                          <div className="min-w-0 flex items-center gap-2">
                            <span
                              className={`h-2 w-2 rounded-full shrink-0 ${
                                KIND_BADGE_COLOR[node.kind].dot
                              }`}
                            />
                            <span className="text-xs font-medium text-[#0F172A] truncate">
                              {node.label}
                            </span>
                          </div>
                          <StatusBadge tone={isPublic ? 'orange' : 'red'} className="shrink-0">
                            {isPublic ? 'Công khai' : 'Riêng tư'}
                          </StatusBadge>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col gap-3 overflow-y-auto">
                  <div className="rounded-lg bg-[#FFF7ED]/70 border border-[#FED7AA] p-3 text-xs leading-relaxed text-[#7C2D12]">
                    <div className="font-semibold flex items-center gap-1.5 mb-1">
                      <Sparkles size={13} /> Nhấp vào bất kỳ nút nào trên đồ thị
                    </div>
                    Kéo để di chuyển, cuộn để phóng to, hoặc lọc theo Nghề O*NET / Kỹ năng để kiểm chứng đường ranh giới Công khai vs Riêng tư.
                  </div>

                  {data.hits.length > 0 ? (
                    <div className="space-y-1.5">
                      <div className="font-mono-tech text-[0.68rem] uppercase text-[#64748B] font-semibold">
                        Kết quả khớp ({data.hits.length})
                      </div>
                      {data.hits.slice(0, 14).map((h) => (
                        <button
                          key={h.id}
                          type="button"
                          onClick={() => setSelectedNodeId(h.id)}
                          className="w-full flex items-center justify-between gap-2 rounded-lg border border-slate-200/80 bg-white/85 hover:border-[#FDBA74] px-2.5 py-2 text-left cursor-pointer transition-colors"
                        >
                          <div className="min-w-0">
                            <div className="text-xs font-semibold text-[#0F172A] truncate">
                              {h.label}
                            </div>
                            <div className="font-mono-tech text-[0.68rem] text-[#64748B]">
                              {h.kind_label} · deg {h.degree}
                            </div>
                          </div>
                          <span
                            className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                              KIND_BADGE_COLOR[h.kind].dot
                            }`}
                          />
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-2 pt-1">
                      <div className="font-mono-tech text-[0.68rem] uppercase text-[#64748B] font-semibold">
                        Gợi ý nút tiêu biểu
                      </div>
                      {data.nodes.slice(0, 8).map((n) => (
                        <button
                          key={n.id}
                          type="button"
                          onClick={() => setSelectedNodeId(n.id)}
                          className="w-full flex items-center justify-between gap-2 rounded-lg border border-slate-200/75 bg-white/80 hover:border-[#FDBA74] px-2.5 py-1.5 text-left cursor-pointer"
                        >
                          <span className="text-xs font-medium text-[#0F172A] truncate">
                            {n.label}
                          </span>
                          <span className="font-mono-tech text-[0.68rem] text-[#64748B] shrink-0">
                            deg {n.degree}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </GlassCard>
          </div>

          {/* 4 Compact V3 Stat Tiles below the main graph stage */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatTile
              kicker="Tổng số nút V3"
              value={`${data.summary.total_nodes.toLocaleString('vi-VN')} nút`}
              sub={`Hiển thị mẫu ${data.summary.sampled_nodes} nút (${data.summary.sampled_edges.toLocaleString('vi-VN')} cạnh)`}
            />
            <StatTile
              kicker="Cạnh công khai (Server)"
              accent="orange"
              value={data.summary.public_edges.toLocaleString('vi-VN')}
              sub="Tin – Nghề O*NET & Nghề – Kỹ năng"
            />
            <StatTile
              kicker="Cạnh riêng tư (Client)"
              accent="ink"
              value={data.summary.private_edges.toLocaleString('vi-VN')}
              sub="Ứng viên – Tin & Ứng viên – Nghề"
            />
            <StatTile
              kicker="O*NET Taxonomy"
              accent="sky"
              value={`${data.summary.n_occupations.toLocaleString('vi-VN')} nghề · ${data.summary.n_skills.toLocaleString('vi-VN')} KN`}
              sub={`${data.summary.n_jobs.toLocaleString('vi-VN')} tin · ${data.summary.n_users.toLocaleString('vi-VN')} ứng viên`}
            />
          </div>
        </>
      )}
    </div>
  );
};
