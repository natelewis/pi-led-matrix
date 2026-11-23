import { useRef, useState, type FormEvent } from 'react';
import {
  CheckCircle2,
  KeyRound,
  Laptop,
  Lock,
  LogOut,
  Plus,
  Send,
  Server,
  Terminal,
  Trash2,
  Wifi,
} from 'lucide-react';
import { api } from '@/api/client';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  ConfirmDialog,
  Field,
  Input,
  Modal,
  SectionHeader,
  useToast,
} from '@/components/ui';
import type { MatrixTarget, TargetProbeResult, TargetsState } from '@/types/matrix';

export interface DevicesPageProps {
  targets: MatrixTarget[];
  activeTargetId: string;
  switching: boolean;
  onSyncTargetsState: (state: TargetsState) => void;
  onSelectTarget: (targetId: string) => Promise<unknown>;
  onAddTarget: (name: string, url: string) => Promise<MatrixTarget>;
  onRemoveTarget: (id: string) => Promise<unknown>;
  onLoginTarget: (id: string, password: string, setup?: boolean) => Promise<unknown>;
  onLogoutTarget: (id: string) => Promise<unknown>;
  onPushLocalConfig: (id: string) => Promise<unknown>;
}

export function DevicesPage({
  targets,
  activeTargetId,
  switching,
  onSyncTargetsState,
  onSelectTarget,
  onAddTarget,
  onRemoveTarget,
  onLoginTarget,
  onLogoutTarget,
  onPushLocalConfig,
}: DevicesPageProps) {
  const { notify } = useToast();

  // Add device form state
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [testingUrl, setTestingUrl] = useState(false);
  const [adding, setAdding] = useState(false);
  const [urlProbe, setUrlProbe] = useState<TargetProbeResult | null>(null);

  // Per-device probe & modal state
  const [deviceProbes, setDeviceProbes] = useState<Record<string, TargetProbeResult>>({});
  const [probingId, setProbingId] = useState<string | null>(null);
  const [loginTarget, setLoginTarget] = useState<MatrixTarget | null>(null);
  const [loginPassword, setLoginPassword] = useState('');
  const [loginConfirm, setLoginConfirm] = useState('');
  const [loginSetup, setLoginSetup] = useState(false);
  const [loginSubmitting, setLoginSubmitting] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const loginModalSeqRef = useRef(0);

  const [pushConfirmTarget, setPushConfirmTarget] = useState<MatrixTarget | null>(null);
  const [pushing, setPushing] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<MatrixTarget | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleTestNewUrl = async () => {
    if (!url.trim()) return;
    setTestingUrl(true);
    setUrlProbe(null);
    try {
      const res = await api.targets.testUrl(url.trim());
      setUrlProbe(res);
    } catch (err) {
      setUrlProbe({
        reachable: false,
        url: url.trim(),
        error: err instanceof Error ? err.message : 'Test failed.',
      });
    } finally {
      setTestingUrl(false);
    }
  };

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !url.trim()) return;
    setAdding(true);
    try {
      const created = await onAddTarget(name.trim(), url.trim());
      setName('');
      setUrl('');
      setUrlProbe(null);
      notify('success', `Added ${created.name}`, 'Sign in or switch to it to start controlling it.');
    } catch (err) {
      notify(
        'error',
        'Could not add device',
        err instanceof Error ? err.message : 'Check the URL and try again.'
      );
    } finally {
      setAdding(false);
    }
  };

  const handleTestSaved = async (target: MatrixTarget) => {
    setProbingId(target.id);
    try {
      const res = await api.targets.testSaved(target.id);
      if (res.targetsState) {
        onSyncTargetsState(res.targetsState);
      }
      setDeviceProbes((prev) => ({ ...prev, [target.id]: res }));
      if (res.reachable) {
        notify(
          'success',
          `${target.name} is reachable`,
          res.authenticated ? 'Remote session active.' : 'Sign in to authenticate.'
        );
      } else {
        notify('error', `${target.name} unreachable`, res.error);
      }
    } catch (err) {
      notify(
        'error',
        'Connection test failed',
        err instanceof Error ? err.message : 'Unable to reach remote device.'
      );
    } finally {
      setProbingId(null);
    }
  };

  const openLoginModal = async (target: MatrixTarget) => {
    const seq = ++loginModalSeqRef.current;
    setLoginTarget(target);
    setLoginPassword('');
    setLoginConfirm('');
    setLoginError(null);
    setLoginSetup(false);
    try {
      const res = await api.targets.testSaved(target.id);
      if (seq !== loginModalSeqRef.current) return;
      if (res.targetsState) {
        onSyncTargetsState(res.targetsState);
      }
      setDeviceProbes((prev) => ({ ...prev, [target.id]: res }));
      if (res.reachable && res.initialized === false) {
        setLoginSetup(true);
      }
    } catch {
      // Fall back to standard login
    }
  };

  const handleLoginSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!loginTarget || !loginPassword) return;
    if (loginSetup) {
      if (loginPassword.length < 4) {
        setLoginError('Password must be at least 4 characters.');
        return;
      }
      if (loginPassword !== loginConfirm) {
        setLoginError('Passwords do not match.');
        return;
      }
    }
    setLoginSubmitting(true);
    setLoginError(null);
    try {
      await onLoginTarget(loginTarget.id, loginPassword, loginSetup);
      notify('success', `Signed in to ${loginTarget.name}`);
      setLoginTarget(null);
      setLoginPassword('');
      setLoginConfirm('');
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : 'Sign-in failed.');
    } finally {
      setLoginSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Devices & Remote Sessions"
        description="Control a Raspberry Pi in another room from this Studio — switch targets seamlessly, live-mirror its frames, or push your local Mac config directly to the Pi."
      />

      {/* Saved Devices */}
      <Card>
        <CardHeader
          title="Connected Matrix Devices"
          description="Requests are proxied through your local Studio server so remote sessions stay secure without CORS or cookie issues."
        />
        <CardContent className="space-y-3">
          {targets.map((target) => {
            const active = target.id === activeTargetId;
            const probe = deviceProbes[target.id];
            return (
              <div
                key={target.id}
                className={`flex flex-wrap items-center justify-between gap-4 rounded-xl border px-4 py-3.5 transition-all ${
                  active
                    ? target.isLocal
                      ? 'border-cyan-400/60 bg-cyan-500/8'
                      : 'border-violet-400/60 bg-violet-500/10'
                    : 'border-slate-800 bg-surface-950/70 hover:border-slate-700'
                }`}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                      target.isLocal
                        ? 'bg-cyan-500/15 text-cyan-300'
                        : 'bg-violet-500/15 text-violet-300'
                    }`}
                  >
                    {target.isLocal ? (
                      <Laptop className="h-5 w-5" />
                    ) : (
                      <Server className="h-5 w-5" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-white">
                        {target.name}
                      </span>
                      {active && (
                        <Badge tone={target.isLocal ? 'cyan' : 'violet'}>Active</Badge>
                      )}
                      {!target.isLocal && (
                        <Badge tone={target.hasSession ? 'emerald' : 'amber'}>
                          {target.hasSession ? 'Signed in' : 'Locked'}
                        </Badge>
                      )}
                      {probe && (
                        <Badge tone={probe.reachable ? 'emerald' : 'rose'}>
                          {probe.reachable ? 'Online' : 'Offline'}
                        </Badge>
                      )}
                    </div>
                    <div className="mt-0.5 truncate font-mono text-xs text-slate-400">
                      {target.isLocal
                        ? 'Runs locally on this machine (virtual simulator or local GPIO)'
                        : target.url}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  {!active && (
                    <Button
                      variant="primary"
                      size="sm"
                      loading={switching}
                      onClick={() => void onSelectTarget(target.id)}
                    >
                      Switch To
                    </Button>
                  )}

                  {!target.isLocal && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        loading={probingId === target.id}
                        onClick={() => void handleTestSaved(target)}
                        leftIcon={<Wifi className="h-3.5 w-3.5" />}
                      >
                        Test
                      </Button>

                      {target.hasSession ? (
                        <>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setPushConfirmTarget(target)}
                            leftIcon={<Send className="h-3.5 w-3.5" />}
                            title="Overwrite this Pi's config.json with your local machine's config"
                          >
                            Push Local Config
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={async () => {
                              try {
                                await onLogoutTarget(target.id);
                                notify('info', `Signed out of ${target.name}`);
                              } catch (err) {
                                notify(
                                  'error',
                                  'Sign out failed',
                                  err instanceof Error ? err.message : undefined
                                );
                              }
                            }}
                            leftIcon={<LogOut className="h-3.5 w-3.5" />}
                          >
                            Sign Out
                          </Button>
                        </>
                      ) : (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => void openLoginModal(target)}
                          leftIcon={<KeyRound className="h-3.5 w-3.5" />}
                        >
                          Sign In
                        </Button>
                      )}

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDeleteTarget(target)}
                        title="Remove remote device"
                        className="text-slate-400 hover:text-rose-300"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Add Remote Device + Pi Setup Guide */}
      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader
            title="Add Remote Raspberry Pi"
            description="Point to any Pi running `make web` on your local network."
          />
          <CardContent>
            <form onSubmit={handleAdd} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Device Name" htmlFor="remote-name">
                  <Input
                    id="remote-name"
                    placeholder="Living Room Pi"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </Field>
                <Field
                  label="Studio URL"
                  htmlFor="remote-url"
                  description="Include port if not 80 (default 8080)."
                >
                  <Input
                    id="remote-url"
                    placeholder="http://raspberrypi.local:8080"
                    value={url}
                    onChange={(e) => {
                      setUrl(e.target.value);
                      setUrlProbe(null);
                    }}
                  />
                </Field>
              </div>

              {urlProbe && (
                <div
                  className={`flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-xs ${
                    urlProbe.reachable
                      ? 'border-emerald-500/35 bg-emerald-500/10 text-emerald-200'
                      : 'border-rose-500/35 bg-rose-500/10 text-rose-200'
                  }`}
                >
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>
                    {urlProbe.reachable
                      ? `Reachable at ${urlProbe.url} (${
                          urlProbe.initialized ? 'password configured' : 'ready for first-time setup'
                        }).`
                      : urlProbe.error}
                  </span>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  loading={testingUrl}
                  disabled={!url.trim()}
                  onClick={() => void handleTestNewUrl()}
                  leftIcon={<Wifi className="h-3.5 w-3.5" />}
                >
                  Test Connection
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  loading={adding}
                  disabled={!name.trim() || !url.trim()}
                  leftIcon={<Plus className="h-3.5 w-3.5" />}
                >
                  Add Device
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <Terminal className="h-4 w-4 text-cyan-400" />
                <span>Headless Pi Setup</span>
              </span>
            }
            description="Run both the LED matrix and Studio on boot."
          />
          <CardContent className="space-y-3 text-xs text-slate-400">
            <p className="leading-relaxed">
              Ready-to-use <code className="text-slate-200">systemd</code> service files are
              included in <code className="text-cyan-300">deploy/systemd/</code> so your Pi
              starts both the playlist runner and web API automatically on boot with shared{' '}
              <code className="text-slate-200">_runtime/</code> permissions.
            </p>
            <pre className="overflow-x-auto rounded-xl border border-slate-800 bg-black/60 p-3 font-mono text-[11px] leading-relaxed text-cyan-200">
{`# Quick test on the Pi:
make web

# Or install systemd units:
cat deploy/systemd/README.md`}
            </pre>
          </CardContent>
        </Card>
      </div>

      {/* Remote Sign-In Modal */}
      <Modal
        open={Boolean(loginTarget)}
        onClose={() => setLoginTarget(null)}
        title={
          loginSetup
            ? `Initialize ${loginTarget?.name ?? 'Remote Pi'}`
            : `Sign in to ${loginTarget?.name ?? 'Remote Pi'}`
        }
        description={loginTarget?.url ?? undefined}
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setLoginTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              loading={loginSubmitting}
              disabled={!loginPassword}
              onClick={(e) => void handleLoginSubmit(e)}
            >
              {loginSetup ? 'Set Password & Connect' : 'Sign In'}
            </Button>
          </>
        }
      >
        <form onSubmit={handleLoginSubmit} className="space-y-4">
          <Field
            label={loginSetup ? 'Choose Remote Admin Password' : 'Remote Admin Password'}
            htmlFor="modal-remote-pw"
            description="Your local Studio stores only the signed remote session token (0600), never the plaintext password."
          >
            <Input
              id="modal-remote-pw"
              type="password"
              autoFocus
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              leftIcon={<Lock className="h-4 w-4" />}
              placeholder="Enter remote password..."
            />
          </Field>
          {loginSetup && (
            <Field label="Confirm Password" htmlFor="modal-remote-confirm">
              <Input
                id="modal-remote-confirm"
                type="password"
                value={loginConfirm}
                onChange={(e) => setLoginConfirm(e.target.value)}
                placeholder="Re-enter remote password..."
              />
            </Field>
          )}
          {loginError && <p className="text-xs text-rose-400">{loginError}</p>}
        </form>
      </Modal>

      {/* Push Local Config Confirm */}
      <ConfirmDialog
        open={Boolean(pushConfirmTarget)}
        onClose={() => setPushConfirmTarget(null)}
        onConfirm={async () => {
          if (!pushConfirmTarget) return;
          setPushing(true);
          try {
            await onPushLocalConfig(pushConfirmTarget.id);
            notify(
              'success',
              `Pushed local config to ${pushConfirmTarget.name}`,
              'The remote Pi saved and hot-reloaded your local config.json.'
            );
            setPushConfirmTarget(null);
          } catch (err) {
            notify(
              'error',
              'Push failed',
              err instanceof Error ? err.message : 'Unable to push config.'
            );
          } finally {
            setPushing(false);
          }
        }}
        title={`Push local config to ${pushConfirmTarget?.name ?? 'remote Pi'}?`}
        description="This overwrites the remote device's config.json with your local machine's saved config.json and triggers a live hot-reload."
        confirmLabel="Push Config"
        loading={pushing}
      />

      {/* Delete Device Confirm */}
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={async () => {
          if (!deleteTarget) return;
          setDeleting(true);
          try {
            await onRemoveTarget(deleteTarget.id);
            notify('info', `Removed ${deleteTarget.name}`);
            setDeleteTarget(null);
          } catch (err) {
            notify(
              'error',
              'Could not remove device',
              err instanceof Error ? err.message : undefined
            );
          } finally {
            setDeleting(false);
          }
        }}
        title={`Remove ${deleteTarget?.name ?? 'device'}?`}
        description="This only removes the saved connection from your local Studio; nothing on the remote Raspberry Pi is modified."
        confirmLabel="Remove Device"
        danger
        loading={deleting}
      />
    </div>
  );
}
