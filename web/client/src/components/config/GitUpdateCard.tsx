import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowDownToLine,
  CheckCircle2,
  GitBranch,
  GitCommitHorizontal,
  Loader2,
  RefreshCw,
  RotateCcw,
} from 'lucide-react';
import { api, ApiError } from '@/api/client';
import { Badge, Button, Card, CardContent, CardHeader, useToast } from '@/components/ui';
import type { GitPullResponse, GitStatusResponse, MatrixTarget } from '@/types/matrix';

export interface GitUpdateCardProps {
  activeTarget: MatrixTarget;
  enabled: boolean;
  onApiError?: (err: unknown) => boolean;
  onRepoUpdated?: (result: GitPullResponse) => void;
}

export function GitUpdateCard({
  activeTarget,
  enabled,
  onApiError,
  onRepoUpdated,
}: GitUpdateCardProps) {
  const { notify } = useToast();
  const [status, setStatus] = useState<GitStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [pulling, setPulling] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPull, setLastPull] = useState<GitPullResponse | null>(null);
  const seqRef = useRef(0);

  const loadStatus = useCallback(
    async (fetchRemote = false) => {
      if (!enabled) return;
      const seq = ++seqRef.current;
      if (fetchRemote) {
        setChecking(true);
      } else {
        setLoading(true);
      }
      setError(null);
      try {
        const res = await api.system.gitStatus(fetchRemote);
        if (seq !== seqRef.current) return;
        setStatus(res);
        if (fetchRemote) {
          if (res.fetchError) {
            notify('error', 'Could not fetch remote updates', res.fetchError);
          } else if (res.behind && res.behind > 0) {
            notify(
              'info',
              `${res.behind} update${res.behind === 1 ? '' : 's'} available on ${activeTarget.name}`
            );
          } else {
            notify('success', `${activeTarget.name} is up to date`);
          }
        }
      } catch (err) {
        if (seq !== seqRef.current) return;
        onApiError?.(err);
        if (err instanceof ApiError && err.status === 404) {
          setError(
            `${activeTarget.name} is running an older Studio server without in-app git pull. Pull once on the Pi and restart pi-led-matrix-web to enable it.`
          );
        } else {
          setError(
            err instanceof Error ? err.message : 'Unable to query repository status.'
          );
        }
      } finally {
        if (seq === seqRef.current) {
          setLoading(false);
          setChecking(false);
        }
      }
    },
    [enabled, activeTarget.name, notify, onApiError]
  );

  useEffect(() => {
    seqRef.current += 1;
    setStatus(null);
    setLastPull(null);
    setError(null);
    setPulling(false);
    setRestarting(false);
    if (enabled) {
      void loadStatus(false);
    }
    return () => {
      seqRef.current += 1;
    };
  }, [activeTarget.id, enabled, loadStatus]);

  const handlePull = async () => {
    const seq = ++seqRef.current;
    setPulling(true);
    setError(null);
    try {
      const res = await api.system.gitPull();
      if (seq !== seqRef.current) return;
      setLastPull(res);
      setStatus({ ...res.status, canRestart: res.canRestart ?? res.status.canRestart });
      if (res.updated) {
        notify(
          'success',
          `Pulled updates on ${activeTarget.name}`,
          `${res.beforeCommit} → ${res.afterCommit} (${res.totalChangedFiles} file${
            res.totalChangedFiles === 1 ? '' : 's'
          } changed)`
        );
        onRepoUpdated?.(res);
      } else {
        notify('info', `${activeTarget.name} is already up to date`);
      }
    } catch (err) {
      if (seq !== seqRef.current) return;
      onApiError?.(err);
      const msg = err instanceof Error ? err.message : 'git pull failed.';
      setError(msg);
      notify('error', `Git pull failed on ${activeTarget.name}`, msg);
    } finally {
      if (seq === seqRef.current) {
        setPulling(false);
      }
    }
  };

  const handleRestart = async () => {
    const seq = ++seqRef.current;
    setRestarting(true);
    setError(null);
    try {
      await api.system.restart();
      if (seq !== seqRef.current) return;
      notify(
        'info',
        `Restarting ${activeTarget.name} server…`,
        'Waiting for the Studio server to come back online.'
      );
      let backOnline = false;
      for (let attempt = 0; attempt < 6; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 900));
        if (seq !== seqRef.current) return;
        try {
          const refreshed = await api.system.gitStatus(false);
          if (seq !== seqRef.current) return;
          setStatus(refreshed);
          setLastPull((prev) => (prev ? { ...prev, serverFilesChanged: false } : null));
          backOnline = true;
          break;
        } catch {
          // Still restarting — retry
        }
      }
      if (seq !== seqRef.current) return;
      if (backOnline) {
        notify('success', `${activeTarget.name} server is back online`);
      } else {
        setError('Server is still restarting — click Check Updates in a moment.');
      }
    } catch (err) {
      if (seq !== seqRef.current) return;
      onApiError?.(err);
      const msg = err instanceof Error ? err.message : 'Server restart failed.';
      setError(msg);
      notify('error', 'Restart failed', msg);
    } finally {
      if (seq === seqRef.current) {
        setRestarting(false);
      }
    }
  };

  const canPull =
    enabled &&
    Boolean(status?.isGitRepo) &&
    !status?.detached &&
    !status?.dirty &&
    !pulling &&
    !restarting;

  return (
    <Card>
      <CardHeader
        title={`Repository & Software Updates — ${activeTarget.name}`}
        description={
          activeTarget.isLocal
            ? 'Check git status or fast-forward pull the latest effects and code on this machine.'
            : `Trigger a safe git pull (--ff-only) directly on ${activeTarget.name} without SSHing in.`
        }
        action={
          enabled && (
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                loading={checking}
                disabled={loading || pulling || restarting}
                onClick={() => void loadStatus(true)}
                leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
              >
                Check Updates
              </Button>
              <Button
                variant="primary"
                size="sm"
                loading={pulling}
                disabled={!canPull}
                onClick={() => void handlePull()}
                leftIcon={<ArrowDownToLine className="h-3.5 w-3.5" />}
              >
                Pull Latest
              </Button>
              {status?.canRestart && (
                <Button
                  variant={lastPull?.serverFilesChanged ? 'secondary' : 'ghost'}
                  size="sm"
                  loading={restarting}
                  disabled={pulling}
                  onClick={() => void handleRestart()}
                  leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
                  title="Reload the Python web server process in-place"
                >
                  Restart Server
                </Button>
              )}
            </div>
          )
        }
      />

      <CardContent className="space-y-3">
        {!enabled ? (
          <p className="text-xs text-slate-400">
            Sign in to <span className="font-medium text-slate-200">{activeTarget.name}</span>{' '}
            above to inspect its git branch and pull updates remotely.
          </p>
        ) : loading && !status ? (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
            Reading repository status on {activeTarget.name}…
          </div>
        ) : error && !status ? (
          <div className="flex items-start gap-2 rounded-xl border border-rose-500/35 bg-rose-500/10 px-3.5 py-2.5 text-xs text-rose-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : status && !status.isGitRepo ? (
          <p className="text-xs text-slate-400">
            This installation is not a git clone, so in-app git pull is unavailable.
          </p>
        ) : status ? (
          <>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge tone="cyan">
                <GitBranch className="h-3 w-3" />
                {status.detached ? 'detached HEAD' : status.branch || 'unknown'}
              </Badge>

              {status.commit && (
                <Badge tone="neutral">
                  <GitCommitHorizontal className="h-3 w-3" />
                  <span className="font-mono">{status.commit}</span>
                </Badge>
              )}

              {status.behind !== null && status.behind > 0 ? (
                <Badge tone="amber">
                  {status.behind} commit{status.behind === 1 ? '' : 's'} behind
                </Badge>
              ) : status.behind === 0 ? (
                <Badge tone="emerald">
                  <CheckCircle2 className="h-3 w-3" />
                  Up to date
                </Badge>
              ) : null}

              {status.ahead !== null && status.ahead > 0 && (
                <Badge tone="neutral">{status.ahead} ahead</Badge>
              )}

              {status.dirty && (
                <Badge tone="amber">
                  <AlertTriangle className="h-3 w-3" />
                  Uncommitted local edits
                </Badge>
              )}
            </div>

            {status.commitMessage && (
              <div className="rounded-xl border border-slate-800/80 bg-surface-950/60 px-3.5 py-2.5 text-xs text-slate-300">
                <span className="text-slate-500">Latest commit: </span>
                <span className="text-slate-100">{status.commitMessage}</span>
                {status.remoteUrl && (
                  <div className="mt-1 truncate font-mono text-[11px] text-slate-500">
                    {status.remoteUrl}
                  </div>
                )}
              </div>
            )}

            {status.dirty && status.dirtyFiles.length > 0 && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2.5 text-xs text-amber-200">
                <p className="font-medium">
                  Pull disabled — tracked files have uncommitted local changes:
                </p>
                <p className="mt-1 font-mono text-[11px] text-amber-100/90">
                  {status.dirtyFiles.join(', ')}
                </p>
              </div>
            )}

            {status.fetchError && (
              <div className="rounded-xl border border-rose-500/35 bg-rose-500/10 px-3.5 py-2.5 text-xs text-rose-200">
                {status.fetchError}
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-rose-500/35 bg-rose-500/10 px-3.5 py-2.5 text-xs text-rose-200">
                {error}
              </div>
            )}

            {lastPull && (
              <div className="space-y-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-2.5 text-xs text-emerald-100">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">
                    {lastPull.updated
                      ? `Updated ${lastPull.beforeCommit} → ${lastPull.afterCommit} (${lastPull.totalChangedFiles} file${
                          lastPull.totalChangedFiles === 1 ? '' : 's'
                        })`
                      : 'Already up to date.'}
                  </span>
                  {lastPull.serverFilesChanged && lastPull.canRestart && (
                    <span className="text-[11px] text-amber-200">
                      Server Python code changed — click Restart Server to apply.
                    </span>
                  )}
                </div>
                {lastPull.playbackFilesChanged && (
                  <p className="text-[11px] text-emerald-200/90">
                    Matrix effect/runner code updated — stop and restart the playlist if it is
                    currently playing to pick up Python module changes.
                  </p>
                )}
                {lastPull.changedFiles.length > 0 && (
                  <div className="max-h-28 overflow-y-auto rounded-lg bg-surface-950/70 p-2 font-mono text-[11px] text-slate-300">
                    {lastPull.changedFiles.map((file) => (
                      <div key={file}>{file}</div>
                    ))}
                    {lastPull.totalChangedFiles > lastPull.changedFiles.length && (
                      <div className="text-slate-500">
                        +{lastPull.totalChangedFiles - lastPull.changedFiles.length} more files
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
