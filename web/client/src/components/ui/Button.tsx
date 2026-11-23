import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400 active:bg-cyan-500 shadow-sm shadow-cyan-500/20 disabled:bg-cyan-500/40 disabled:text-slate-900',
  secondary:
    'bg-surface-800 text-slate-100 hover:bg-surface-700 border border-slate-700/80 disabled:opacity-50',
  outline:
    'bg-transparent text-slate-200 border border-slate-700 hover:border-slate-500 hover:bg-surface-800/60 disabled:opacity-50',
  ghost:
    'bg-transparent text-slate-300 hover:text-white hover:bg-surface-800/80 disabled:opacity-40',
  danger:
    'bg-rose-500/15 text-rose-300 border border-rose-500/35 hover:bg-rose-500/25 hover:text-rose-200 disabled:opacity-40',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-2.5 text-xs gap-1.5 rounded-lg',
  md: 'h-9 px-3.5 text-sm gap-2 rounded-lg',
  lg: 'h-11 px-5 text-sm gap-2 rounded-xl',
};

export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  leftIcon,
  rightIcon,
  disabled,
  className = '',
  children,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors cursor-pointer disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/70 ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...rest}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : leftIcon}
      {children}
      {!loading && rightIcon}
    </button>
  );
}
