import { useEffect, useRef, useState } from 'react';
import { Radio, Tv2 } from 'lucide-react';
import { api } from '@/api/client';
import { Badge } from '@/components/ui';
import { paintLedPreviewCanvas } from '@/utils/smartCrop';

export interface LiveMatrixMirrorProps {
  active: boolean;
  isPlaying: boolean;
  ledDots: boolean;
  targetName: string;
  onApiError?: (err: unknown) => boolean;
}

/**
 * Streams live RGB frame snapshots (~6-7 FPS) from the active local or remote
 * matrix via `/api/playback/frame` and renders them with crisp LED dots.
 */
export function LiveMatrixMirror({
  active,
  isPlaying,
  ledDots,
  targetName,
  onApiError,
}: LiveMatrixMirrorProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rgbaScratchRef = useRef<Uint8ClampedArray | null>(null);
  const [frameInfo, setFrameInfo] = useState<{ width: number; height: number } | null>(
    null
  );
  const [hasFrame, setHasFrame] = useState(false);

  useEffect(() => {
    if (!active || !isPlaying) {
      setHasFrame(false);
      return;
    }

    let cancelled = false;
    let inFlight = false;
    let consecutiveErrors = 0;
    let timerId: number | null = null;
    let controller: AbortController | null = null;

    const scheduleNext = (delayMs: number) => {
      if (cancelled) return;
      timerId = window.setTimeout(() => void pullFrame(), delayMs);
    };

    const pullFrame = async () => {
      if (cancelled || inFlight) return;
      if (document.visibilityState !== 'visible') {
        scheduleNext(500);
        return;
      }
      inFlight = true;
      controller = new AbortController();
      let nextDelay = 150;
      try {
        const frame = await api.playback.fetchFrame(controller.signal);
        if (cancelled) return;
        consecutiveErrors = 0;
        if (!frame) {
          setHasFrame(false);
          nextDelay = 400;
          return;
        }
        const pixelCount = frame.width * frame.height;
        const needed = pixelCount * 4;
        if (!rgbaScratchRef.current || rgbaScratchRef.current.length !== needed) {
          rgbaScratchRef.current = new Uint8ClampedArray(needed);
        }
        const rgba = rgbaScratchRef.current;
        const rgb = frame.rgbBytes;
        for (let i = 0, j = 0; i < rgb.length; i += 3, j += 4) {
          rgba[j] = rgb[i];
          rgba[j + 1] = rgb[i + 1];
          rgba[j + 2] = rgb[i + 2];
          rgba[j + 3] = 255;
        }
        if (canvasRef.current) {
          paintLedPreviewCanvas(
            canvasRef.current,
            rgba,
            frame.width,
            frame.height,
            ledDots
          );
        }
        setHasFrame(true);
        setFrameInfo((prev) =>
          prev && prev.width === frame.width && prev.height === frame.height
            ? prev
            : { width: frame.width, height: frame.height }
        );
      } catch (err) {
        if (!cancelled && !(err instanceof DOMException && err.name === 'AbortError')) {
          consecutiveErrors += 1;
          nextDelay = Math.min(3000, 300 * Math.pow(2, consecutiveErrors - 1));
          onApiError?.(err);
        }
      } finally {
        inFlight = false;
        scheduleNext(nextDelay);
      }
    };

    void pullFrame();

    return () => {
      cancelled = true;
      if (timerId !== null) window.clearTimeout(timerId);
      controller?.abort();
    };
  }, [active, isPlaying, ledDots, onApiError]);

  if (!isPlaying) {
    return (
      <div className="flex min-h-[210px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-800 bg-black/70 px-4 py-8 text-center">
        <Tv2 className="mb-2.5 h-6 w-6 text-slate-500" />
        <div className="text-xs font-medium text-slate-300">
          {targetName} is currently stopped
        </div>
        <p className="mt-1 max-w-xs text-[11px] text-slate-500">
          Start the playlist to watch a real-time pixel mirror right here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      <div className="relative flex min-h-[210px] items-center justify-center overflow-hidden rounded-xl border border-slate-800 bg-black p-3">
        <canvas
          ref={canvasRef}
          className={`max-h-[240px] max-w-full rounded ${hasFrame ? 'block' : 'hidden'}`}
          style={{ imageRendering: 'pixelated' }}
        />
        {!hasFrame && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Radio className="h-4 w-4 animate-pulse text-cyan-400" />
            Waiting for live frames from {targetName}...
          </div>
        )}
        {hasFrame && (
          <div className="pointer-events-none absolute left-2.5 top-2.5">
            <Badge tone="emerald" className="bg-black/75 backdrop-blur-xs">
              LIVE MIRROR
            </Badge>
          </div>
        )}
      </div>
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span className="font-mono">
          {frameInfo ? `${frameInfo.width}×${frameInfo.height} live stream` : 'Connecting...'}
        </span>
        <span className="text-[11px] text-slate-500">
          Mirroring {targetName} (~6 FPS)
        </span>
      </div>
    </div>
  );
}
