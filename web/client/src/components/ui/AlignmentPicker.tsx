import { AlignCenter, AlignLeft, AlignRight } from 'lucide-react';

export interface AlignmentPickerProps {
  value: string;
  mode?: 'horizontal' | 'grid';
  disabled?: boolean;
  onChange: (value: string) => void;
}

const HORIZONTAL_OPTS = [
  { value: 'left', label: 'Left', icon: AlignLeft },
  { value: 'center', label: 'Center', icon: AlignCenter },
  { value: 'right', label: 'Right', icon: AlignRight },
] as const;

const GRID_ROWS = ['top', 'middle', 'bottom'] as const;
const GRID_COLS = ['left', 'center', 'right'] as const;

export function AlignmentPicker({
  value,
  mode = 'horizontal',
  disabled = false,
  onChange,
}: AlignmentPickerProps) {
  if (mode === 'horizontal') {
    const normalized = ['left', 'center', 'right'].includes(value) ? value : 'center';
    return (
      <div className="grid w-full grid-cols-3 gap-1 rounded-lg border border-slate-800 bg-surface-950 p-1">
        {HORIZONTAL_OPTS.map(({ value: optVal, label, icon: Icon }) => {
          const active = normalized === optVal;
          return (
            <button
              key={optVal}
              type="button"
              disabled={disabled}
              title={label}
              onClick={() => onChange(optVal)}
              className={`inline-flex h-7 items-center justify-center gap-1.5 rounded-md px-2 text-xs font-medium transition-colors cursor-pointer disabled:opacity-40 ${
                active
                  ? 'bg-cyan-500/20 text-cyan-200 ring-1 ring-cyan-500/40'
                  : 'text-slate-400 hover:bg-surface-800/80 hover:text-slate-200'
              }`}
            >
              <Icon className="h-3.5 w-3.5 shrink-0" />
              <span>{label}</span>
            </button>
          );
        })}
      </div>
    );
  }

  const normalized = value.includes('-') ? value : 'center-middle';
  const [curH, curV] = normalized.split('-');

  return (
    <div className="flex items-center gap-4 rounded-xl border border-slate-800/80 bg-surface-950/60 p-3">
      <div
        role="radiogroup"
        aria-label="Optical text alignment"
        className="grid grid-cols-3 gap-1.5 rounded-lg border border-slate-800 bg-black/70 p-2"
      >
        {GRID_ROWS.map((row) =>
          GRID_COLS.map((col) => {
            const cellVal = `${col}-${row}`;
            const active = normalized === cellVal;
            return (
              <button
                key={cellVal}
                type="button"
                role="radio"
                aria-checked={active}
                disabled={disabled}
                title={`${col} / ${row}`}
                onClick={() => onChange(cellVal)}
                className={`flex h-7 w-7 items-center justify-center rounded-md border transition-all cursor-pointer disabled:opacity-40 ${
                  active
                    ? 'border-cyan-400 bg-cyan-500/25 shadow-sm shadow-cyan-500/30'
                    : 'border-slate-800 bg-surface-900/70 hover:border-slate-600'
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full transition-transform ${
                    active ? 'scale-110 bg-cyan-300' : 'bg-slate-600'
                  }`}
                />
              </button>
            );
          })
        )}
      </div>

      <div className="space-y-1 text-xs">
        <div className="font-medium capitalize text-slate-200">
          {curH || 'center'} · {curV || 'middle'}
        </div>
        <p className="text-[11px] leading-relaxed text-slate-400">
          Centers ink bounds optically on your LED display.
        </p>
      </div>
    </div>
  );
}
