import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutGrid,
  Network,
  RefreshCw,
  Server,
  ClipboardCheck,
  Menu,
  X,
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

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const renderSidebarContent = (onNavigate?: () => void) => (
    <div className="flex h-full flex-col justify-between p-4">
      <div>
        {/* Brand Header */}
        <div className="flex items-center justify-between px-2 pb-4 mb-3 border-b border-slate-200/80">
          <div className="flex items-center gap-2.5">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-[10px] bg-gradient-to-b from-[#FF5A1F] to-[#EA580C] text-white shadow-[0_2px_8px_rgba(255,90,31,0.32)]">
              <Network size={18} strokeWidth={2} />
            </div>
            <div>
              <div className="font-display text-[1.02rem] font-bold tracking-[-0.025em] text-[#0F172A] leading-tight">
                FedGraph
              </div>
              <div className="font-mono-tech text-[0.65rem] font-semibold uppercase tracking-[0.08em] text-[#C2410C]">
                GNN · FL Job Reco
              </div>
            </div>
          </div>
          {onNavigate && (
            <button
              type="button"
              onClick={onNavigate}
              aria-label="Đóng menu"
              className="lg:hidden rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer"
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
                className={`group relative flex items-center gap-3 rounded-[9px] px-3 py-2.5 text-[0.88rem] font-medium transition-colors ${
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
                <span className="relative z-10 truncate">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Framed Academic Footer */}
      <div className="sb-footer p-3.5 mt-4">
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
    </div>
  );

  return (
    <div className="relative min-h-screen blueprint-grid text-[#0F172A]">
      {/* Persistent ThreeUI WarmSilkAurora WebGL Backdrop */}
      <WarmSilkAurora />

      <div className="relative z-10 flex min-h-screen">
        {/* Desktop Sidebar */}
        <aside className="hidden lg:block w-[264px] shrink-0 sticky top-0 h-screen sidebar-glass z-20">
          {renderSidebarContent()}
        </aside>

        {/* Mobile Top Bar */}
        <div className="lg:hidden fixed top-0 inset-x-0 h-14 z-30 flex items-center justify-between px-4 sidebar-glass border-b border-slate-200/80">
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
        <main className="flex-1 min-w-0 pt-18 lg:pt-7 pb-12 px-4 sm:px-6 lg:px-9">
          <div className="mx-auto max-w-[1360px]">{children}</div>
        </main>
      </div>
    </div>
  );
};
