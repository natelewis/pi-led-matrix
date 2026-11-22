import { Play, Radio, SkipForward, Square } from 'lucide-react';
import { Badge, Button } from '@/components/ui';
import { formatPlaylistItemLabel } from '@/utils/playlistLabels';
import type { EffectMeta, PlaybackStatus } from '@/types/matrix';

export interface LivePlaybackBarProps {
  playback: PlaybackStatus;
  effectMap: Map<string, EffectMeta>;
  busy: boolean;
  onStart: () => void;
  onStop: () => void;
  onNext: () => void;
}

export function LivePlaybackBar({
  playback,
  effectMap,
  busy,
  onStart,
  onStop,
  onNext,
}: LivePlaybackBarProps) {
  const nowPlayingLabel = playback.currentEffect
    ? formatPlaylistItemLabel(
        {
          effect: playback.currentEffect,
          config: playback.currentConfig ?? undefined,
        },
        effectMap.get(playback.currentEffect)
      )
    : null;

  const delay = playback.playlistDelay ?? 0;
  const elapsed = Math.min(delay || playback.elapsedSeconds, playback.elapsedSeconds);
  const progressPct =
    playback.running && delay > 0 ? Math.min(100, Math.round((elapsed / delay) * 100)) : 0;

  return (
    <div className="border-b border-slate-800/80 bg-surface-900/75 px-4 py-2.5 sm:px-6">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              {playback.running && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              )}
              <span
                className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
                  playback.running ? 'bg-emerald-400' : 'bg-slate-600'
                }`}
              />
            </span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              {playback.running ? 'Live' : 'Stopped'}
            </span>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          {playback.running ? (
            <div className="flex min-w-0 items-center gap-2.5">
              <Radio className="h-3.5 w-3.5 shrink-0 text-cyan-400" />
              <span className="truncate text-xs font-medium text-white">
                {nowPlayingLabel || 'Starting playlist...'}
              </span>
              {playback.currentIndex !== null && playback.playlistLength !== null && (
                <Badge tone="neutral" className="font-mono text-[10px]">
                  #{playback.currentIndex + 1}/{playback.playlistLength}
                </Badge>
              )}
              {delay > 0 && (
                <div className="hidden items-center gap-2 sm:flex">
                  <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-cyan-400 transition-all duration-500"
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>
                  <span className="font-mono text-[11px] text-slate-400">
                    {Math.floor(elapsed)}s/{delay}s
                  </span>
                </div>
              )}
            </div>
          ) : (
            <span className="truncate text-xs text-slate-400">
              Local playlist idle — click Start to launch or run{' '}
              <code className="text-slate-300">make playlist</code>
            </span>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          {playback.running ? (
            <>
              <Button
                variant="secondary"
                size="sm"
                loading={busy}
                onClick={onNext}
                leftIcon={<SkipForward className="h-3.5 w-3.5" />}
              >
                Skip
              </Button>
              <Button
                variant="danger"
                size="sm"
                disabled={busy}
                onClick={onStop}
                leftIcon={<Square className="h-3 w-3" />}
              >
                Stop
              </Button>
            </>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              loading={busy}
              onClick={onStart}
              leftIcon={<Play className="h-3.5 w-3.5 text-emerald-400" />}
            >
              Start Playlist
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
