import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Maximize2, RotateCcw } from 'lucide-react';
import type { GraphNode3D, JobGraphExplorer3DProps } from './types';

declare global {
  interface Window {
    ForceGraph?: () => (el: HTMLElement) => any;
    ForceGraph3D?: () => (el: HTMLElement) => any;
  }
}

// Palette for CareerBuilder + O*NET (V3) interactive graph (White + Orange design system)
const KIND_COLOR: Record<GraphNode3D['kind'], string> = {
  user: '#7b241c',
  job: '#e8836b',
  skill: '#0EA5E9',
  occupation: '#10B981',
};

const KIND_LABEL: Record<GraphNode3D['kind'], string> = {
  user: 'Người dùng',
  job: 'Tin tuyển dụng',
  skill: 'Kỹ năng',
  occupation: 'Nghề O*NET',
};

const EDGE_PUBLIC_COLOR = '#F97316';
const EDGE_PRIVATE_COLOR = '#EF4444';

function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace('#', '');
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

const scriptCache = new Map<string, Promise<void>>();

function loadVendorScript(src: string): Promise<void> {
  const existing = scriptCache.get(src);
  if (existing) return existing;
  const p = new Promise<void>((resolve, reject) => {
    const el = document.createElement('script');
    el.src = src;
    el.async = true;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error(`Không tải được thư viện đồ thị: ${src}`));
    document.head.appendChild(el);
  });
  scriptCache.set(src, p);
  return p;
}

function getLinkEndpointId(v: any): string {
  return v && typeof v === 'object' ? String(v.id) : String(v);
}

interface FGNode extends GraphNode3D {
  color: string;
  fx?: number;
  fy?: number;
}

interface FGLink {
  source: string | FGNode;
  target: string | FGNode;
  edge_type: string;
  is_public: boolean;
  color: string;
  alpha: number;
  width: number;
}

export const JobGraphExplorer3D: React.FC<JobGraphExplorer3DProps> = ({
  nodes,
  edges,
  mode,
  showPublic,
  showPrivate,
  highlightIds,
  selectedNodeId,
  messagePassingActive = false,
  hop1Ids,
  hop2Ids,
  onSelectNode,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<any>(null);
  const [libError, setLibError] = useState<string | null>(null);
  const [hoveredInfo, setHoveredInfo] = useState<{ node: GraphNode3D } | null>(null);

  // Refs synced with latest React props so callbacks & canvas paint always read fresh state
  const hoveredIdRef = useRef<string | null>(null);
  const selectedIdRef = useRef<string | null>(selectedNodeId ?? null);
  const mpActiveRef = useRef<boolean>(messagePassingActive);
  const hop1SetRef = useRef<Set<string>>(new Set(hop1Ids ?? []));
  const hop2SetRef = useRef<Set<string>>(new Set(hop2Ids ?? []));
  const highlightSetRef = useRef<Set<string>>(new Set());
  const highlightFocusSetRef = useRef<Set<string>>(new Set());
  const adjRef = useRef<Map<string, Set<string>>>(new Map());
  const nodeByIdRef = useRef<Map<string, GraphNode3D>>(new Map());
  const onSelectRef = useRef(onSelectNode);
  onSelectRef.current = onSelectNode;

  // Compute filtered edges and adjacency map
  const filteredEdges = useMemo(() => {
    const idSet = new Set(nodes.map((n) => n.id));
    return edges.filter((e) => {
      if (!idSet.has(e.source) || !idSet.has(e.target)) return false;
      if (e.is_public && !showPublic) return false;
      if (!e.is_public && !showPrivate) return false;
      return true;
    });
  }, [nodes, edges, showPublic, showPrivate]);

  const maxDegree = useMemo(() => {
    let m = 1;
    for (const n of nodes) {
      if (n.degree > m) m = n.degree;
    }
    return m;
  }, [nodes]);
  const maxDegRef = useRef(maxDegree);
  maxDegRef.current = maxDegree;

  // Keep lookup & highlight sets synchronized
  useEffect(() => {
    const byId = new Map<string, GraphNode3D>();
    for (const n of nodes) byId.set(n.id, n);
    nodeByIdRef.current = byId;

    const adj = new Map<string, Set<string>>();
    for (const n of nodes) adj.set(n.id, new Set());
    for (const e of filteredEdges) {
      adj.get(e.source)?.add(e.target);
      adj.get(e.target)?.add(e.source);
    }
    adjRef.current = adj;

    const hl = new Set<string>(highlightIds ?? []);
    highlightSetRef.current = hl;
    const hlFocus = new Set<string>(hl);
    if (hl.size > 0) {
      for (const id of hl) {
        const nbrs = adj.get(id);
        if (nbrs) nbrs.forEach((nb) => hlFocus.add(nb));
      }
    }
    highlightFocusSetRef.current = hlFocus;
  }, [nodes, filteredEdges, highlightIds]);

  // Sync external selectedNodeId & 2-Hop Message Passing sets into refs
  useEffect(() => {
    selectedIdRef.current = selectedNodeId ?? null;
    mpActiveRef.current = Boolean(messagePassingActive && selectedNodeId);
    hop1SetRef.current = new Set(hop1Ids ?? []);
    hop2SetRef.current = new Set(hop2Ids ?? []);
    const g = graphRef.current;
    if (!g) return;
    try {
      if (typeof g.linkDirectionalParticles === 'function') {
        g.linkDirectionalParticles(g.linkDirectionalParticles());
      }
      if (mode === '3d') {
        g.nodeColor(g.nodeColor());
        g.linkColor(g.linkColor());
      }
    } catch {
      // ignore if tearing down
    }
  }, [selectedNodeId, highlightIds, messagePassingActive, hop1Ids, hop2Ids, mode]);

  // Mount & configure ForceGraph (2D) or ForceGraph3D (3D)
  useEffect(() => {
    const host = containerRef.current;
    if (!host) return;
    let disposed = false;
    let ro: ResizeObserver | null = null;
    let fitTimer: number | null = null;

    const radiusFor = (n: { degree: number }) => {
      const ratio = Math.sqrt(Math.max(1, n.degree)) / Math.sqrt(Math.max(1, maxDegRef.current));
      return 3.4 + ratio * 7.8;
    };

    const getFocusId = () => hoveredIdRef.current || selectedIdRef.current;

    const isNeighborOrSelf = (focusId: string, nodeId: string) =>
      focusId === nodeId || Boolean(adjRef.current.get(focusId)?.has(nodeId));

    const isInMessagePassing = (nodeId: string) => {
      if (!mpActiveRef.current || !selectedIdRef.current) return false;
      return (
        nodeId === selectedIdRef.current ||
        hop1SetRef.current.has(nodeId) ||
        hop2SetRef.current.has(nodeId)
      );
    };

    const getMessagePassingEdgeHop = (s: string, t: string): 0 | 1 | 2 => {
      if (!mpActiveRef.current || !selectedIdRef.current) return 0;
      const sel = selectedIdRef.current;
      if ((s === sel && hop1SetRef.current.has(t)) || (t === sel && hop1SetRef.current.has(s))) {
        return 1;
      }
      if (
        (hop1SetRef.current.has(s) && hop2SetRef.current.has(t)) ||
        (hop1SetRef.current.has(t) && hop2SetRef.current.has(s))
      ) {
        return 2;
      }
      return 0;
    };

    const nodeAlpha = (nodeId: string) => {
      if (mpActiveRef.current && selectedIdRef.current) {
        return isInMessagePassing(nodeId) ? 1 : 0.06;
      }
      const f = getFocusId();
      if (f) return isNeighborOrSelf(f, nodeId) ? 1 : 0.1;
      const hl = highlightSetRef.current;
      if (hl.size > 0) return highlightFocusSetRef.current.has(nodeId) ? 1 : 0.12;
      return 1;
    };

    const init = async () => {
      try {
        setLibError(null);
        if (mode === '2d') {
          if (!window.ForceGraph) {
            await loadVendorScript('/vendor/force-graph.min.js');
          }
          if (disposed || !window.ForceGraph) return;
        } else {
          if (!window.ForceGraph3D) {
            await loadVendorScript('/vendor/3d-force-graph.min.js');
          }
          if (disposed || !window.ForceGraph3D) return;
        }

        host.innerHTML = '';

        const fgNodes: FGNode[] = nodes.map((n) => ({
          ...n,
          color: KIND_COLOR[n.kind] || '#64748B',
        }));
        const fgLinks: FGLink[] = filteredEdges.map((e) => ({
          source: e.source,
          target: e.target,
          edge_type: e.edge_type,
          is_public: e.is_public,
          color: e.is_public ? EDGE_PUBLIC_COLOR : EDGE_PRIVATE_COLOR,
          alpha: e.is_public ? 0.42 : 0.54,
          width: e.is_public ? 1.0 : 1.15,
        }));

        let userMoved = false;
        let firstFitDone = false;
        const markMoved = () => {
          userMoved = true;
        };
        host.addEventListener('pointerdown', markMoved, { passive: true });
        host.addEventListener('wheel', markMoved, { passive: true });

        if (mode === '2d') {
          let lastClick = { id: null as string | null, t: 0 };

          const Graph = window.ForceGraph!()(host)
            .backgroundColor('#ffffff')
            .nodeRelSize(1)
            .nodeVal((n: FGNode) => {
              const r = radiusFor(n);
              return r * r;
            })
            .nodeCanvasObject((node: FGNode, ctx: CanvasRenderingContext2D, scale: number) => {
              const r = radiusFor(node);
              const a = nodeAlpha(node.id);
              const dim = a < 1;
              const f = getFocusId();
              const isHl = highlightSetRef.current.size > 0 && !f && highlightSetRef.current.has(node.id);

              const isMpOn = mpActiveRef.current && Boolean(selectedIdRef.current);
              const isMpHop1 = isMpOn && hop1SetRef.current.has(node.id);
              const isMpHop2 = isMpOn && hop2SetRef.current.has(node.id);

              if (isHl) {
                ctx.globalAlpha = 0.9;
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 5 / scale, 0, 2 * Math.PI, false);
                ctx.fillStyle = 'rgba(255, 214, 10, 0.55)';
                ctx.fill();
              } else if (isMpHop1) {
                ctx.globalAlpha = 0.32;
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 5.5 / scale, 0, 2 * Math.PI, false);
                ctx.fillStyle = '#EF4444';
                ctx.fill();
              } else if (isMpHop2) {
                ctx.globalAlpha = 0.28;
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 4.5 / scale, 0, 2 * Math.PI, false);
                ctx.fillStyle = '#FF5A1F';
                ctx.fill();
              }

              ctx.globalAlpha = a;
              ctx.beginPath();
              ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
              ctx.fillStyle = node.color;
              ctx.fill();

              if (isHl) {
                ctx.lineWidth = 2.4 / scale;
                ctx.strokeStyle = '#b8860b';
                ctx.stroke();
              } else if (isMpHop1) {
                ctx.lineWidth = 2.0 / scale;
                ctx.strokeStyle = '#EF4444';
                ctx.stroke();
              } else if (isMpHop2) {
                ctx.lineWidth = 1.8 / scale;
                ctx.strokeStyle = '#FF5A1F';
                ctx.stroke();
              } else if (!dim) {
                ctx.lineWidth = 1.2 / scale;
                ctx.strokeStyle = '#ffffff';
                ctx.stroke();
              }

              if (node.id === selectedIdRef.current) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 3.5 / scale, 0, 2 * Math.PI, false);
                ctx.lineWidth = 2.0 / scale;
                ctx.strokeStyle = isMpOn ? '#FF5A1F' : '#0F172A';
                ctx.stroke();
              }

              const showLabel =
                !dim &&
                (node.id === selectedIdRef.current ||
                  node.id === hoveredIdRef.current ||
                  (f && isNeighborOrSelf(f, node.id) && scale > 1.05) ||
                  (isHl && scale > 0.7) ||
                  scale > 1.65);

              if (showLabel) {
                const fs = Math.max(6, 11 / scale);
                let lab = String(node.label || '');
                if (lab.length > 28) lab = `${lab.slice(0, 27)}…`;
                ctx.font = `600 ${fs}px "Plus Jakarta Sans", system-ui, sans-serif`;
                ctx.textAlign = 'left';
                ctx.textBaseline = 'middle';
                ctx.lineWidth = 3 / scale;
                ctx.strokeStyle = 'rgba(255,255,255,0.94)';
                ctx.strokeText(lab, node.x + r + 4 / scale, node.y);
                ctx.fillStyle = '#0F172A';
                ctx.fillText(lab, node.x + r + 4 / scale, node.y);
              }
              ctx.globalAlpha = 1;
            })
            .nodePointerAreaPaint((node: FGNode, color: string, ctx: CanvasRenderingContext2D) => {
              ctx.fillStyle = color;
              ctx.beginPath();
              ctx.arc(node.x, node.y, radiusFor(node) + 3.5, 0, 2 * Math.PI, false);
              ctx.fill();
            })
            .nodeLabel(() => '')
            .linkColor((l: FGLink) => {
              const s = getLinkEndpointId(l.source);
              const t = getLinkEndpointId(l.target);
              if (mpActiveRef.current && selectedIdRef.current) {
                const hop = getMessagePassingEdgeHop(s, t);
                if (hop === 1) return hexToRgba(l.is_public ? '#FF5A1F' : '#EF4444', 0.92);
                if (hop === 2) return hexToRgba('#FF5A1F', 0.72);
                return hexToRgba(l.color, 0.03);
              }
              const f = getFocusId();
              if (f) {
                return s === f || t === f ? hexToRgba(l.color, 0.85) : hexToRgba(l.color, 0.06);
              }
              if (highlightSetRef.current.size > 0) {
                const inHl = highlightFocusSetRef.current.has(s) && highlightFocusSetRef.current.has(t);
                return inHl ? hexToRgba(l.color, 0.78) : hexToRgba(l.color, 0.06);
              }
              return hexToRgba(l.color, l.alpha);
            })
            .linkWidth((l: FGLink) => {
              const s = getLinkEndpointId(l.source);
              const t = getLinkEndpointId(l.target);
              if (mpActiveRef.current && selectedIdRef.current) {
                const hop = getMessagePassingEdgeHop(s, t);
                if (hop === 1) return 2.4;
                if (hop === 2) return 1.65;
                return 0.35;
              }
              const f = getFocusId();
              if (f) return s === f || t === f ? 1.8 : 0.5;
              return l.width;
            })
            .linkDirectionalParticles((l: FGLink) => {
              if (!mpActiveRef.current || !selectedIdRef.current) return 0;
              const hop = getMessagePassingEdgeHop(
                getLinkEndpointId(l.source),
                getLinkEndpointId(l.target),
              );
              return hop === 1 ? 3 : hop === 2 ? 2 : 0;
            })
            .linkDirectionalParticleWidth(3.2)
            .linkDirectionalParticleSpeed(0.008)
            .linkDirectionalParticleColor((l: FGLink) => {
              const hop = getMessagePassingEdgeHop(
                getLinkEndpointId(l.source),
                getLinkEndpointId(l.target),
              );
              return hop === 1 ? '#EF4444' : '#FF5A1F';
            })
            .d3AlphaDecay(0.026)
            .d3VelocityDecay(0.32)
            .warmupTicks(45)
            .cooldownTicks(260)
            .onNodeHover((n: FGNode | null) => {
              hoveredIdRef.current = n ? n.id : null;
              host.style.cursor = n ? 'pointer' : 'grab';
              setHoveredInfo(n ? { node: nodeByIdRef.current.get(n.id) ?? n } : null);
            })
            .onNodeClick((n: FGNode) => {
              const now = Date.now();
              if (lastClick.id === n.id && now - lastClick.t < 380) {
                // Double click unpins the node
                n.fx = undefined;
                n.fy = undefined;
                lastClick = { id: null, t: 0 };
                return;
              }
              lastClick = { id: n.id, t: now };
              selectedIdRef.current = n.id;
              const orig = nodeByIdRef.current.get(n.id) ?? n;
              onSelectRef.current?.(orig);
              Graph.centerAt(n.x, n.y, 450);
              if (Graph.zoom() < 1.8) Graph.zoom(1.8, 450);
            })
            .onNodeDragEnd((n: FGNode) => {
              n.fx = n.x;
              n.fy = n.y;
            })
            .onBackgroundClick(() => {
              selectedIdRef.current = null;
              onSelectRef.current?.(null);
            })
            .onEngineStop(() => {
              if (!firstFitDone && !userMoved) {
                firstFitDone = true;
                try {
                  Graph.zoomToFit(450, 38);
                } catch {
                  // ignore
                }
              }
            })
            .graphData({ nodes: fgNodes, links: fgLinks });

          graphRef.current = Graph;

          const resize = () => {
            if (disposed || !host) return;
            const w = Math.max(300, host.clientWidth);
            const h = Math.max(380, host.clientHeight);
            try {
              Graph.width(w).height(h);
            } catch {
              // ignore
            }
          };
          resize();
          ro = new ResizeObserver(resize);
          ro.observe(host);

          fitTimer = window.setTimeout(() => {
            if (!disposed && !userMoved) {
              try {
                Graph.zoomToFit(450, 38);
              } catch {
                // ignore
              }
            }
          }, 520);
        } else {
          // Classic 3d-force-graph (Three.js/WebGL)
          const Graph3D = window.ForceGraph3D!()(host)
            .backgroundColor('#ffffff')
            .nodeId('id')
            .nodeLabel((n: FGNode) => `${KIND_LABEL[n.kind]} · ${n.label} (bậc ${n.degree})`)
            .nodeVal((n: FGNode) => Math.max(1.5, Math.sqrt(Math.max(1, n.degree)) * 2.2))
            .nodeResolution(12)
            .nodeOpacity(0.95)
            .nodeColor((n: FGNode) => {
              if (mpActiveRef.current && selectedIdRef.current) {
                if (n.id === selectedIdRef.current) return '#0F172A';
                if (hop1SetRef.current.has(n.id)) return '#EF4444';
                if (hop2SetRef.current.has(n.id)) return '#FF5A1F';
                return '#e8ecf1';
              }
              const f = getFocusId();
              if (f && !isNeighborOrSelf(f, n.id)) return '#e8ecf1';
              if (highlightSetRef.current.size > 0 && !f) {
                if (highlightSetRef.current.has(n.id)) return '#b8860b';
                if (!highlightFocusSetRef.current.has(n.id)) return '#e8ecf1';
              }
              return n.color;
            })
            .linkColor((l: FGLink) => {
              const s = getLinkEndpointId(l.source);
              const t = getLinkEndpointId(l.target);
              if (mpActiveRef.current && selectedIdRef.current) {
                const hop = getMessagePassingEdgeHop(s, t);
                if (hop === 1) return '#EF4444';
                if (hop === 2) return '#FF5A1F';
                return '#f2f5f8';
              }
              const f = getFocusId();
              if (f && s !== f && t !== f) return '#f2f5f8';
              if (highlightSetRef.current.size > 0 && !f) {
                if (!(highlightFocusSetRef.current.has(s) && highlightFocusSetRef.current.has(t))) {
                  return '#f2f5f8';
                }
              }
              return l.color;
            })
            .linkOpacity(0.5)
            .linkWidth((l: FGLink) => {
              const s = getLinkEndpointId(l.source);
              const t = getLinkEndpointId(l.target);
              if (mpActiveRef.current && selectedIdRef.current) {
                const hop = getMessagePassingEdgeHop(s, t);
                if (hop === 1) return 2.2;
                if (hop === 2) return 1.5;
                return 0.3;
              }
              const f = getFocusId();
              if (f && (s === f || t === f)) return 1.8;
              return 0.8;
            })
            .linkDirectionalParticles((l: FGLink) => {
              if (!mpActiveRef.current || !selectedIdRef.current) return 0;
              const hop = getMessagePassingEdgeHop(
                getLinkEndpointId(l.source),
                getLinkEndpointId(l.target),
              );
              return hop === 1 ? 3 : hop === 2 ? 2 : 0;
            })
            .linkDirectionalParticleWidth(2.4)
            .linkDirectionalParticleSpeed(0.008)
            .cooldownTicks(180)
            .onNodeHover((n: FGNode | null) => {
              hoveredIdRef.current = n ? n.id : null;
              host.style.cursor = n ? 'pointer' : 'grab';
              setHoveredInfo(n ? { node: nodeByIdRef.current.get(n.id) ?? n } : null);
              try {
                Graph3D.nodeColor(Graph3D.nodeColor());
                Graph3D.linkColor(Graph3D.linkColor());
              } catch {
                // ignore
              }
            })
            .onNodeClick((n: FGNode) => {
              selectedIdRef.current = n.id;
              const orig = nodeByIdRef.current.get(n.id) ?? n;
              onSelectRef.current?.(orig);
              try {
                Graph3D.nodeColor(Graph3D.nodeColor());
                Graph3D.linkColor(Graph3D.linkColor());
              } catch {
                // ignore
              }
            })
            .onEngineStop(() => {
              if (!firstFitDone && !userMoved) {
                firstFitDone = true;
                try {
                  Graph3D.zoomToFit(500, 45);
                } catch {
                  // ignore
                }
              }
            })
            .graphData({ nodes: fgNodes, links: fgLinks });

          graphRef.current = Graph3D;

          const resize3D = () => {
            if (disposed || !host) return;
            const w = Math.max(300, host.clientWidth);
            const h = Math.max(380, host.clientHeight);
            try {
              Graph3D.width(w).height(h);
            } catch {
              // ignore
            }
          };
          resize3D();
          ro = new ResizeObserver(resize3D);
          ro.observe(host);

          fitTimer = window.setTimeout(() => {
            if (!disposed && !userMoved) {
              try {
                Graph3D.zoomToFit(500, 45);
              } catch {
                // ignore
              }
            }
          }, 700);
        }

        return () => {
          host.removeEventListener('pointerdown', markMoved);
          host.removeEventListener('wheel', markMoved);
        };
      } catch (err) {
        if (!disposed) {
          setLibError(err instanceof Error ? err.message : 'Lỗi khởi tạo đồ thị.');
        }
      }
    };

    let cleanupListeners: (() => void) | undefined;
    init().then((fn) => {
      cleanupListeners = fn;
    });

    return () => {
      disposed = true;
      if (fitTimer !== null) window.clearTimeout(fitTimer);
      ro?.disconnect();
      cleanupListeners?.();
      const g = graphRef.current;
      if (g) {
        try {
          if (typeof g._destructor === 'function') g._destructor();
          else if (typeof g.pauseAnimation === 'function') g.pauseAnimation();
        } catch {
          // ignore
        }
        graphRef.current = null;
      }
      if (host) host.innerHTML = '';
    };
  }, [nodes, filteredEdges, mode]);

  const handleFitView = () => {
    const g = graphRef.current;
    if (!g) return;
    try {
      g.zoomToFit(450, 40);
    } catch {
      // ignore
    }
  };

  const handleClearFocus = () => {
    selectedIdRef.current = null;
    hoveredIdRef.current = null;
    onSelectNode?.(null);
    const g = graphRef.current;
    if (g && mode === '3d') {
      try {
        g.nodeColor(g.nodeColor());
        g.linkColor(g.linkColor());
      } catch {
        // ignore
      }
    }
  };

  return (
    <div
      className={`relative w-full h-full bg-white overflow-hidden rounded-[12px] ${className}`}
    >
      {/* ForceGraph / ForceGraph3D mount host (absolute inset-0 prevents canvas from inflating parent div) */}
      <div ref={containerRef} className="absolute inset-0 w-full h-full" />

      {/* Top-right compact controls */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5">
        {selectedNodeId && (
          <button
            type="button"
            onClick={handleClearFocus}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white/92 px-2.5 py-1.5 text-xs font-semibold text-slate-700 shadow-sm backdrop-blur-md hover:border-orange-300 hover:text-[#C2410C] cursor-pointer"
          >
            <RotateCcw size={13} />
            <span>Bỏ chọn</span>
          </button>
        )}
        <button
          type="button"
          onClick={handleFitView}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white/92 px-2.5 py-1.5 text-xs font-semibold text-slate-700 shadow-sm backdrop-blur-md hover:border-orange-300 hover:text-[#C2410C] cursor-pointer"
        >
          <Maximize2 size={13} />
          <span>Vừa khung</span>
        </button>
      </div>

      {/* Hover quick badge (top-left) */}
      {hoveredInfo && (
        <div className="pointer-events-none absolute top-3 left-3 z-10 max-w-[300px] rounded-xl border border-slate-200 bg-white/94 px-3 py-2 shadow-md backdrop-blur-md">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500">
            <span
              className="h-2 w-2 rounded-full shrink-0"
              style={{ background: KIND_COLOR[hoveredInfo.node.kind] }}
            />
            <span>{KIND_LABEL[hoveredInfo.node.kind]}</span>
            <span className="ml-auto font-mono text-[10px] text-slate-400">
              bậc {hoveredInfo.node.degree}
            </span>
          </div>
          <div className="text-xs font-semibold text-slate-900 truncate mt-0.5">
            {hoveredInfo.node.label}
          </div>
        </div>
      )}

      {/* Classic clean floating legend (bottom-left) */}
      <div className="pointer-events-none absolute bottom-3 left-3 z-10 rounded-xl border border-slate-200/90 bg-white/92 px-3 py-2.5 text-[11.5px] text-slate-700 shadow-sm backdrop-blur-md">
        <div className="font-semibold text-slate-900 mb-1.5">Loại nút</div>
        <div className="space-y-1">
          {(['user', 'job', 'skill', 'occupation'] as const).map((k) => (
            <div key={k} className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 rounded-full ring-1 ring-white shadow-xs"
                style={{ background: KIND_COLOR[k] }}
              />
              <span>{KIND_LABEL[k]}</span>
            </div>
          ))}
        </div>
        <div className="font-semibold text-slate-900 mt-2.5 mb-1">Loại cạnh</div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="h-[2.5px] w-3.5 rounded-full bg-[#F97316]" />
            <span>Công khai</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-[2.5px] w-3.5 rounded-full bg-[#EF4444]" />
            <span>Riêng tư</span>
          </div>
        </div>
      </div>

      {/* Minimal interaction hint (bottom-right) */}
      <div className="pointer-events-none absolute bottom-3 right-3 z-10 hidden sm:block rounded-full border border-slate-200/80 bg-white/88 px-3 py-1 text-[11px] text-slate-500 backdrop-blur-md">
        {mode === '2d'
          ? 'Kéo nút để dời · thả ra để ghim · bấm đúp để bỏ ghim · cuộn để zoom'
          : 'Kéo để xoay 3D · cuộn để zoom · bấm nút để soi liên kết'}
      </div>

      {libError && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/90 p-6 text-center text-sm text-rose-700">
          {libError}
        </div>
      )}
    </div>
  );
};

export default JobGraphExplorer3D;
