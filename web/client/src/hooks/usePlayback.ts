import { useCallback, useEffect, useState } from 'react';
import { api } from '@/api/client';
import type { PlaybackStatus } from '@/types/matrix';

interface UsePlaybackOptions {
  enabled: boolean;
  onUnauthorized?: (err: unknown) => boolean;
}

const DEFAULT_STATUS: PlaybackStatus = {
  running: false,
  managed: false,
  pid: null,
  status: 'stopped',
  mode: 'stopped',
  currentIndex: null,
  currentEffect: null,
  currentConfig: null,
  playlistLength: null,
  playlistDelay: null,
  startedAt: null,
  elapsedSeconds: 0,
  virtual: null,
};

export function usePlayback({ enabled, onUnauthorized }: UsePlaybackOptions) {
  const [status, setStatus] = useState<PlaybackStatus>(DEFAULT_STATUS);
  const [busy, setBusy] = useState(false);

  const poll = useCallback(async () => {
    if (!enabled) return;
    try {
      const next = await api.playback.status();
      setStatus(next);
    } catch (err) {
      onUnauthorized?.(err);
    }
  }, [enabled, onUnauthorized]);

  useEffect(() => {
    if (!enabled) {
      setStatus(DEFAULT_STATUS);
      return;
    }

    void poll();
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') {
        void poll();
      }
    }, 1500);

    return () => window.clearInterval(timer);
  }, [enabled, poll]);

  const runAction = useCallback(
    async (fn: () => Promise<PlaybackStatus>) => {
      setBusy(true);
      try {
        const next = await fn();
        setStatus(next);
        window.setTimeout(() => void poll(), 350);
        return next;
      } catch (err) {
        onUnauthorized?.(err);
        throw err;
      } finally {
        setBusy(false);
      }
    },
    [onUnauthorized, poll]
  );

  const start = useCallback(
    (opts?: { index?: number; effect?: string; config?: Record<string, unknown> }) =>
      runAction(() => api.playback.start(opts)),
    [runAction]
  );

  const stop = useCallback(
    () => runAction(() => api.playback.stop()),
    [runAction]
  );

  const next = useCallback(
    () => runAction(() => api.playback.next()),
    [runAction]
  );

  const jump = useCallback(
    (index: number) => runAction(() => api.playback.jump(index)),
    [runAction]
  );

  const playEffect = useCallback(
    (effect: string, config?: Record<string, unknown>) =>
      runAction(() => api.playback.playEffect(effect, config)),
    [runAction]
  );

  return {
    status,
    busy,
    refresh: poll,
    start,
    stop,
    next,
    jump,
    playEffect,
  };
}
