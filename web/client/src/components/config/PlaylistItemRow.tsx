import { useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  Check,
  CopyPlus,
  GripVertical,
  Play,
  Sliders,
  Terminal,
  Trash2,
} from 'lucide-react';
import { Badge, type BadgeTone } from '@/components/ui';
import { buildEffectRunCommand } from '@/utils/cliCommand';
import { formatPlaylistItemLabel } from '@/utils/playlistLabels';
import type { EffectCategory, EffectMeta, PlaylistItem } from '@/types/matrix';

const CATEGORY_TONES: Record<EffectCategory, BadgeTone> = {
  animation: 'cyan',
  game: 'violet',
  media: 'amber',
  text: 'emerald',
  utility: 'neutral',
};

export interface PlaylistItemRowProps {
  index: number;
  total: number;
  item: PlaylistItem;
  meta?: EffectMeta;
  isPlaying?: boolean;
  isDragging?: boolean;
  isDragOver?: boolean;
  onDragStart: () => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: () => void;
  onDragEnd: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onPlayNow: () => void;
  onCopyCommand: (command: string) => void;
  onDuplicate: () => void;
  onConfigure: () => void;
  onRemove: () => void;
}

export function PlaylistItemRow({
  index,
  total,
  item,
  meta,
  isPlaying = false,
  isDragging,
  isDragOver,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
  onMoveUp,
  onMoveDown,
  onPlayNow,
  onCopyCommand,
  onDuplicate,
  onConfigure,
  onRemove,
}: PlaylistItemRowProps) {
  const [copied, setCopied] = useState(false);
  const hasConfig = Boolean(item.config && Object.keys(item.config).length > 0);
  const needsConfig =
    meta && meta.configSchema !== 'none' && !hasConfig;
  const runCommand = buildEffectRunCommand(item);
  const displayLabel = formatPlaylistItemLabel(item, meta);
  const configuredFile =
    (item.effect === 'video' || item.effect === 'image') &&
    typeof item.config?.file === 'string' &&
    item.config.file.trim().length > 0
      ? item.config.file
      : null;

  const handleCopyCommand = () => {
    onCopyCommand(runCommand);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onDragEnd={onDragEnd}
      className={`group flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-all ${
        isDragOver
          ? 'border-cyan-400 bg-cyan-500/10'
          : isDragging
            ? 'border-slate-700 bg-surface-950/40 opacity-50'
            : isPlaying
              ? 'border-emerald-400/60 bg-emerald-500/8 ring-1 ring-emerald-500/25'
              : 'border-slate-800/90 bg-surface-950/75 hover:border-slate-700'
      }`}
    >
      <div
        title="Drag to reorder"
        className="flex cursor-grab items-center gap-1.5 text-slate-500 active:cursor-grabbing"
      >
        <GripVertical className="h-4 w-4" />
        <span className="w-5 text-right font-mono text-[11px] text-slate-500">
          {index + 1}
        </span>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="truncate text-sm font-medium text-slate-100"
            title={configuredFile ?? displayLabel}
          >
            {displayLabel}
          </span>
          {!configuredFile && (
            <span className="font-mono text-[11px] text-slate-500">{item.effect}</span>
          )}
          {isPlaying && (
            <Badge tone="emerald" className="animate-pulse">
              Playing
            </Badge>
          )}
          {meta && (
            <Badge tone={CATEGORY_TONES[meta.category]}>{meta.category}</Badge>
          )}
          {hasConfig && <Badge tone="emerald">Configured</Badge>}
          {needsConfig && <Badge tone="amber">Needs config</Badge>}
        </div>
        {(configuredFile || meta?.description) && (
          <p className="mt-0.5 truncate text-xs text-slate-400">
            {configuredFile ? (
              <span className="font-mono text-[11px] text-slate-400">{configuredFile}</span>
            ) : (
              meta?.description
            )}
          </p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <button
          type="button"
          onClick={onPlayNow}
          title="Play this effect now on local matrix"
          className={`rounded-lg p-1.5 transition-colors cursor-pointer ${
            isPlaying
              ? 'bg-emerald-500/20 text-emerald-300'
              : 'text-emerald-400/80 hover:bg-emerald-500/15 hover:text-emerald-300'
          }`}
        >
          <Play className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={handleCopyCommand}
          title={`Copy terminal command: ${runCommand}`}
          className={`rounded-lg p-1.5 transition-colors cursor-pointer ${
            copied
              ? 'bg-emerald-500/15 text-emerald-300'
              : 'text-slate-400 hover:bg-surface-800 hover:text-cyan-200'
          }`}
        >
          {copied ? (
            <Check className="h-3.5 w-3.5" />
          ) : (
            <Terminal className="h-3.5 w-3.5" />
          )}
        </button>
        <button
          type="button"
          onClick={onConfigure}
          title="Configure effect options"
          className={`rounded-lg p-1.5 transition-colors cursor-pointer ${
            hasConfig || needsConfig
              ? 'text-cyan-300 hover:bg-cyan-500/15'
              : 'text-slate-400 hover:bg-surface-800 hover:text-slate-200'
          }`}
        >
          <Sliders className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={onMoveUp}
          disabled={index === 0}
          title="Move up"
          className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-surface-800 hover:text-slate-100 disabled:opacity-25 cursor-pointer disabled:cursor-not-allowed"
        >
          <ArrowUp className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={onMoveDown}
          disabled={index === total - 1}
          title="Move down"
          className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-surface-800 hover:text-slate-100 disabled:opacity-25 cursor-pointer disabled:cursor-not-allowed"
        >
          <ArrowDown className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={onDuplicate}
          title="Duplicate in playlist (increases play weight)"
          className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-surface-800 hover:text-slate-100 cursor-pointer"
        >
          <CopyPlus className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={onRemove}
          title="Remove from playlist"
          className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-rose-500/15 hover:text-rose-300 cursor-pointer"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
