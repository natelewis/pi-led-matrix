import type { SelectHTMLAttributes } from 'react';
import { ChevronDown } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  hasError?: boolean;
}

export function Select({
  options,
  hasError = false,
  className = '',
  ...rest
}: SelectProps) {
  return (
    <div className="relative">
      <select
        className={`h-9 w-full appearance-none rounded-lg border bg-surface-950/90 pl-3 pr-9 text-sm text-slate-100 transition-colors focus:outline-none focus:ring-2 ${
          hasError
            ? 'border-rose-500/70 focus:border-rose-400 focus:ring-rose-500/25'
            : 'border-slate-700/90 focus:border-cyan-400 focus:ring-cyan-400/20'
        } ${className}`}
        {...rest}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-surface-900 text-slate-100">
            {opt.label}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
    </div>
  );
}
