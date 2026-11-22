import { useState, type FormEvent } from 'react';
import { Eye, EyeOff, Grid3X3, KeyRound, Lock, ShieldCheck } from 'lucide-react';
import { Button, Card, CardContent, Field, Input } from '@/components/ui';

interface AuthPageProps {
  initialized: boolean;
  onSetup: (password: string) => Promise<unknown>;
  onLogin: (password: string) => Promise<unknown>;
}

export function AuthPage({ initialized, onSetup, onLogin }: AuthPageProps) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!initialized) {
      if (password.length < 4) {
        setError('Please choose a password of at least 4 characters.');
        return;
      }
      if (password !== confirm) {
        setError('Passwords do not match.');
        return;
      }
    }

    setSubmitting(true);
    try {
      if (initialized) {
        await onLogin(password);
      } else {
        await onSetup(password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-surface-950 px-4 py-12">
      {/* Subtle ambient glow */}
      <div className="pointer-events-none absolute -top-32 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-cyan-500/10 blur-3xl" />

      <div className="relative w-full max-w-md space-y-6">
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400/20 to-emerald-400/20 text-cyan-300 ring-1 ring-cyan-400/35 shadow-lg shadow-cyan-500/10">
            <Grid3X3 className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">
            LED Matrix Studio
          </h1>
          <p className="mt-1.5 text-sm text-slate-400">
            {initialized
              ? 'Sign in to configure your Raspberry Pi LED matrix.'
              : 'Create a local admin password to protect your matrix configuration.'}
          </p>
        </div>

        <Card elevated>
          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <Field
                label={initialized ? 'Admin Password' : 'Choose Admin Password'}
                htmlFor="auth-password"
                description={
                  initialized
                    ? undefined
                    : 'Stored locally as a salted PBKDF2 hash. Sessions use an HttpOnly cookie.'
                }
              >
                <Input
                  id="auth-password"
                  type={showPassword ? 'text' : 'password'}
                  autoFocus
                  autoComplete={initialized ? 'current-password' : 'new-password'}
                  placeholder="Enter password..."
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  leftIcon={<Lock className="h-4 w-4" />}
                  rightSlot={
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      className="text-slate-400 hover:text-slate-200 cursor-pointer"
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  }
                />
              </Field>

              {!initialized && (
                <Field label="Confirm Password" htmlFor="auth-confirm">
                  <Input
                    id="auth-confirm"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Re-enter password..."
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    leftIcon={<KeyRound className="h-4 w-4" />}
                  />
                </Field>
              )}

              {error && (
                <div className="rounded-xl border border-rose-500/35 bg-rose-500/10 px-3.5 py-2.5 text-xs text-rose-300">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                variant="primary"
                size="lg"
                loading={submitting}
                disabled={!password}
                className="w-full"
              >
                {initialized ? 'Sign In' : 'Set Password & Continue'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="flex items-center justify-center gap-2 text-xs text-slate-500">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-400/80" />
          <span>Local LAN session secured via signed HttpOnly cookie</span>
        </div>
      </div>
    </div>
  );
}
