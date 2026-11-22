import React, { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutGrid,
  Network,
  RefreshCw,
  Server,
  ClipboardCheck,
  Menu,
  X,
  Presentation,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { WarmSilkAurora } from './three';

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Tổng quan', icon: LayoutGrid },
  { to: '/do-thi', label: 'Đồ thị việc làm', icon: Network },
  { to: '/lien-bang', label: 'Mô phỏng FL', icon: RefreshCw },
  { to: '/giam-sat-node', label: 'Giám sát node FL', icon: Server },
  { to: '/ket-luan', label: 'Kết luận & hạn chế', icon: ClipboardCheck },
];

interface DefenseStep {
  to: string;
  title: string;
  point: string;
}

const DEFENSE_STEPS: DefenseStep[] = [
  {
    to: '/',
    title: 'Kiến trúc tổng thể & Kết quả chính',
    point:
      'Trình bày bài toán gợi ý việc làm bảo vệ quyền riêng tư: tách 52.544 Public Edges và 711.820 Private Edges trên 9.116 employer silos (0 B raw data rời máy).',
  },
  {
    to: '/do-thi',
    title: 'Đồ thị Heterogeneous & LightGCN 2-Hop',
    point:
      'Chọn 1 nút việc làm/kỹ năng rồi bấm "Minh họa 2-Hop" để giải thích cách LightGCN lan truyền tín hiệu qua Public Graph Backbone (O*NET) mà không cần lộ dữ liệu riêng.',
  },
  {
    to: '/lien-bang',
    title: 'Ablation Study & Phân tích hội tụ FL',
    point:
      'So sánh Centralized vs Federated (FedAvg / FedProx), đánh giá Privacy-Utility Trade-off và phân bố Non-IID giữa 9.116 doanh nghiệp.',
  },
  {
    to: '/giam-sat-node',
    title: 'Thực nghiệm Live: Dropout, Straggler & Fairness',
    point:
      'Chạy nhanh Preset 1 → Preset 2/3 để so sánh A/B trực tiếp, và click điểm trên Scatter Non-IID để đối chiếu Client Drift với 3D Topology.',
  },
  {
    to: '/ket-luan',
    title: 'Tổng kết đóng góp & Hướng phát triển',
    point:
      'Chốt lại giá trị nghiên cứu của hệ thống (FL Catalog, 0 B Data Leakage) cùng các hạn chế về DP-SGD, Secure Aggregation và kế hoạch mở rộng.',
  },
];

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const currentStepIdx = Math.max(
    0,
    DEFENSE_STEPS.findIndex((s) =>
      s.to === '/' ? location.pathname === '/' : location.pathname.startsWith(s.to),
    ),
  );
  const currentStep = DEFENSE_STEPS[currentStepIdx];

  const goToStep = (idx: number) => {
    const clamped = Math.max(0, Math.min(DEFENSE_STEPS.length - 1, idx));
    navigate(DEFENSE_STEPS[clamped].to);
  };

  const renderSidebarContent = (onNavigate?: () => void, collapsed = false) => (
    <div className={`flex h-full flex-col justify-between ${collapsed ? 'p-2.5' : 'p-4'}`}>
      <div>
        {/* Brand Header */}
        <div
          className={`flex items-center ${
            collapsed ? 'flex-col gap-2 pb-3' : 'justify-between px-2 pb-4'
          } mb-3 border-b border-slate-200/80`}
        >
          <div className="flex items-center gap-2.5">
            <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-gradient-to-b from-[#FF5A1F] to-[#EA580C] text-white shadow-[0_2px_8px_rgba(255,90,31,0.32)]">
              <Network size={18} strokeWidth={2} />
            </div>
            {!collapsed && (
              <div>
                <div className="font-display text-[1.02rem] font-bold tracking-[-0.025em] text-[#0F172A] leading-tight">
                  FedGraph
                </div>
                <div className="font-mono-tech text-[0.65rem] font-semibold uppercase tracking-[0.08em] text-[#C2410C]">
                  GNN · FL Job Reco
                </div>
              </div>
            )}
          </div>
          {!onNavigate && (
            <button
              type="button"
              onClick={() => setSidebarCollapsed((v) => !v)}
              title={collapsed ? 'Mở rộng thanh taskbar bên trái' : 'Thu nhỏ thanh taskbar bên trái'}
              aria-label={collapsed ? 'Mở rộng thanh taskbar bên trái' : 'Thu nhỏ thanh taskbar bên trái'}
              className="hidden md:inline-flex items-center justify-center rounded-lg border border-orange-200/90 bg-[#FFF7ED]/90 p-1.5 text-[#C2410C] hover:border-[#FF5A1F] hover:bg-orange-100/80 transition-all cursor-pointer"
            >
              {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
            </button>
          )}
          {onNavigate && (
            <button
              type="button"
              onClick={onNavigate}
              aria-label="Đóng menu"
              className="md:hidden rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer"
            >
              <X size={18} />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav aria-label="Điều hướng chính" className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.to);

            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={onNavigate}
                title={collapsed ? item.label : undefined}
                className={`group relative flex items-center ${
                  collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2.5'
                } rounded-[9px] text-[0.88rem] font-medium transition-colors ${
                  isActive
                    ? 'text-[#C2410C] font-semibold'
                    : 'text-[#475569] hover:bg-[#FFF7ED]/75 hover:text-[#0F172A]'
                }`}
              >
                {isActive && (
                  <motion.span
                    layoutId="nav-pill"
                    transition={{ type: 'spring', stiffness: 460, damping: 34 }}
                    className="absolute inset-0 rounded-[9px] bg-[#FFF7ED] shadow-[inset_3px_0_0_#FF5A1F] ring-1 ring-[#FED7AA]/75"
                  />
                )}
                <Icon
                  size={17}
                  strokeWidth={1.75}
                  className={`relative z-10 shrink-0 transition-colors ${
                    isActive
                      ? 'text-[#EA580C]'
                      : 'text-[#64748B] group-hover:text-[#0F172A]'
                  }`}
                />
                {!collapsed && <span className="relative z-10 truncate">{item.label}</span>}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Sidebar Collapse Button + Presentation Mode Trigger + Framed Academic Footer */}
      <div className="space-y-2 mt-4">
        {!onNavigate && (
          <button
            type="button"
            onClick={() => setSidebarCollapsed((v) => !v)}
            title={collapsed ? 'Mở rộng thanh bên' : 'Thu nhỏ thanh bên'}
            className={`hidden md:flex w-full items-center ${
              collapsed ? 'justify-center px-2 py-2' : 'justify-between gap-2 px-3 py-2'
            } rounded-[10px] border border-orange-200/90 bg-[#FFF7ED]/85 text-xs font-semibold text-[#C2410C] hover:border-[#FF5A1F] hover:bg-orange-100/70 transition-all cursor-pointer`}
          >
            {collapsed ? (
              <ChevronRight size={15} />
            ) : (
              <>
                <span className="inline-flex items-center gap-1.5">
                  <ChevronLeft size={14} />
                  <span>Thu nhỏ thanh bên</span>
                </span>
                <span className="font-mono-tech text-[10px] rounded px-1.5 py-0.5 bg-white/80 text-[#C2410C] border border-orange-200">
                  «
                </span>
              </>
            )}
          </button>
        )}

        <button
          type="button"
          onClick={() => {
            setGuideOpen((v) => !v);
            onNavigate?.();
          }}
          title={collapsed ? 'Chế độ Thuyết trình (5 bước)' : undefined}
          className={`w-full flex items-center ${
            collapsed ? 'justify-center px-2 py-2' : 'justify-between gap-2 px-3 py-2'
          } rounded-[10px] border text-xs font-semibold transition-all cursor-pointer ${
            guideOpen
              ? 'border-[#FF5A1F] bg-[#FFF7ED] text-[#C2410C] shadow-xs'
              : 'border-slate-200/90 bg-white/80 text-slate-700 hover:border-orange-300 hover:bg-[#FFF7ED]/70 hover:text-[#C2410C]'
          }`}
        >
          <span className="inline-flex items-center gap-2">
            <Presentation size={14} className={guideOpen ? 'text-[#FF5A1F]' : 'text-slate-500'} />
            {!collapsed && <span>Chế độ Thuyết trình</span>}
          </span>
          {!collapsed && (
            <span
              className={`font-mono-tech text-[10px] rounded-full px-1.5 py-0.5 ${
                guideOpen ? 'bg-[#FF5A1F] text-white' : 'bg-slate-100 text-slate-500'
              }`}
            >
              {guideOpen ? 'ON' : '5 bước'}
            </span>
          )}
        </button>

        {!collapsed && (
          <div className="sb-footer p-3.5">
            <div className="font-mono-tech text-[0.66rem] font-bold uppercase tracking-[0.08em] text-[#C2410C] mb-1.5">
              Đồ án cuối kỳ — DSS
            </div>
            <div className="space-y-0.5 text-[0.79rem] font-medium text-[#0F172A]">
              <div>Phan Gia Bảo · <span className="font-mono-tech text-[0.74rem] text-[#475569]">102220265</span></div>
              <div>Nguyễn Văn Chương · <span className="font-mono-tech text-[0.74rem] text-[#475569]">102220267</span></div>
            </div>
            <div className="mt-2 pt-2 border-t border-slate-200/80 font-mono-tech text-[0.66rem] text-[#64748B] space-y-0.5">
              <div className="font-semibold text-[#0F172A]">CareerBuilder + O*NET (V3)</div>
              <div>9.116 nodes · 264.995 nút · 764.364 cạnh</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="relative min-h-screen blueprint-grid text-[#0F172A]">
      {/* Persistent ThreeUI WarmSilkAurora WebGL Backdrop */}
      <WarmSilkAurora />

      <div className="relative z-10 flex min-h-screen">
        {/* Desktop Sidebar */}
        <aside
          className={`hidden md:block ${
            sidebarCollapsed ? 'w-[72px]' : 'w-[264px]'
          } shrink-0 sticky top-0 h-screen sidebar-glass z-20 transition-[width] duration-200 ease-out`}
        >
          {renderSidebarContent(undefined, sidebarCollapsed)}
        </aside>

        {/* Mobile Top Bar */}
        <div className="md:hidden fixed top-0 inset-x-0 h-14 z-30 flex items-center justify-between px-4 sidebar-glass border-b border-slate-200/80">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-b from-[#FF5A1F] to-[#EA580C] text-white">
              <Network size={15} strokeWidth={2} />
            </div>
            <span className="font-display font-bold text-sm tracking-tight text-[#0F172A]">
              FedGraph
            </span>
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Mở menu điều hướng"
            className="rounded-lg border border-slate-200 bg-white/85 p-1.5 text-slate-700 hover:border-[#FDBA74] cursor-pointer"
          >
            <Menu size={18} />
          </button>
        </div>

        {/* Mobile Drawer */}
        <AnimatePresence>
          {mobileOpen && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setMobileOpen(false)}
                className="lg:hidden fixed inset-0 z-40 bg-slate-900/25 backdrop-blur-xs"
              />
              <motion.aside
                initial={{ x: -280 }}
                animate={{ x: 0 }}
                exit={{ x: -280 }}
                transition={{ type: 'spring', stiffness: 400, damping: 36 }}
                className="lg:hidden fixed top-0 left-0 bottom-0 w-[272px] z-50 sidebar-glass shadow-2xl"
              >
                {renderSidebarContent(() => setMobileOpen(false))}
              </motion.aside>
            </>
          )}
        </AnimatePresence>

        {/* Main Content Viewport */}
        <main className={`flex-1 min-w-0 pt-18 md:pt-7 px-4 sm:px-6 lg:px-9 ${guideOpen ? 'pb-32' : 'pb-12'}`}>
          <div className="mx-auto max-w-[1360px]">{children}</div>
        </main>
      </div>

      {/* Floating 5-Step Guided Defense Presentation Bar */}
      <AnimatePresence>
        {guideOpen && currentStep && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            className="fixed bottom-4 left-1/2 -translate-x-1/2 lg:left-[calc(50%+132px)] z-40 w-[min(94vw,760px)] rounded-2xl border border-orange-200/90 bg-white/92 p-3.5 shadow-[0_14px_38px_-10px_rgba(15,23,42,0.22)] backdrop-blur-xl"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1 rounded-full bg-[#FF5A1F] px-2.5 py-0.5 font-mono-tech text-[10px] font-bold uppercase tracking-wider text-white">
                    <Presentation size={11} />
                    Bước {currentStepIdx + 1}/{DEFENSE_STEPS.length}
                  </span>
                  <span className="font-display text-sm font-bold text-[#0F172A]">
                    {currentStep.title}
                  </span>
                  <div className="flex items-center gap-1 ml-1">
                    {DEFENSE_STEPS.map((st, idx) => (
                      <button
                        key={st.to}
                        type="button"
                        onClick={() => goToStep(idx)}
                        aria-label={`Đi tới bước ${idx + 1}: ${st.title}`}
                        className={`h-1.5 rounded-full transition-all cursor-pointer ${
                          idx === currentStepIdx
                            ? 'w-5 bg-[#FF5A1F]'
                            : 'w-1.5 bg-slate-300 hover:bg-orange-300'
                        }`}
                      />
                    ))}
                  </div>
                </div>
                <p className="text-xs leading-relaxed text-[#475569]">{currentStep.point}</p>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  type="button"
                  disabled={currentStepIdx === 0}
                  onClick={() => goToStep(currentStepIdx - 1)}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:border-orange-300 hover:text-[#C2410C] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                >
                  <ChevronLeft size={13} />
                  <span>Trước</span>
                </button>
                <button
                  type="button"
                  disabled={currentStepIdx === DEFENSE_STEPS.length - 1}
                  onClick={() => goToStep(currentStepIdx + 1)}
                  className="inline-flex items-center gap-1 rounded-lg bg-[#FF5A1F] px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-[#EA580C] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                >
                  <span>Tiếp theo</span>
                  <ChevronRight size={13} />
                </button>
                <button
                  type="button"
                  onClick={() => setGuideOpen(false)}
                  aria-label="Đóng chế độ thuyết trình"
                  className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 cursor-pointer"
                >
                  <X size={14} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
