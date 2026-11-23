export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}

export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled = false,
}: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="group flex w-full items-center justify-between gap-4 rounded-xl border border-slate-800/80 bg-surface-950/60 px-4 py-3 text-left transition-colors hover:border-slate-700 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
    >
      <div className="min-w-0">
        <div className="text-sm font-medium text-slate-100">{label}</div>
        {description && <p className="mt-0.5 text-xs text-slate-400">{description}</p>}
      </div>
      <span
        className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors ${
          checked
            ? 'border-cyan-400/60 bg-cyan-500/85'
            : 'border-slate-700 bg-slate-800'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
            checked ? 'translate-x-5.5' : 'translate-x-1'
          }`}
        />
      </span>
    </button>
  );
}
