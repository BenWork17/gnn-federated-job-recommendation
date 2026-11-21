import React, { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';

/* -------------------------------------------------------------------------- */
/* GlassCard — Frosted specular glass with optional 3D tilt + warm sheen      */
/* -------------------------------------------------------------------------- */
export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  tilt?: boolean;
  sheen?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const PAD_MAP = {
  none: '',
  sm: 'p-3.5',
  md: 'p-5',
  lg: 'p-6',
};

export const GlassCard: React.FC<GlassCardProps> = ({
  tilt = false,
  sheen = true,
  padding = 'md',
  className = '',
  style,
  onMouseMove,
  onMouseLeave,
  children,
  ...rest
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const [tiltStyle, setTiltStyle] = useState<React.CSSProperties>({});

  const handleMove = (e: React.MouseEvent<HTMLDivElement>) => {
    onMouseMove?.(e);
    if ((!tilt && !sheen) || !ref.current) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const rect = ref.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (sheen) {
      ref.current.style.setProperty('--mx', `${x}px`);
      ref.current.style.setProperty('--my', `${y}px`);
    }
    if (tilt) {
      const px = (x / rect.width - 0.5) * 2;
      const py = (y / rect.height - 0.5) * 2;
      const rx = (-py * 1.8).toFixed(2);
      const ry = (px * 1.8).toFixed(2);
      setTiltStyle({
        transform: `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-2px)`,
      });
    }
  };

  const handleLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    onMouseLeave?.(e);
    if (tilt) setTiltStyle({});
  };

  return (
    <div
      ref={ref}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      style={{ ...style, ...tiltStyle }}
      className={`glass-card ${tilt ? 'glass-card-interactive' : ''} ${
        sheen ? 'glass-card-sheen' : ''
      } ${PAD_MAP[padding]} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
};

/* -------------------------------------------------------------------------- */
/* BorderBeamCard — Magic UI animated Signal Orange border beam hero card     */
/* -------------------------------------------------------------------------- */
export interface BorderBeamCardProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const BorderBeamCard: React.FC<BorderBeamCardProps> = ({
  padding = 'lg',
  className = '',
  children,
  ...rest
}) => (
  <div className={`border-beam ${PAD_MAP[padding]} ${className}`} {...rest}>
    <div className="relative z-10 h-full">{children}</div>
  </div>
);

/* -------------------------------------------------------------------------- */
/* StatTile — Swiss-grid KPI metric tile with tabular numerals                */
/* -------------------------------------------------------------------------- */
export interface StatTileProps {
  kicker: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  accent?: 'orange' | 'ink' | 'green' | 'sky';
  badge?: React.ReactNode;
  liveDot?: boolean;
  className?: string;
}

const ACCENT_VALUE = {
  orange: 'text-[#C2410C]',
  ink: 'text-[#0F172A]',
  green: 'text-[#047857]',
  sky: 'text-[#0369A1]',
};

export const StatTile: React.FC<StatTileProps> = ({
  kicker,
  value,
  sub,
  accent = 'ink',
  badge,
  liveDot = false,
  className = '',
}) => (
  <GlassCard tilt padding="md" className={`flex flex-col justify-between gap-2 ${className}`}>
    <div className="flex items-center justify-between gap-2">
      <span className="kicker-label">{kicker}</span>
      {badge}
    </div>
    <div
      className={`font-display text-[1.75rem] leading-[1.1] font-bold tracking-[-0.035em] tabular-nums flex items-center gap-2 ${ACCENT_VALUE[accent]}`}
    >
      {liveDot && (
        <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#FF5A1F] pulse-dot-orange shrink-0" />
      )}
      <span>{value}</span>
    </div>
    {sub && <div className="text-[0.83rem] leading-[1.45] text-[#475569]">{sub}</div>}
  </GlassCard>
);

/* -------------------------------------------------------------------------- */
/* SegmentedTabs — Vercel-style Framer Motion layoutId spring pill tabs       */
/* -------------------------------------------------------------------------- */
export interface TabOption<T extends string> {
  id: T;
  label: string;
  badge?: string | number;
}

export interface SegmentedTabsProps<T extends string> {
  options: TabOption<T>[];
  value: T;
  onChange: (value: T) => void;
  layoutId: string;
  size?: 'sm' | 'md';
  className?: string;
}

export function SegmentedTabs<T extends string>({
  options,
  value,
  onChange,
  layoutId,
  size = 'md',
  className = '',
}: SegmentedTabsProps<T>) {
  return (
    <div
      role="tablist"
      className={`inline-flex items-center rounded-[10px] bg-slate-100/85 p-1 border border-slate-200/80 backdrop-blur-sm ${className}`}
    >
      {options.map((opt) => {
        const active = opt.id === value;
        return (
          <button
            key={opt.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.id)}
            className={`relative z-10 inline-flex items-center gap-1.5 rounded-[7px] font-semibold transition-colors cursor-pointer select-none ${
              size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3.5 py-1.5 text-[0.84rem]'
            } ${active ? 'text-[#C2410C]' : 'text-[#475569] hover:text-[#0F172A]'}`}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                transition={{ type: 'spring', stiffness: 460, damping: 34 }}
                className="absolute inset-0 -z-10 rounded-[7px] bg-white shadow-[0_1px_3px_rgba(15,23,42,0.08)] ring-1 ring-[#FED7AA]"
              />
            )}
            <span>{opt.label}</span>
            {opt.badge !== undefined && (
              <span
                className={`font-mono-tech text-[0.68rem] px-1.5 py-0.5 rounded-full ${
                  active ? 'bg-[#FFF7ED] text-[#C2410C]' : 'bg-slate-200/80 text-slate-600'
                }`}
              >
                {opt.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* GlassExpander — Clean collapsed explainer accordion                        */
/* -------------------------------------------------------------------------- */
export interface GlassExpanderProps {
  title: string;
  defaultOpen?: boolean;
  badge?: string;
  children: React.ReactNode;
  className?: string;
}

export const GlassExpander: React.FC<GlassExpanderProps> = ({
  title,
  defaultOpen = false,
  badge,
  children,
  className = '',
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div
      className={`rounded-[10px] border transition-colors ${
        open ? 'border-[#FDBA74] bg-white/80' : 'border-[#E2E8F0] bg-white/70 hover:border-[#FDBA74]'
      } backdrop-blur-md ${className}`}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left cursor-pointer"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          {badge && (
            <span className="font-mono-tech text-[0.68rem] font-bold px-2 py-0.5 rounded-md bg-[#FFF7ED] text-[#C2410C] border border-[#FED7AA] shrink-0">
              {badge}
            </span>
          )}
          <span className="text-[0.88rem] font-semibold text-[#0F172A] truncate">{title}</span>
        </div>
        <ChevronDown
          size={16}
          className={`text-[#64748B] shrink-0 transition-transform duration-200 ${
            open ? 'rotate-180 text-[#EA580C]' : ''
          }`}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-1 border-t border-slate-200/70 text-[0.87rem] leading-relaxed text-[#475569]">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

/* -------------------------------------------------------------------------- */
/* StatusBadge — Live telemetry pill with optional animated pulse dot         */
/* -------------------------------------------------------------------------- */
export type BadgeTone = 'orange' | 'green' | 'warn' | 'red' | 'sky' | 'slate';

const BADGE_STYLES: Record<BadgeTone, string> = {
  orange: 'bg-[#FFF7ED] text-[#C2410C] border-[#FED7AA]',
  green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warn: 'bg-amber-50 text-amber-800 border-amber-200',
  red: 'bg-rose-50 text-rose-700 border-rose-200',
  sky: 'bg-sky-50 text-sky-700 border-sky-200',
  slate: 'bg-slate-100 text-slate-700 border-slate-200',
};

const DOT_STYLES: Record<BadgeTone, string> = {
  orange: 'bg-[#FF5A1F] pulse-dot-orange',
  green: 'bg-[#10B981] pulse-dot-green',
  warn: 'bg-[#F59E0B]',
  red: 'bg-[#EF4444]',
  sky: 'bg-[#0EA5E9]',
  slate: 'bg-slate-400',
};

export interface StatusBadgeProps {
  tone?: BadgeTone;
  pulse?: boolean;
  children: React.ReactNode;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  tone = 'orange',
  pulse = false,
  children,
  className = '',
}) => (
  <span
    className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono-tech text-[0.72rem] font-semibold leading-5 ${BADGE_STYLES[tone]} ${className}`}
  >
    {pulse && <span className={`h-2 w-2 rounded-full ${DOT_STYLES[tone]}`} />}
    {children}
  </span>
);

/* -------------------------------------------------------------------------- */
/* PageHeader — Crisp editorial kicker + Display title + 1-line subtitle      */
/* -------------------------------------------------------------------------- */
export interface PageHeaderProps {
  kicker: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ kicker, title, subtitle, actions }) => (
  <header className={`${subtitle ? 'mb-5' : 'mb-3'} flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between`}>
    <div className="min-w-0">
      <div className="kicker-label mb-1">{kicker}</div>
      <h1 className="font-display text-[1.85rem] sm:text-[2.15rem] font-bold tracking-[-0.035em] leading-[1.12] text-[#0F172A]">
        {title}
      </h1>
      {subtitle && (
        <p className="mt-1.5 text-[0.95rem] leading-[1.45] text-[#475569] max-w-3xl">{subtitle}</p>
      )}
    </div>
    {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
  </header>
);

/* -------------------------------------------------------------------------- */
/* LoadingSkeleton & ErrorBanner                                              */
/* -------------------------------------------------------------------------- */
export const LoadingPanel: React.FC<{ label?: string }> = ({ label = 'Đang tải dữ liệu...' }) => (
  <GlassCard padding="lg" className="flex items-center justify-center gap-3 min-h-[200px]">
    <span className="h-4 w-4 rounded-full border-2 border-[#FF5A1F] border-t-transparent animate-spin" />
    <span className="font-mono-tech text-xs font-semibold text-[#475569]">{label}</span>
  </GlassCard>
);

export const ErrorPanel: React.FC<{ message: string; onRetry?: () => void }> = ({
  message,
  onRetry,
}) => (
  <div className="rounded-[10px] border border-rose-200 border-l-4 border-l-[#EF4444] bg-white/85 backdrop-blur-md p-4 flex flex-wrap items-center justify-between gap-3">
    <div>
      <div className="font-mono-tech text-xs font-bold uppercase tracking-wider text-rose-700">
        Lỗi tải dữ liệu API
      </div>
      <p className="text-sm text-[#475569] mt-0.5">{message}</p>
    </div>
    {onRetry && (
      <button type="button" onClick={onRetry} className="btn-secondary text-xs">
        Thử lại
      </button>
    )}
  </div>
);
