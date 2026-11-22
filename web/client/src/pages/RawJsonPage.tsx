import { useEffect, useRef, useState } from 'react';
import {
  Check,
  Copy,
  Download,
  RotateCcw,
  Upload,
} from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  ConfirmDialog,
  SectionHeader,
  useToast,
} from '@/components/ui';
import { copyToClipboard } from '@/utils/cliCommand';
import type { MatrixConfig } from '@/types/matrix';

interface RawJsonPageProps {
  config: MatrixConfig;
  configPath: string;
  saving: boolean;
  onApplyDraft: (next: MatrixConfig) => void;
  onResetToDefaults: () => Promise<void>;
}

export function RawJsonPage({
  config,
  configPath,
  saving,
  onApplyDraft,
  onResetToDefaults,
}: RawJsonPageProps) {
  const { notify } = useToast();
  const [text, setText] = useState(() => JSON.stringify(config, null, 4));
  const [parseError, setParseError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [confirmResetOpen, setConfirmResetOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setText(JSON.stringify(config, null, 4));
    setParseError(null);
  }, [config]);

  const handleApply = () => {
    try {
      const parsed = JSON.parse(text);
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        setParseError('Root value must be a JSON object.');
        return;
      }
      setParseError(null);
      onApplyDraft(parsed as MatrixConfig);
      notify('info', 'JSON applied to draft', 'Click Save Config in the top bar to write config.json.');
    } catch (err) {
      setParseError(err instanceof Error ? err.message : 'Invalid JSON');
    }
  };

  const handleCopy = async () => {
    try {
      await copyToClipboard(text);
      setCopied(true);
      notify('success', 'Copied JSON to clipboard');
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      notify('error', 'Copy failed', 'Could not access clipboard.');
    }
  };

  const handleDownload = () => {
    const blob = new Blob([text + '\n'], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'config.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const content = await file.text();
      const parsed = JSON.parse(content);
      setText(JSON.stringify(parsed, null, 4));
      onApplyDraft(parsed as MatrixConfig);
      notify('info', `Imported ${file.name}`, 'Review and click Save Config to persist.');
    } catch {
      notify('error', 'Import failed', 'Selected file is not valid JSON.');
    } finally {
      e.target.value = '';
    }
  };

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Raw JSON Configuration"
        description="Inspect, import, export, or directly edit your config.json payload."
        actions={
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={handleImportFile}
            />
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Upload className="h-3.5 w-3.5" />}
              onClick={() => fileInputRef.current?.click()}
            >
              Import
            </Button>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Download className="h-3.5 w-3.5" />}
              onClick={handleDownload}
            >
              Export
            </Button>
            <Button
              variant="danger"
              size="sm"
              leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
              onClick={() => setConfirmResetOpen(true)}
            >
              Reset to Defaults
            </Button>
          </>
        }
      />

      <Card>
        <CardHeader
          title="config.json"
          description={configPath || 'Repository root config.json'}
          action={
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                leftIcon={
                  copied ? (
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )
                }
              >
                {copied ? 'Copied' : 'Copy'}
              </Button>
              <Button variant="secondary" size="sm" onClick={handleApply}>
                Apply to Draft
              </Button>
            </div>
          }
        />
        <CardContent className="space-y-3">
          <textarea
            rows={24}
            spellCheck={false}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setParseError(null);
            }}
            className="w-full rounded-xl border border-slate-800 bg-surface-950 p-4 font-mono text-xs leading-relaxed text-slate-100 focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
          />
          {parseError && (
            <div className="rounded-xl border border-rose-500/35 bg-rose-500/10 px-3.5 py-2.5 font-mono text-xs text-rose-300">
              {parseError}
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmResetOpen}
        onClose={() => setConfirmResetOpen(false)}
        onConfirm={async () => {
          await onResetToDefaults();
          setConfirmResetOpen(false);
        }}
        title="Reset config.json to defaults?"
        description="This overwrites config.json with the factory settings from default_config.json, including the default playlist."
        confirmLabel="Reset Configuration"
        danger
        loading={saving}
      />
    </div>
  );
}
