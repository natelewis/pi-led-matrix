import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api, ApiError, setActiveTargetHeader } from '@/api/client';
import type { MatrixTarget, TargetsState } from '@/types/matrix';

interface UseTargetsOptions {
  enabled: boolean;
  onLocalUnauthorized?: (err: unknown) => boolean;
}

const DEFAULT_TARGETS: TargetsState = {
  activeTargetId: 'local',
  targets: [
    {
      id: 'local',
      name: 'Local Machine',
      url: null,
      isLocal: true,
      hasSession: true,
      createdAt: null,
    },
  ],
};

export function useTargets({ enabled, onLocalUnauthorized }: UseTargetsOptions) {
  const [state, setState] = useState<TargetsState>(DEFAULT_TARGETS);
  const [initialized, setInitialized] = useState(false);
  const [loading, setLoading] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [remoteAuthNeeded, setRemoteAuthNeeded] = useState(false);
  const [remoteUnreachableError, setRemoteUnreachableError] = useState<string | null>(
    null
  );

  const activeTargetIdRef = useRef(state.activeTargetId);
  activeTargetIdRef.current = state.activeTargetId;

  const applyTargetsState = useCallback((next: TargetsState) => {
    setActiveTargetHeader(next.activeTargetId);
    activeTargetIdRef.current = next.activeTargetId;
    setState(next);
  }, []);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    try {
      const next = await api.targets.list();
      applyTargetsState(next);
    } catch (err) {
      onLocalUnauthorized?.(err);
    } finally {
      setLoading(false);
      setInitialized(true);
    }
  }, [enabled, onLocalUnauthorized, applyTargetsState]);

  useEffect(() => {
    if (enabled) {
      void refresh();
    } else {
      applyTargetsState(DEFAULT_TARGETS);
      setInitialized(false);
      setRemoteAuthNeeded(false);
      setRemoteUnreachableError(null);
    }
  }, [enabled, refresh, applyTargetsState]);

  const activeTarget: MatrixTarget = useMemo(() => {
    return (
      state.targets.find((t) => t.id === state.activeTargetId) ?? state.targets[0]
    );
  }, [state]);

  const isRemote = !activeTarget.isLocal;

  const handleApiError = useCallback(
    (err: unknown) => {
      if (err instanceof ApiError) {
        if (err.remoteAuthRequired) {
          // Ignore stale 401s from a previously selected device
          if (!err.targetId || err.targetId === activeTargetIdRef.current) {
            setRemoteAuthNeeded(true);
            setRemoteUnreachableError(null);
          }
          void refresh();
          return true;
        }
        if (err.remoteUnreachable) {
          if (!err.targetId || err.targetId === activeTargetIdRef.current) {
            setRemoteUnreachableError(err.message);
          }
          return true;
        }
      }
      return onLocalUnauthorized?.(err) ?? false;
    },
    [onLocalUnauthorized, refresh]
  );

  const selectTarget = useCallback(
    async (targetId: string) => {
      setSwitching(true);
      setRemoteAuthNeeded(false);
      setRemoteUnreachableError(null);
      try {
        const next = await api.targets.setActive(targetId);
        applyTargetsState(next);
        const chosen = next.targets.find((t) => t.id === next.activeTargetId);
        if (chosen && !chosen.isLocal && !chosen.hasSession) {
          setRemoteAuthNeeded(true);
        }
        return next;
      } catch (err) {
        onLocalUnauthorized?.(err);
        throw err;
      } finally {
        setSwitching(false);
      }
    },
    [onLocalUnauthorized, applyTargetsState]
  );

  const addTarget = useCallback(
    async (name: string, url: string) => {
      try {
        const next = await api.targets.add(name, url);
        applyTargetsState({ activeTargetId: next.activeTargetId, targets: next.targets });
        return next.target;
      } catch (err) {
        onLocalUnauthorized?.(err);
        throw err;
      }
    },
    [onLocalUnauthorized, applyTargetsState]
  );

  const removeTarget = useCallback(
    async (id: string) => {
      try {
        const next = await api.targets.remove(id);
        applyTargetsState(next);
        if (next.activeTargetId === 'local') {
          setRemoteAuthNeeded(false);
          setRemoteUnreachableError(null);
        }
        return next;
      } catch (err) {
        onLocalUnauthorized?.(err);
        throw err;
      }
    },
    [onLocalUnauthorized, applyTargetsState]
  );

  const loginTarget = useCallback(
    async (id: string, password: string, setup = false) => {
      try {
        const res = await api.targets.login(id, password, setup);
        applyTargetsState(res.targetsState);
        if (id === res.targetsState.activeTargetId) {
          setRemoteAuthNeeded(false);
          setRemoteUnreachableError(null);
        }
        return res;
      } catch (err) {
        onLocalUnauthorized?.(err);
        throw err;
      }
    },
    [onLocalUnauthorized, applyTargetsState]
  );

  const logoutTarget = useCallback(
    async (id: string) => {
      try {
        const res = await api.targets.logout(id);
        applyTargetsState(res.targetsState);
        if (id === res.targetsState.activeTargetId) {
          setRemoteAuthNeeded(true);
        }
        return res;
      } catch (err) {
        onLocalUnauthorized?.(err);
        throw err;
      }
    },
    [onLocalUnauthorized, applyTargetsState]
  );

  return {
    targets: state.targets,
    activeTargetId: state.activeTargetId,
    activeTarget,
    isRemote,
    initialized,
    loading,
    switching,
    remoteAuthNeeded,
    remoteUnreachableError,
    applyTargetsState,
    clearRemoteErrors: () => {
      setRemoteAuthNeeded(false);
      setRemoteUnreachableError(null);
    },
    refresh,
    selectTarget,
    addTarget,
    removeTarget,
    loginTarget,
    logoutTarget,
    handleApiError,
  };
}
