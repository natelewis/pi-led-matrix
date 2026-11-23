import type { ReactNode } from 'react';

export type BadgeTone = 'neutral' | 'cyan' | 'emerald' | 'amber' | 'rose' | 'violet';

const toneClasses: Record<BadgeTone, string> = {
  neutral: 'bg-slate-800 text-slate-300 border-slate-700/80',
  cyan: 'bg-cyan-500/12 text-cyan-300 border-cyan-500/30',
  emerald: 'bg-emerald-500/12 text-emerald-300 border-emerald-500/30',
  amber: 'bg-amber-500/12 text-amber-300 border-amber-500/30',
  rose: 'bg-rose-500/12 text-rose-300 border-rose-500/30',
  violet: 'bg-violet-500/12 text-violet-300 border-violet-500/30',
};

export interface BadgeProps {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
}

export function Badge({ tone = 'neutral', children, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-tight ${toneClasses[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
