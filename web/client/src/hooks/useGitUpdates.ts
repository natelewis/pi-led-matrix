import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '@/api/client';
import type { GitPullResponse, GitStatusResponse } from '@/types/matrix';

const AUTO_CHECK_INTERVAL_MS = 5 * 60 * 1000; // Check every 5 minutes when tab is visible

export interface UseGitUpdatesOptions {
  enabled: boolean;
  targetId: string;
  targetName: string;
  isPlaying: boolean;
  onApiError?: (err: unknown) => boolean;
  onRepoUpdated?: (result: GitPullResponse) => void;
  onBouncePlayback?: () => Promise<void>;
}

export interface PullAndRestartOutcome {
  pull: GitPullResponse;
  serverRestarted: boolean;
  serverBackOnline: boolean;
  playbackRestarted: boolean;
}

export function useGitUpdates({
  enabled,
  targetId,
  targetName,
  isPlaying,
  onApiError,
  onRepoUpdated,
  onBouncePlayback,
}: UseGitUpdatesOptions) {
  const [status, setStatus] = useState<GitStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [phaseMessage, setPhaseMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastPull, setLastPull] = useState<GitPullResponse | null>(null);

  const seqRef = useRef(0);
  const busyRef = useRef(false);
  busyRef.current = updating || restarting;

  const isPlayingRef = useRef(isPlaying);
  isPlayingRef.current = isPlaying;

  const onApiErrorRef = useRef(onApiError);
  onApiErrorRef.current = onApiError;

  const onRepoUpdatedRef = useRef(onRepoUpdated);
  onRepoUpdatedRef.current = onRepoUpdated;

  const onBouncePlaybackRef = useRef(onBouncePlayback);
  onBouncePlaybackRef.current = onBouncePlayback;

  const targetNameRef = useRef(targetName);
  targetNameRef.current = targetName;

  const formatError = useCallback((err: unknown, fallback: string) => {
    if (err instanceof ApiError && err.status === 404) {
      return `${targetNameRef.current} is running an older Studio server without in-app git updates. Pull once on the Pi and restart pi-led-matrix-web to enable it.`;
    }
    return err instanceof Error ? err.message : fallback;
  }, []);

  const waitForServerBackOnline = useCallback(async (seq: number) => {
    for (let attempt = 0; attempt < 8; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 850));
      if (seq !== seqRef.current) return null;
      try {
        const refreshed = await api.system.gitStatus(false);
        if (seq !== seqRef.current) return null;
        return refreshed;
      } catch {
        // Still restarting — retry
      }
    }
    return null;
  }, []);

  const checkUpdates = useCallback(
    async (options?: { fetchRemote?: boolean; silent?: boolean }) => {
      if (!enabled) return null;
      const fetchRemote = options?.fetchRemote ?? true;
      const silent = options?.silent ?? false;
      const seq = ++seqRef.current;

      if (silent) {
        setLoading(true);
      } else {
        setChecking(true);
      }
      if (!silent) {
        setError(null);
      }

      try {
        const res = await api.system.gitStatus(fetchRemote);
        if (seq !== seqRef.current) return null;
        setStatus(res);
        setError(null);
        return res;
      } catch (err) {
        if (seq !== seqRef.current) return null;
        onApiErrorRef.current?.(err);
        setError(formatError(err, 'Unable to query repository status.'));
        return null;
      } finally {
        if (seq === seqRef.current) {
          setLoading(false);
          setChecking(false);
        }
      }
    },
    [enabled, formatError]
  );

  // Auto-check on target connect/switch + gentle 5-minute background poll
  useEffect(() => {
    seqRef.current += 1;
    setStatus(null);
    setLastPull(null);
    setError(null);
    setUpdating(false);
    setRestarting(false);
    setPhaseMessage(null);

    if (!enabled) {
      setLoading(false);
      return;
    }

    void checkUpdates({ fetchRemote: true, silent: true });

    const intervalId = window.setInterval(() => {
      if (document.visibilityState === 'visible' && !busyRef.current) {
        void checkUpdates({ fetchRemote: true, silent: true });
      }
    }, AUTO_CHECK_INTERVAL_MS);

    return () => {
      seqRef.current += 1;
      window.clearInterval(intervalId);
    };
  }, [targetId, enabled, checkUpdates]);

  const pullAndRestart = useCallback(async (): Promise<PullAndRestartOutcome | null> => {
    if (!enabled) return null;
    const seq = ++seqRef.current;
    setUpdating(true);
    setError(null);
    setPhaseMessage('Pulling latest commits from git…');

    try {
      const pull = await api.system.gitPull();
      if (seq !== seqRef.current) return null;

      setLastPull(pull);
      const canRestart = Boolean(pull.canRestart ?? pull.status.canRestart);
      setStatus({ ...pull.status, canRestart });

      let serverRestarted = false;
      let serverBackOnline = true;
      let playbackRestarted = false;

      if (pull.updated) {
        if (canRestart) {
          setRestarting(true);
          setPhaseMessage('Restarting Studio server…');
          await api.system.restart();
          if (seq !== seqRef.current) return null;
          serverRestarted = true;

          const refreshed = await waitForServerBackOnline(seq);
          if (seq !== seqRef.current) return null;
          if (refreshed) {
            setStatus(refreshed);
            setLastPull((prev) =>
              prev ? { ...prev, serverFilesChanged: false } : null
            );
          } else {
            serverBackOnline = false;
            setError('Server is still restarting — click Check Updates in a moment.');
          }
          setRestarting(false);
        }

        if (serverBackOnline) {
          onRepoUpdatedRef.current?.(pull);
        }

        if (
          serverBackOnline &&
          pull.playbackFilesChanged &&
          isPlayingRef.current &&
          onBouncePlaybackRef.current
        ) {
          setPhaseMessage('Reloading running playlist…');
          try {
            await onBouncePlaybackRef.current();
            playbackRestarted = true;
          } catch {
            // Non-fatal: pull & server restart succeeded
          }
        }
      }

      return {
        pull,
        serverRestarted,
        serverBackOnline,
        playbackRestarted,
      };
    } catch (err) {
      if (seq !== seqRef.current) return null;
      onApiErrorRef.current?.(err);
      const msg = formatError(err, 'git pull failed.');
      setError(msg);
      throw new Error(msg);
    } finally {
      if (seq === seqRef.current) {
        setUpdating(false);
        setRestarting(false);
        setPhaseMessage(null);
      }
    }
  }, [enabled, formatError, waitForServerBackOnline]);

  const restartServer = useCallback(async (): Promise<boolean> => {
    if (!enabled) return false;
    const seq = ++seqRef.current;
    setRestarting(true);
    setError(null);
    setPhaseMessage('Restarting Studio server…');
    try {
      await api.system.restart();
      if (seq !== seqRef.current) return false;
      const refreshed = await waitForServerBackOnline(seq);
      if (seq !== seqRef.current) return false;
      if (refreshed) {
        setStatus(refreshed);
        setLastPull((prev) => (prev ? { ...prev, serverFilesChanged: false } : null));
        return true;
      }
      setError('Server is still restarting — click Check Updates in a moment.');
      return false;
    } catch (err) {
      if (seq !== seqRef.current) return false;
      onApiErrorRef.current?.(err);
      const msg = formatError(err, 'Server restart failed.');
      setError(msg);
      throw new Error(msg);
    } finally {
      if (seq === seqRef.current) {
        setRestarting(false);
        setPhaseMessage(null);
      }
    }
  }, [enabled, formatError, waitForServerBackOnline]);

  const updatesAvailable =
    enabled && status?.isGitRepo && typeof status.behind === 'number' && status.behind > 0
      ? status.behind
      : 0;

  return {
    status,
    loading,
    checking,
    updating,
    restarting,
    phaseMessage,
    error,
    lastPull,
    updatesAvailable,
    checkUpdates,
    pullAndRestart,
    restartServer,
  };
}

export type GitUpdatesController = ReturnType<typeof useGitUpdates>;
