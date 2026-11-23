import { useCallback, useEffect, useRef, useState } from 'react';
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
  const followUpTimerRef = useRef<number | null>(null);
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  const clearFollowUpTimer = useCallback(() => {
    if (followUpTimerRef.current !== null) {
      window.clearTimeout(followUpTimerRef.current);
      followUpTimerRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    if (!enabledRef.current) return;
    try {
      const next = await api.playback.status();
      if (enabledRef.current) {
        setStatus(next);
      }
    } catch (err) {
      onUnauthorized?.(err);
    }
  }, [onUnauthorized]);

  useEffect(() => {
    if (!enabled) {
      clearFollowUpTimer();
      setStatus(DEFAULT_STATUS);
      return;
    }

    void poll();
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') {
        void poll();
      }
    }, 1500);

    return () => {
      window.clearInterval(timer);
      clearFollowUpTimer();
    };
  }, [enabled, poll, clearFollowUpTimer]);

  const runAction = useCallback(
    async (fn: () => Promise<PlaybackStatus>) => {
      setBusy(true);
      try {
        const next = await fn();
        if (enabledRef.current) {
          setStatus(next);
          clearFollowUpTimer();
          followUpTimerRef.current = window.setTimeout(() => {
            followUpTimerRef.current = null;
            void poll();
          }, 350);
        }
        return next;
      } catch (err) {
        onUnauthorized?.(err);
        throw err;
      } finally {
        setBusy(false);
      }
    },
    [onUnauthorized, poll, clearFollowUpTimer]
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
