import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Grid2x2,
  Info,
  Loader2,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  Tv2,
} from 'lucide-react';
import { api } from '@/api/client';
import { Badge, Button, Select, useToast } from '@/components/ui';
import { paintLedPreviewCanvas } from '@/utils/smartCrop';
import type { EffectPreviewDiagnostic, EffectPreviewResponse } from '@/types/matrix';

const SIMULATED_SIZES = [
  { id: 'current', label: 'Current Matrix' },
  { id: '32x16', label: '32×16 (Micro)', width: 32, height: 16 },
  { id: '64x32', label: '64×32 (Compact)', width: 64, height: 32 },
  { id: '128x72', label: '128×72 (Standard)', width: 128, height: 72 },
  { id: '192x96', label: '192×96 (Large)', width: 192, height: 96 },
] as const;

function decodeBase64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) {
    out[i] = bin.charCodeAt(i);
  }
  return out;
}

export interface EffectLivePreviewProps {
  effectId: string;
  config: Record<string, unknown>;
  pixelWidth: number;
  pixelHeight: number;
  defaultLedDots: boolean;
  onApplyPatch?: (patch: Record<string, unknown>) => void;
}

/**
 * Reusable live LED preview panel for ANY effect implementing a server `preview()` hook.
 * Displays pixel-exact animated frames with LED dots, screen-size simulator, alignment guides,
 * smart capability diagnostics with 1-click fixes, and a live "Test on Matrix" action.
 */
export function EffectLivePreview({
  effectId,
  config,
  pixelWidth,
  pixelHeight,
  defaultLedDots,
  onApplyPatch,
}: EffectLivePreviewProps) {
  const { notify } = useToast();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rgbaScratchRef = useRef<Uint8ClampedArray | null>(null);
  const frameIndexRef = useRef(0);

  const [sizePreset, setSizePreset] = useState<string>('current');
  const [ledDots, setLedDots] = useState(defaultLedDots);
  const [showGuides, setShowGuides] = useState(false);
  const [playing, setPlaying] = useState(true);
  const [restartTick, setRestartTick] = useState(0);
  const [loading, setLoading] = useState(false);
  const [testingOnMatrix, setTestingOnMatrix] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<{
    meta: EffectPreviewResponse;
    rgbBytes: Uint8Array;
  } | null>(null);

  const targetDims = useMemo(() => {
    const match = SIMULATED_SIZES.find((s) => s.id === sizePreset);
    if (match && 'width' in match) {
      return { width: match.width, height: match.height, isSimulated: true };
    }
    return { width: pixelWidth, height: pixelHeight, isSimulated: false };
  }, [sizePreset, pixelWidth, pixelHeight]);

  const configSignature = useMemo(() => JSON.stringify(config), [config]);

  // Debounced server preview fetch
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const res = await api.effects.preview(
          effectId,
          {
            config: JSON.parse(configSignature) as Record<string, unknown>,
            width: targetDims.width,
            height: targetDims.height,
          },
          controller.signal
        );
        if (controller.signal.aborted) return;
        const rgbBytes = decodeBase64ToBytes(res.framesBase64);
        setPreviewData({ meta: res, rgbBytes });
        setError(null);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : 'Preview unavailable');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 130);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [effectId, configSignature, targetDims.width, targetDims.height]);

  // Animate decoded frames onto the LED preview canvas
  useEffect(() => {
    if (!previewData || !canvasRef.current) return;
    const { meta, rgbBytes } = previewData;
    const { width, height, frameCount, fps } = meta;
    const frameStride = width * height * 3;
    const neededRgba = width * height * 4;
    if (!rgbaScratchRef.current || rgbaScratchRef.current.length !== neededRgba) {
      rgbaScratchRef.current = new Uint8ClampedArray(neededRgba);
    }
    const rgba = rgbaScratchRef.current;

    const paintFrame = (idx: number) => {
      if (!canvasRef.current) return;
      const offset = (idx % Math.max(1, frameCount)) * frameStride;
      if (offset + frameStride > rgbBytes.length) return;
      for (let i = 0, j = 0; i < frameStride; i += 3, j += 4) {
        rgba[j] = rgbBytes[offset + i];
        rgba[j + 1] = rgbBytes[offset + i + 1];
        rgba[j + 2] = rgbBytes[offset + i + 2];
        rgba[j + 3] = 255;
      }
      paintLedPreviewCanvas(canvasRef.current, rgba, width, height, ledDots);
    };

    const safeFrameCount = Math.max(1, frameCount);
    const startIndex = frameIndexRef.current % safeFrameCount;
    frameIndexRef.current = startIndex;
    paintFrame(startIndex);
    if (frameCount <= 1 || !playing) return;

    let rafId = 0;
    const startMs = performance.now();
    const frameIntervalMs = 1000 / Math.max(1, fps);
    let lastIndex = startIndex;

    const tick = (now: number) => {
      const elapsedFrames = Math.floor((now - startMs) / frameIntervalMs);
      const idx = (startIndex + elapsedFrames) % safeFrameCount;
      if (idx !== lastIndex) {
        lastIndex = idx;
        frameIndexRef.current = idx;
        paintFrame(idx);
      }
      rafId = window.requestAnimationFrame(tick);
    };

    rafId = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(rafId);
  }, [previewData, ledDots, playing, restartTick]);

  const handleTestOnMatrix = async () => {
    setTestingOnMatrix(true);
    try {
      await api.playback.start({ effect: effectId, config });
      notify('success', 'Sent to matrix', `Testing ${effectId} live on your display.`);
    } catch (err) {
      notify(
        'error',
        'Could not play on matrix',
        err instanceof Error ? err.message : 'Unable to start live preview.'
      );
    } finally {
      setTestingOnMatrix(false);
    }
  };

  const diagnostics: EffectPreviewDiagnostic[] = previewData?.meta.diagnostics ?? [];
  const isAnimated = (previewData?.meta.frameCount ?? 0) > 1;

  return (
    <div className="space-y-3 rounded-2xl border border-slate-800/90 bg-surface-950/90 p-3.5">
      {/* Header + Screen Size Simulator */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Live LED Preview
          </span>
          {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-400" />}
          {targetDims.isSimulated && (
            <Badge tone="amber" className="text-[10px]">
              Simulated
            </Badge>
          )}
        </div>

        <div className="w-48">
          <Select
            aria-label="Preview screen size"
            value={sizePreset}
            onChange={(e) => setSizePreset(e.target.value)}
            className="min-h-0 h-8 py-1 font-mono text-[11px]"
            options={SIMULATED_SIZES.map((s) => ({
              value: s.id,
              label:
                s.id === 'current'
                  ? `My Matrix (${pixelWidth}×${pixelHeight})`
                  : s.label,
            }))}
          />
        </div>
      </div>

      {/* Matrix Canvas Stage */}
      <div className="relative flex min-h-[170px] items-center justify-center overflow-hidden rounded-xl border border-slate-800 bg-black p-3 shadow-inner shadow-black">
        <div className="relative inline-flex max-w-full items-center justify-center">
          <canvas
            ref={canvasRef}
            className="max-h-[230px] max-w-full rounded"
            style={{ imageRendering: 'pixelated' }}
          />
          {showGuides && previewData && (
            <div className="pointer-events-none absolute inset-0 rounded border border-cyan-400/35">
              <div className="absolute inset-y-0 left-1/2 w-px bg-cyan-400/30" />
              <div className="absolute inset-x-0 top-1/2 h-px bg-cyan-400/30" />
            </div>
          )}
        </div>
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80 px-4 text-center text-xs text-rose-300">
            {error}
          </div>
        )}
      </div>

      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          {isAnimated && (
            <>
              <Button
                variant="ghost"
                size="sm"
                className="w-[82px] justify-center"
                onClick={() => setPlaying((p) => !p)}
                leftIcon={
                  playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />
                }
              >
                {playing ? 'Pause' : 'Play'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                title="Restart preview loop"
                onClick={() => {
                  frameIndexRef.current = 0;
                  setPlaying(true);
                  setRestartTick((t) => t + 1);
                }}
                leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
              >
                Restart
              </Button>
            </>
          )}
          <button
            type="button"
            onClick={() => setLedDots((d) => !d)}
            className={`rounded-lg px-2 py-1 text-[11px] font-medium transition-colors cursor-pointer ${
              ledDots
                ? 'bg-cyan-500/15 text-cyan-200 ring-1 ring-cyan-500/35'
                : 'bg-surface-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            LED Dots
          </button>
          <button
            type="button"
            onClick={() => setShowGuides((g) => !g)}
            title="Toggle optical center guides"
            className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium transition-colors cursor-pointer ${
              showGuides
                ? 'bg-cyan-500/15 text-cyan-200 ring-1 ring-cyan-500/35'
                : 'bg-surface-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            <Grid2x2 className="h-3 w-3" />
            Guides
          </button>
        </div>

        <Button
          variant="secondary"
          size="sm"
          loading={testingOnMatrix}
          onClick={() => void handleTestOnMatrix()}
          leftIcon={<Tv2 className="h-3.5 w-3.5 text-emerald-300" />}
        >
          Test on Matrix
        </Button>
      </div>

      {/* Smart Capability Diagnostics & 1-Click Fixes */}
      {diagnostics.length > 0 && (
        <div className="space-y-2 border-t border-slate-800/80 pt-2.5">
          {diagnostics.map((diag, idx) => {
            const toneStyles =
              diag.level === 'warn'
                ? 'border-amber-500/35 bg-amber-500/10 text-amber-100'
                : diag.level === 'ok'
                  ? 'border-emerald-500/30 bg-emerald-500/8 text-emerald-100'
                  : 'border-cyan-500/30 bg-cyan-500/8 text-cyan-100';
            const Icon =
              diag.level === 'warn'
                ? AlertTriangle
                : diag.level === 'ok'
                  ? CheckCircle2
                  : Info;
            return (
              <div
                key={idx}
                className={`space-y-1.5 rounded-xl border px-3 py-2 text-xs ${toneStyles}`}
              >
                <div className="flex items-start gap-2">
                  <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span className="leading-snug">{diag.message}</span>
                </div>
                {diag.actions && diag.actions.length > 0 && onApplyPatch && (
                  <div className="flex flex-wrap gap-1.5 pl-5">
                    {diag.actions.map((action, aIdx) => (
                      <button
                        key={aIdx}
                        type="button"
                        onClick={() => onApplyPatch(action.patch)}
                        className="inline-flex items-center gap-1 rounded-md border border-white/20 bg-black/40 px-2 py-0.5 text-[11px] font-medium text-white transition-colors hover:bg-black/70 cursor-pointer"
                      >
                        <Sparkles className="h-3 w-3 text-cyan-300" />
                        {action.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
