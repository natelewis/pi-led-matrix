import { useEffect, useRef, useState } from 'react';
import {
  Check,
  ChevronDown,
  Laptop,
  Lock,
  Plus,
  Server,
} from 'lucide-react';
import type { MatrixTarget } from '@/types/matrix';

export interface TargetSwitcherProps {
  targets: MatrixTarget[];
  activeTarget: MatrixTarget;
  switching?: boolean;
  onSelect: (targetId: string) => void;
  onManageDevices: () => void;
}

export function TargetSwitcher({
  targets,
  activeTarget,
  switching = false,
  onSelect,
  onManageDevices,
}: TargetSwitcherProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('mousedown', onClickOutside);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('mousedown', onClickOutside);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const isRemote = !activeTarget.isLocal;

  return (
    <div ref={containerRef} className="relative px-3 pt-3">
      <button
        type="button"
        disabled={switching}
        onClick={() => setOpen((v) => !v)}
        className={`flex w-full items-center gap-2.5 rounded-xl border px-3 py-2 text-left transition-all cursor-pointer ${
          isRemote
            ? 'border-violet-500/40 bg-violet-500/10 hover:border-violet-400/60'
            : 'border-slate-800 bg-surface-950/70 hover:border-slate-700'
        }`}
      >
        <div
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${
            isRemote
              ? 'bg-violet-500/20 text-violet-300'
              : 'bg-surface-800 text-cyan-300'
          }`}
        >
          {isRemote ? <Server className="h-3.5 w-3.5" /> : <Laptop className="h-3.5 w-3.5" />}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-xs font-semibold text-white">
              {activeTarget.name}
            </span>
          </div>
          <div className="truncate font-mono text-[10px] text-slate-400">
            {isRemote ? activeTarget.url : 'This computer'}
          </div>
        </div>

        <ChevronDown
          className={`h-3.5 w-3.5 shrink-0 text-slate-400 transition-transform ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>

      {open && (
        <div className="absolute left-3 right-3 z-40 mt-1.5 overflow-hidden rounded-xl border border-slate-700/90 bg-surface-900 shadow-2xl shadow-black/60">
          <div className="max-h-56 overflow-y-auto p-1">
            {targets.map((target) => {
              const selected = target.id === activeTarget.id;
              return (
                <button
                  key={target.id}
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    if (!selected) onSelect(target.id);
                  }}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors cursor-pointer ${
                    selected
                      ? 'bg-cyan-500/12 text-white'
                      : 'text-slate-300 hover:bg-surface-800'
                  }`}
                >
                  <span className="shrink-0 text-slate-400">
                    {target.isLocal ? (
                      <Laptop className="h-3.5 w-3.5 text-cyan-300" />
                    ) : (
                      <Server className="h-3.5 w-3.5 text-violet-300" />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-medium">{target.name}</div>
                    {target.url && (
                      <div className="truncate font-mono text-[10px] text-slate-500">
                        {target.url}
                      </div>
                    )}
                  </div>
                  {!target.isLocal && !target.hasSession && (
                    <Lock className="h-3 w-3 shrink-0 text-amber-400" />
                  )}
                  {selected && <Check className="h-3.5 w-3.5 shrink-0 text-cyan-400" />}
                </button>
              );
            })}
          </div>
          <div className="border-t border-slate-800 p-1">
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                onManageDevices();
              }}
              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium text-cyan-300 transition-colors hover:bg-surface-800 cursor-pointer"
            >
              <Plus className="h-3.5 w-3.5" />
              Manage Remote Devices
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
