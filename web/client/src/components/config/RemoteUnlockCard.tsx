import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  AlertTriangle,
  Laptop,
  Loader2,
  Lock,
  RefreshCw,
  Server,
} from 'lucide-react';
import { api } from '@/api/client';
import { Button, Card, CardContent, Field, Input } from '@/components/ui';
import type { MatrixTarget, TargetProbeResult } from '@/types/matrix';

export interface RemoteUnlockCardProps {
  target: MatrixTarget;
  unreachableError?: string | null;
  onLogin: (password: string, setup: boolean) => Promise<void>;
  onSwitchLocal: () => void;
  onRetry: () => void;
}

export function RemoteUnlockCard({
  target,
  unreachableError,
  onLogin,
  onSwitchLocal,
  onRetry,
}: RemoteUnlockCardProps) {
  const [probe, setProbe] = useState<TargetProbeResult | null>(null);
  const [probing, setProbing] = useState(true);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const probeSeqRef = useRef(0);

  const runProbe = async () => {
    const seq = ++probeSeqRef.current;
    setProbing(true);
    setError(null);
    try {
      const res = await api.targets.testSaved(target.id);
      if (seq !== probeSeqRef.current) return;
      setProbe(res);
      if (res.reachable && res.authenticated) {
        onRetry();
      }
    } catch (err) {
      if (seq !== probeSeqRef.current) return;
      setProbe({
        reachable: false,
        url: target.url || '',
        error: err instanceof Error ? err.message : 'Unable to reach remote device.',
      });
    } finally {
      if (seq === probeSeqRef.current) {
        setProbing(false);
      }
    }
  };

  useEffect(() => {
    void runProbe();
    return () => {
      probeSeqRef.current += 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target.id]);

  const isUnreachable =
    probe !== null ? !probe.reachable : Boolean(unreachableError);
  const needsSetup = probe?.reachable && probe.initialized === false;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (needsSetup) {
      if (password.length < 4) {
        setError('Password must be at least 4 characters.');
        return;
      }
      if (password !== confirm) {
        setError('Passwords do not match.');
        return;
      }
    }
    setSubmitting(true);
    try {
      await onLogin(password, Boolean(needsSetup));
      setPassword('');
      setConfirm('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Remote sign-in failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-md py-10">
      <Card elevated>
        <CardContent className="space-y-5 p-6">
          <div className="flex flex-col items-center text-center">
            <div
              className={`mb-3 flex h-12 w-12 items-center justify-center rounded-2xl ring-1 ${
                isUnreachable
                  ? 'bg-amber-500/15 text-amber-300 ring-amber-500/35'
                  : 'bg-violet-500/15 text-violet-300 ring-violet-500/35'
              }`}
            >
              {isUnreachable ? (
                <AlertTriangle className="h-6 w-6" />
              ) : (
                <Server className="h-6 w-6" />
              )}
            </div>
            <h2 className="text-lg font-semibold text-white">{target.name}</h2>
            <p className="mt-0.5 font-mono text-xs text-slate-400">{target.url}</p>
          </div>

          {probing ? (
            <div className="flex items-center justify-center gap-2 py-6 text-xs text-slate-400">
              <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
              Checking remote Studio server...
            </div>
          ) : isUnreachable ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs leading-relaxed text-amber-200">
                {unreachableError || probe?.error || 'Could not reach the remote device.'}
              </div>
              <p className="text-xs text-slate-400">
                Make sure <code className="text-slate-200">make web</code> (or the{' '}
                <code className="text-slate-200">pi-led-matrix-web</code> service) is running
                on your Raspberry Pi and reachable on your local network.
              </p>
              <div className="flex items-center justify-between gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onSwitchLocal}
                  leftIcon={<Laptop className="h-3.5 w-3.5" />}
                >
                  Back to Local
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => void runProbe()}
                  leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
                >
                  Retry Connection
                </Button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <p className="text-center text-xs text-slate-400">
                {needsSetup
                  ? 'This remote Pi does not have an admin password yet. Create one to initialize its remote session.'
                  : 'Enter the admin password configured on this remote Raspberry Pi.'}
              </p>

              <Field
                label={needsSetup ? 'Set Remote Admin Password' : 'Remote Admin Password'}
                htmlFor="remote-unlock-password"
              >
                <Input
                  id="remote-unlock-password"
                  type="password"
                  autoFocus
                  placeholder="Enter password..."
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  leftIcon={<Lock className="h-4 w-4" />}
                />
              </Field>

              {needsSetup && (
                <Field label="Confirm Password" htmlFor="remote-unlock-confirm">
                  <Input
                    id="remote-unlock-confirm"
                    type="password"
                    placeholder="Re-enter password..."
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                  />
                </Field>
              )}

              {error && (
                <div className="rounded-xl border border-rose-500/35 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
                  {error}
                </div>
              )}

              <div className="flex items-center justify-between gap-2 pt-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onSwitchLocal}
                  leftIcon={<Laptop className="h-3.5 w-3.5" />}
                >
                  Local Machine
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  loading={submitting}
                  disabled={!password}
                >
                  {needsSetup ? 'Initialize & Connect' : 'Unlock Device'}
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
