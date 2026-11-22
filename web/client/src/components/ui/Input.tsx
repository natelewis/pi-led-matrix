import type { InputHTMLAttributes, ReactNode } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  leftIcon?: ReactNode;
  rightSlot?: ReactNode;
  hasError?: boolean;
}

export function Input({
  leftIcon,
  rightSlot,
  hasError = false,
  className = '',
  ...rest
}: InputProps) {
  return (
    <div className="relative flex items-center">
      {leftIcon && (
        <span className="pointer-events-none absolute left-3 text-slate-400">
          {leftIcon}
        </span>
      )}
      <input
        className={`h-9 w-full rounded-lg border bg-surface-950/90 text-sm text-slate-100 placeholder:text-slate-500 transition-colors focus:outline-none focus:ring-2 ${
          hasError
            ? 'border-rose-500/70 focus:border-rose-400 focus:ring-rose-500/25'
            : 'border-slate-700/90 focus:border-cyan-400 focus:ring-cyan-400/20'
        } ${leftIcon ? 'pl-9' : 'pl-3'} ${rightSlot ? 'pr-12' : 'pr-3'} ${className}`}
        {...rest}
      />
      {rightSlot && (
        <span className="absolute right-2.5 flex items-center text-xs text-slate-400">
          {rightSlot}
        </span>
      )}
    </div>
  );
}
