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
import { Badge, Button, Card, CardContent, CardHeader, useToast } from '@/components/ui';
import type { GitUpdatesController } from '@/hooks/useGitUpdates';
import type { MatrixTarget } from '@/types/matrix';

export interface GitUpdateCardProps {
  activeTarget: MatrixTarget;
  enabled: boolean;
  gitUpdates: GitUpdatesController;
  onPullAndRestart: () => Promise<void>;
}

export function GitUpdateCard({
  activeTarget,
  enabled,
  gitUpdates,
  onPullAndRestart,
}: GitUpdateCardProps) {
  const { notify } = useToast();
  const {
    status,
    loading,
    checking,
    updating,
    restarting,
    phaseMessage,
    error,
    lastPull,
    updatesAvailable,
  } = gitUpdates;

  const handleCheck = async () => {
    const res = await gitUpdates.checkUpdates({ fetchRemote: true, silent: false });
    if (!res) return;
    if (res.fetchError) {
      notify('error', 'Could not check remote updates', res.fetchError);
    } else if (res.behind && res.behind > 0) {
      notify(
        'info',
        `${res.behind} update${res.behind === 1 ? '' : 's'} available on ${activeTarget.name}`,
        'Click Pull & Restart to apply.'
      );
    } else {
      notify('success', `${activeTarget.name} is up to date`);
    }
  };

  const handleRestartOnly = async () => {
    try {
      notify('info', `Restarting ${activeTarget.name} server…`);
      const backOnline = await gitUpdates.restartServer();
      if (backOnline) {
        notify('success', `${activeTarget.name} server is back online`);
      }
    } catch (err) {
      notify(
        'error',
        'Restart failed',
        err instanceof Error ? err.message : 'Unable to restart server.'
      );
    }
  };

  const canPull =
    enabled &&
    Boolean(status?.isGitRepo) &&
    !status?.detached &&
    !status?.dirty &&
    (updatesAvailable > 0 || status?.behind === null) &&
    !updating &&
    !restarting;

  const pullButtonLabel =
    updatesAvailable > 0
      ? `Pull & Restart (${updatesAvailable})`
      : status?.behind === 0
        ? 'Up to Date'
        : status?.canRestart
          ? 'Pull & Restart'
          : 'Pull Latest';

  return (
    <Card>
      <CardHeader
        title={`Repository & Software Updates — ${activeTarget.name}`}
        description={
          activeTarget.isLocal
            ? 'Automatically checks for new commits, pulls, rebuilds changed Python/UI dependencies, and restarts.'
            : `Automatically checks for new commits on ${activeTarget.name}, pulls, installs changed dependencies, and restarts headlessly.`
        }
        action={
          enabled && (
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                loading={checking}
                disabled={loading || updating || restarting}
                onClick={() => void handleCheck()}
                leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
              >
                Check Updates
              </Button>
              <Button
                variant={updatesAvailable > 0 ? 'primary' : 'secondary'}
                size="sm"
                loading={updating}
                disabled={!canPull}
                onClick={() => void onPullAndRestart()}
                leftIcon={
                  updatesAvailable === 0 && status?.behind === 0 ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : (
                    <ArrowDownToLine className="h-3.5 w-3.5" />
                  )
                }
              >
                {pullButtonLabel}
              </Button>
              {status?.canRestart && (
                <Button
                  variant="ghost"
                  size="sm"
                  loading={restarting && !updating}
                  disabled={updating || restarting}
                  onClick={() => void handleRestartOnly()}
                  leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
                  title="Reload the Python web server process in-place without pulling"
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
            above to check for git updates and pull remotely.
          </p>
        ) : phaseMessage ? (
          <div className="flex items-center gap-2 rounded-xl border border-cyan-500/35 bg-cyan-500/10 px-3.5 py-2.5 text-xs text-cyan-200">
            <Loader2 className="h-4 w-4 shrink-0 animate-spin text-cyan-300" />
            <span>{phaseMessage}</span>
          </div>
        ) : loading && !status ? (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
            Checking repository status on {activeTarget.name}…
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

              {updatesAvailable > 0 ? (
                <Badge tone="amber">
                  <ArrowDownToLine className="h-3 w-3" />
                  {updatesAvailable} update{updatesAvailable === 1 ? '' : 's'} available
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
              <div
                className={`space-y-2 rounded-xl border px-3.5 py-2.5 text-xs ${
                  lastPull.rebuildFailed
                    ? 'border-amber-500/35 bg-amber-500/10 text-amber-100'
                    : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100'
                }`}
              >
                <div className="font-medium">
                  {lastPull.updated
                    ? `Updated ${lastPull.beforeCommit} → ${lastPull.afterCommit} (${lastPull.totalChangedFiles} file${
                        lastPull.totalChangedFiles === 1 ? '' : 's'
                      })`
                    : 'Already up to date.'}
                </div>
                {lastPull.rebuildSteps && lastPull.rebuildSteps.length > 0 && (
                  <div className="space-y-1 rounded-lg bg-surface-950/60 p-2 text-[11px]">
                    {lastPull.rebuildSteps.map((step) => (
                      <div key={step.name} className="flex items-start gap-2">
                        <Badge
                          tone={
                            step.status === 'ok'
                              ? 'emerald'
                              : step.status === 'failed'
                                ? 'rose'
                                : 'neutral'
                          }
                        >
                          {step.name}
                        </Badge>
                        <span className="whitespace-pre-wrap text-slate-300">
                          {step.detail}
                        </span>
                      </div>
                    ))}
                  </div>
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
