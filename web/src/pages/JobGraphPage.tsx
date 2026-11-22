import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Search,
  Eye,
  Lock,
  Globe,
  X,
  Sparkles,
  GitBranch,
  Building2,
  Compass,
  PlusCircle,
  RotateCcw,
  Target,
} from 'lucide-react';
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

  // Chế độ đồ thị: 'silo' (mặc định — xem theo 9.116 Silo Nhà tuyển dụng) hoặc 'ego' (Tìm kiếm toàn bộ 264.995 nút & Ego-graph)
  const [graphMode, setGraphMode] = useState<'silo' | 'ego'>('silo');
  const [clientId, setClientId] = useState<number>(0);
  const [siloSearch, setSiloSearch] = useState('');
  const [debouncedSiloQ, setDebouncedSiloQ] = useState('');

  // Tham số Ego-graph (Hướng 2)
  const [centerId, setCenterId] = useState<string | null>(null);
  const [hops, setHops] = useState<1 | 2>(1);
  const [extraIds, setExtraIds] = useState<string[]>([]);

  // Tìm kiếm & bộ lọc
  const [search, setSearch] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [kindFilter, setKindFilter] = useState<'all' | 'user' | 'job' | 'skill' | 'occupation'>('all');
  const [nodeLimit, setNodeLimit] = useState<number>(430);
  const [viewMode, setViewMode] = useState<'3d' | '2d'>('2d');
  const [showPublic, setShowPublic] = useState(true);
  const [showPrivate, setShowPrivate] = useState(true);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [focusSeq, setFocusSeq] = useState<number>(0);
  const [mpActive, setMpActive] = useState(false);

  const selectAndFocusNode = useCallback((nid: string | null) => {
    setSelectedNodeId(nid);
    if (nid) {
      setFocusSeq((s) => s + 1);
    }
  }, []);

  // Reset message passing highlight when clearing selection
  useEffect(() => {
    if (!selectedNodeId) setMpActive(false);
  }, [selectedNodeId]);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedQ(search.trim()), 260);
    return () => window.clearTimeout(t);
  }, [search]);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSiloQ(siloSearch.trim()), 240);
    return () => window.clearTimeout(t);
  }, [siloSearch]);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await api.graph({
        mode: graphMode,
        client_id: clientId,
        center_id: graphMode === 'ego' ? centerId : undefined,
        hops,
        extra_ids: graphMode === 'ego' ? extraIds : undefined,
        silo_q: debouncedSiloQ || undefined,
        limit: nodeLimit,
        q: debouncedQ || undefined,
        kind: kindFilter === 'all' ? undefined : kindFilter,
      });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Không tải được đồ thị CareerBuilder + O*NET (V3).');
    } finally {
      setLoading(false);
    }
  }, [graphMode, clientId, centerId, hops, extraIds, debouncedSiloQ, nodeLimit, debouncedQ, kindFilter]);

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
    const inGraphHits = data.hit_ids.filter((id) => nodeMap.has(id));
    return inGraphHits.length > 0 ? inGraphHits : undefined;
  }, [data, debouncedQ, kindFilter, nodeMap]);

  const handleExpandNeighbors = (nid: string) => {
    if (graphMode !== 'ego') {
      // Nếu đang ở chế độ Silo mà bấm mở rộng/khám phá nút này -> chuyển sang Ego-graph quanh nút đó
      setGraphMode('ego');
      setCenterId(nid);
      setExtraIds([]);
      return;
    }
    if (!extraIds.includes(nid) && nid !== data?.ego_info?.center_id) {
      setExtraIds((prev) => [...prev, nid]);
    }
  };

  const handleSetEgoCenter = (nid: string) => {
    setGraphMode('ego');
    setCenterId(nid);
    setExtraIds([]);
    selectAndFocusNode(nid);
  };

  const siloInfo = data?.silo_info;
  const egoInfo = data?.ego_info;

  return (
    <div className="space-y-3.5">
      <PageHeader
        kicker="02 // CAREERBUILDER + O*NET V3 GRAPH (264.995 NÚT · 9.116 SILO)"
        title="Đồ thị việc làm"
        subtitle=""
      />

      {/* Mode Switcher + Context Controls */}
      <GlassCard padding="sm" className="space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-slate-200/75 pb-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono-tech text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
              Chế độ dữ liệu thật:
            </span>
            <button
              type="button"
              onClick={() => {
                setGraphMode('silo');
                setSelectedNodeId(null);
              }}
              className={`inline-flex items-center gap-1.5 rounded-[8px] border px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                graphMode === 'silo'
                  ? 'bg-[#FF5A1F] border-[#EA580C] text-white shadow-xs'
                  : 'bg-white border-slate-200 text-slate-700 hover:border-orange-300 hover:bg-[#FFF7ED]/70'
              }`}
            >
              <Building2 size={13} />
              <span>Silo Nhà tuyển dụng ({(data?.total_silos ?? 9116).toLocaleString('vi-VN')} silo)</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setGraphMode('ego');
              }}
              className={`inline-flex items-center gap-1.5 rounded-[8px] border px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                graphMode === 'ego'
                  ? 'bg-[#FF5A1F] border-[#EA580C] text-white shadow-xs'
                  : 'bg-white border-slate-200 text-slate-700 hover:border-orange-300 hover:bg-[#FFF7ED]/70'
              }`}
            >
              <Compass size={13} />
              <span>Tìm kiếm toàn bộ (264.995 nút) & Ego-graph</span>
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600">
              <span>Giới hạn vẽ:</span>
              <select
                value={nodeLimit}
                onChange={(e) => setNodeLimit(Number(e.target.value))}
                className="input-control text-xs font-semibold py-1"
              >
                <option value={250}>250 nút</option>
                <option value={430}>430 nút</option>
                <option value={650}>650 nút</option>
                <option value={900}>900 nút</option>
              </select>
            </label>

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
        </div>

        {/* Row 2: Mode-specific controls + Search */}
        <div className="flex flex-wrap items-center justify-between gap-2.5">
          {graphMode === 'silo' ? (
            <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[280px]">
              <div className="relative min-w-[180px] max-w-[230px]">
                <Building2
                  size={14}
                  className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[#64748B]"
                />
                <input
                  type="text"
                  value={siloSearch}
                  onChange={(e) => setSiloSearch(e.target.value)}
                  placeholder="Lọc 9.116 nhà tuyển dụng..."
                  style={{ paddingLeft: '2rem', paddingRight: '1.5rem' }}
                  className="input-control w-full text-xs"
                />
                {siloSearch && (
                  <button
                    type="button"
                    onClick={() => setSiloSearch('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 cursor-pointer"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>

              <select
                value={clientId}
                onChange={(e) => {
                  setClientId(Number(e.target.value));
                  setSelectedNodeId(null);
                }}
                aria-label="Chọn Silo Nhà tuyển dụng"
                className="input-control text-xs font-semibold min-w-[250px] max-w-[360px]"
              >
                {(data?.silos ?? []).map((s) => (
                  <option key={s.client_id} value={s.client_id}>
                    #{s.client_id} · {s.name} ({s.n_jobs} tin · {s.n_apps.toLocaleString('vi-VN')} đơn)
                  </option>
                ))}
              </select>

              <div className="relative flex-1 min-w-[180px] max-w-[280px]">
                <Search
                  size={14}
                  className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[#64748B]"
                />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Lọc nút trong silo này..."
                  style={{ paddingLeft: '2rem', paddingRight: '1.5rem' }}
                  className="input-control w-full text-xs"
                />
                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 cursor-pointer"
                  >
                    <X size={12} />
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
          ) : (
            <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[280px]">
              <div className="relative flex-1 min-w-[240px] max-w-[380px]">
                <Search
                  size={15}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#64748B]"
                />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Tìm trên toàn bộ 264.995 nút (Python, SAP, randstad, mã nghề, ID)..."
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
                <option value="all">Tất cả 264.995 nút</option>
                <option value="job">Tin tuyển dụng (84.845)</option>
                <option value="user">Người dùng (171.807)</option>
                <option value="occupation">Nghề O*NET (583)</option>
                <option value="skill">Kỹ năng (7.760)</option>
              </select>

              <div className="inline-flex items-center rounded-[8px] border border-slate-200 bg-white p-0.5 text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setHops(1)}
                  className={`rounded-[6px] px-2.5 py-1 transition-colors cursor-pointer ${
                    hops === 1 ? 'bg-[#FFF7ED] text-[#C2410C] border border-[#FDBA74]' : 'text-slate-600'
                  }`}
                >
                  1-Hop
                </button>
                <button
                  type="button"
                  onClick={() => setHops(2)}
                  className={`rounded-[6px] px-2.5 py-1 transition-colors cursor-pointer ${
                    hops === 2 ? 'bg-[#FFF7ED] text-[#C2410C] border border-[#FDBA74]' : 'text-slate-600'
                  }`}
                >
                  2-Hop
                </button>
              </div>

              {extraIds.length > 0 && (
                <button
                  type="button"
                  onClick={() => setExtraIds([])}
                  className="inline-flex items-center gap-1 rounded-[8px] border border-orange-200 bg-[#FFF7ED] px-2.5 py-1.5 text-xs font-semibold text-[#C2410C] hover:border-[#FF5A1F] cursor-pointer"
                >
                  <RotateCcw size={12} />
                  <span>Xoá {extraIds.length} nút mở rộng</span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Context Summary Strip */}
        {data && (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs text-slate-600">
            {graphMode === 'silo' && siloInfo ? (
              <div>
                Silo <b className="text-[#0F172A]">{siloInfo.name}</b> (#{siloInfo.client_id}):{' '}
                <b>{siloInfo.n_jobs.toLocaleString('vi-VN')}</b> tin ·{' '}
                <b>{siloInfo.n_users.toLocaleString('vi-VN')}</b> ứng viên ·{' '}
                <b>{siloInfo.n_occs.toLocaleString('vi-VN')}</b> nghề O*NET ·{' '}
                <b>{siloInfo.n_skills.toLocaleString('vi-VN')}</b> kỹ năng — đang vẽ{' '}
                <b className="text-[#C2410C]">
                  {data.summary.sampled_nodes.toLocaleString('vi-VN')} / {siloInfo.n_nodes.toLocaleString('vi-VN')} nút
                </b>{' '}
                ({data.summary.sampled_edges.toLocaleString('vi-VN')} / {siloInfo.n_edges.toLocaleString('vi-VN')} cạnh).
              </div>
            ) : egoInfo ? (
              <div>
                Ego-graph <b>{egoInfo.hops}-Hop</b> quanh tâm{' '}
                <b className="text-[#0F172A]">{egoInfo.center_label}</b> ({egoInfo.center_kind_label}
                {egoInfo.extra_ids.length > 0 ? ` · +${egoInfo.extra_ids.length} nút mở rộng` : ''}) — đang vẽ{' '}
                <b className="text-[#C2410C]">
                  {data.summary.sampled_nodes.toLocaleString('vi-VN')} /{' '}
                  {egoInfo.total_unfiltered_nodes.toLocaleString('vi-VN')} nút lân cận
                </b>{' '}
                ({data.summary.sampled_edges.toLocaleString('vi-VN')} cạnh).
              </div>
            ) : null}
          </div>
        )}
      </GlassCard>

      {error && <ErrorPanel message={error} onRetry={load} />}
      {loading && !data && (
        <LoadingPanel label="Đang trích xuất đồ thị thật từ CareerBuilder + O*NET (V3 — 264.995 nút)..." />
      )}

      {data && (
        <>
          {/* Main Graph Stage + Right Glass Node Inspector */}
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
                focusSeq={focusSeq}
                messagePassingActive={mpActive}
                hop1Ids={hop1Ids}
                hop2Ids={hop2Ids}
                onSelectNode={(n) => selectAndFocusNode(n ? n.id : null)}
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

                  {/* Quick Actions: Expand Neighbors & Set Ego Center */}
                  <div className="flex flex-wrap gap-1.5">
                    <button
                      type="button"
                      onClick={() => handleExpandNeighbors(selectedNode.id)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-orange-300 bg-[#FFF7ED] px-2.5 py-1.5 text-xs font-semibold text-[#C2410C] hover:bg-orange-100/80 cursor-pointer"
                    >
                      <PlusCircle size={13} />
                      <span>Mở rộng láng giềng (1-Hop)</span>
                    </button>
                    {(!egoInfo || egoInfo.center_id !== selectedNode.id) && (
                      <button
                        type="button"
                        onClick={() => handleSetEgoCenter(selectedNode.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:border-orange-300 hover:text-[#C2410C] cursor-pointer"
                      >
                        <Target size={13} />
                        <span>Đặt làm tâm Ego-graph</span>
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="rounded-lg bg-white/85 border border-slate-200/80 p-2.5">
                      <div className="font-mono-tech text-[0.65rem] text-[#64748B] uppercase">
                        Bậc đang vẽ / Toàn V3
                      </div>
                      <div className="font-display text-base font-bold tabular-nums">
                        {selectedNode.degree}
                        {selectedNode.global_degree !== undefined && (
                          <span className="text-xs font-normal text-slate-500">
                            {' '}
                            / {selectedNode.global_degree.toLocaleString('vi-VN')}
                          </span>
                        )}
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
                                  onClick={() => selectAndFocusNode(h2.id)}
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
                      Láng giềng trực tiếp ({neighbors.length})
                    </div>
                    <div className="space-y-1.5 max-h-[210px] overflow-y-auto pr-1">
                      {neighbors.slice(0, 30).map(({ node, isPublic, edgeLabel }) => (
                        <button
                          key={`${node.id}-${edgeLabel}`}
                          type="button"
                          onClick={() => selectAndFocusNode(node.id)}
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
                      <Sparkles size={13} />{' '}
                      {graphMode === 'silo'
                        ? 'Khám phá dữ liệu thật theo Silo Nhà tuyển dụng'
                        : 'Tìm kiếm toàn bộ 264.995 nút & vẽ Ego-graph'}
                    </div>
                    {graphMode === 'silo'
                      ? 'Chọn 1 trong 9.116 nhà tuyển dụng ở trên để xem toàn bộ Tin tuyển dụng thật của silo đó cùng các Ứng viên (cạnh Riêng tư) và Nghề O*NET / Kỹ năng (cạnh Công khai).'
                      : 'Gõ tên nghề, kỹ năng (Python, SAP), tiêu đề việc làm, nhà tuyển dụng hoặc ID ứng viên để tìm trên toàn bộ 264.995 nút; bấm một kết quả để đặt làm tâm Ego-graph 1–2 Hop.'}
                  </div>

                  {data.hits.length > 0 ? (
                    <div className="space-y-1.5">
                      <div className="font-mono-tech text-[0.68rem] uppercase text-[#64748B] font-semibold">
                        {graphMode === 'ego'
                          ? `Kết quả tìm kiếm toàn đồ thị (${data.hits.length})`
                          : `Kết quả khớp trong silo (${data.hits.length})`}
                      </div>
                      {data.hits.slice(0, 16).map((h) => (
                        <button
                          key={h.id}
                          type="button"
                          onClick={() => {
                            if (graphMode === 'ego' && !nodeMap.has(h.id)) {
                              handleSetEgoCenter(h.id);
                            } else {
                              selectAndFocusNode(h.id);
                            }
                          }}
                          className="w-full flex items-center justify-between gap-2 rounded-lg border border-slate-200/80 bg-white/85 hover:border-[#FDBA74] px-2.5 py-2 text-left cursor-pointer transition-colors"
                        >
                          <div className="min-w-0">
                            <div className="text-xs font-semibold text-[#0F172A] truncate">
                              {h.label}
                            </div>
                            <div className="font-mono-tech text-[0.68rem] text-[#64748B]">
                              {h.kind_label} · deg {h.degree.toLocaleString('vi-VN')}
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
                        Nút tiêu biểu trong khung hình
                      </div>
                      {data.nodes.slice(0, 8).map((n) => (
                        <button
                          key={n.id}
                          type="button"
                          onClick={() => selectAndFocusNode(n.id)}
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
              kicker={
                graphMode === 'silo' && siloInfo
                  ? `Nút Silo #${siloInfo.client_id} (${siloInfo.name})`
                  : 'Nút Ego-graph / Toàn V3'
              }
              value={
                graphMode === 'silo' && siloInfo
                  ? `${siloInfo.n_nodes.toLocaleString('vi-VN')} nút`
                  : egoInfo
                    ? `${egoInfo.total_unfiltered_nodes.toLocaleString('vi-VN')} nút`
                    : `${data.summary.total_nodes.toLocaleString('vi-VN')} nút`
              }
              sub={`Đang vẽ ${data.summary.sampled_nodes.toLocaleString('vi-VN')} nút · Toàn V3: ${data.summary.total_nodes.toLocaleString('vi-VN')} nút`}
            />
            <StatTile
              kicker="Cạnh công khai (Server)"
              accent="orange"
              value={
                graphMode === 'silo' && siloInfo
                  ? siloInfo.n_public.toLocaleString('vi-VN')
                  : data.summary.sampled_public_edges.toLocaleString('vi-VN')
              }
              sub={`Toàn V3: ${data.summary.public_edges.toLocaleString('vi-VN')} cạnh (Tin–Nghề & Nghề–KN)`}
            />
            <StatTile
              kicker="Cạnh riêng tư (Client Silo)"
              accent="ink"
              value={
                graphMode === 'silo' && siloInfo
                  ? siloInfo.n_private.toLocaleString('vi-VN')
                  : data.summary.sampled_private_edges.toLocaleString('vi-VN')
              }
              sub={`Toàn V3: ${data.summary.private_edges.toLocaleString('vi-VN')} cạnh (Ứng tuyển & Hồ sơ)`}
            />
            <StatTile
              kicker="Cấu trúc thực thể đang xem"
              accent="sky"
              value={
                graphMode === 'silo' && siloInfo
                  ? `${siloInfo.n_occs} nghề · ${siloInfo.n_skills.toLocaleString('vi-VN')} KN`
                  : `${data.summary.kind_counts.occupation} nghề · ${data.summary.kind_counts.skill} KN`
              }
              sub={
                graphMode === 'silo' && siloInfo
                  ? `${siloInfo.n_jobs.toLocaleString('vi-VN')} tin · ${siloInfo.n_users.toLocaleString('vi-VN')} ứng viên (Silo)`
                  : `${data.summary.kind_counts.job} tin · ${data.summary.kind_counts.user} ứng viên`
              }
            />
          </div>
        </>
      )}
    </div>
  );
};
