import { useState, type FormEvent } from 'react';
import { KeyRound, LogOut, ShieldCheck } from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  Field,
  Input,
  SectionHeader,
  useToast,
} from '@/components/ui';
import type { AuthStatus } from '@/types/matrix';

interface SecurityPageProps {
  authStatus: AuthStatus;
  onChangePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  onLogout: () => Promise<void>;
}

export function SecurityPage({
  authStatus,
  onChangePassword,
  onLogout,
}: SecurityPageProps) {
  const { notify } = useToast();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword.length < 4) {
      setError('New password must be at least 4 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.');
      return;
    }
    setSaving(true);
    try {
      await onChangePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      notify(
        'success',
        'Password updated',
        'Your session was refreshed and any other signed-in devices were signed out.'
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to change password');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Security & Session"
        description="Manage your local access password and active HttpOnly cookie session."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Active Session"
            description="Authentication uses an HMAC-SHA256 signed HttpOnly cookie."
          />
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-xl border border-slate-800/80 bg-surface-950/60 px-4 py-3">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <span className="text-sm font-medium text-slate-200">Session Status</span>
              </div>
              <Badge tone="emerald">Authenticated</Badge>
            </div>

            <div className="space-y-2 rounded-xl border border-slate-800/80 bg-surface-950/60 px-4 py-3 text-xs text-slate-400">
              <div className="flex items-center justify-between">
                <span>Credential source</span>
                <span className="font-mono text-slate-200">
                  {authStatus.envManaged ? 'LED_MATRIX_PASSWORD env' : 'web/.auth.json'}
                </span>
              </div>
              {authStatus.expiresAt && (
                <div className="flex items-center justify-between">
                  <span>Session expires</span>
                  <span className="font-mono text-slate-200">
                    {new Date(authStatus.expiresAt * 1000).toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            <Button
              variant="danger"
              onClick={onLogout}
              leftIcon={<LogOut className="h-4 w-4" />}
            >
              Sign Out This Browser
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader
            title="Change Admin Password"
            description={
              authStatus.envManaged
                ? 'Password is controlled by the LED_MATRIX_PASSWORD environment variable.'
                : 'Changing the password also rotates the signing key and signs out other devices.'
            }
          />
          <CardContent>
            {authStatus.envManaged ? (
              <p className="text-xs leading-relaxed text-slate-400">
                To change the password, update <code className="text-cyan-300">LED_MATRIX_PASSWORD</code>{' '}
                in your environment and restart the web server.
              </p>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <Field label="Current Password" htmlFor="sec-current">
                  <Input
                    id="sec-current"
                    type="password"
                    autoComplete="current-password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    leftIcon={<KeyRound className="h-4 w-4" />}
                  />
                </Field>
                <Field label="New Password" htmlFor="sec-new">
                  <Input
                    id="sec-new"
                    type="password"
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                </Field>
                <Field label="Confirm New Password" htmlFor="sec-confirm">
                  <Input
                    id="sec-confirm"
                    type="password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </Field>

                {error && <p className="text-xs text-rose-400">{error}</p>}

                <Button
                  type="submit"
                  variant="primary"
                  loading={saving}
                  disabled={!currentPassword || !newPassword}
                >
                  Update Password
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
