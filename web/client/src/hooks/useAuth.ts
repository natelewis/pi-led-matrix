import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '@/api/client';
import type { AuthStatus } from '@/types/matrix';

export function useAuth() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await api.auth.status();
      setStatus(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reach server');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setup = useCallback(async (password: string) => {
    const next = await api.auth.setup(password);
    setStatus(next);
    return next;
  }, []);

  const login = useCallback(async (password: string) => {
    const next = await api.auth.login(password);
    setStatus(next);
    return next;
  }, []);

  const logout = useCallback(async () => {
    await api.auth.logout();
    setStatus((prev) =>
      prev ? { ...prev, authenticated: false, expiresAt: null } : null
    );
  }, []);

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      await api.auth.changePassword(currentPassword, newPassword);
      await refresh();
    },
    [refresh]
  );

  const handleUnauthorized = useCallback((err: unknown) => {
    if (err instanceof ApiError && err.status === 401 && !err.remoteAuthRequired) {
      setStatus((prev) =>
        prev ? { ...prev, authenticated: false, expiresAt: null } : null
      );
      return true;
    }
    return false;
  }, []);

  return {
    status,
    loading,
    error,
    refresh,
    setup,
    login,
    logout,
    changePassword,
    handleUnauthorized,
  };
}
