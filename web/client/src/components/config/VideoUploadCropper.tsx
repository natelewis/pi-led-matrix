import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Crop,
  Film,
  Maximize2,
  Move,
  Pause,
  Play,
  Scissors,
  Sparkles,
  StretchHorizontal,
  Upload,
  X,
} from 'lucide-react';
import { api } from '@/api/client';
import {
  Badge,
  Button,
  Field,
  Input,
  NumberInput,
  Slider,
  useToast,
} from '@/components/ui';
import type { UploadedVideoMeta } from '@/types/matrix';
import {
  analyzeSmartCropSource,
  computeCropRect,
  paintLedPreviewCanvas,
  renderMatrixSource,
  type ImageFitMode,
  type SmartCropAnalysis,
} from '@/utils/smartCrop';

export interface VideoUploadCropperProps {
  targetWidth: number;
  targetHeight: number;
  ledDots?: boolean;
  onUploaded: (video: UploadedVideoMeta, allFiles: UploadedVideoMeta[]) => void;
  onCancel?: () => void;
}

const FIT_MODES: { id: ImageFitMode; label: string; icon: typeof Crop }[] = [
  { id: 'crop', label: 'Smart Crop', icon: Crop },
  { id: 'contain', label: 'Fit (Pad)', icon: Maximize2 },
  { id: 'stretch', label: 'Stretch', icon: StretchHorizontal },
];

function formatDuration(sec: number): string {
  if (!Number.isFinite(sec) || sec <= 0) return '0:00';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function VideoUploadCropper({
  targetWidth,
  targetHeight,
  ledDots = true,
  onUploaded,
  onCancel,
}: VideoUploadCropperProps) {
  const { notify } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const previewCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const offscreenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);

  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [videoDims, setVideoDims] = useState<{ w: number; h: number } | null>(null);
  const [duration, setDuration] = useState<number>(0);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const [filename, setFilename] = useState('');
  const [analysis, setAnalysis] = useState<SmartCropAnalysis | null>(null);
  const [fitMode, setFitMode] = useState<ImageFitMode>('crop');
  const [focalX, setFocalX] = useState(0.5);
  const [focalY, setFocalY] = useState(0.5);
  const [zoom, setZoom] = useState(1);

  const [trimEnabled, setTrimEnabled] = useState(false);
  const [startSec, setStartSec] = useState(0);
  const [endSec, setEndSec] = useState(0);
  const [previewUnavailable, setPreviewUnavailable] = useState(false);
  const [uploading, setUploading] = useState(false);

  const analyzedRef = useRef(false);
  const analyzeTimerRef = useRef<number | null>(null);
  const lastUiTimeUpdateRef = useRef(0);
  const dragStateRef = useRef<{
    startX: number;
    startY: number;
    startFocalX: number;
    startFocalY: number;
  } | null>(null);

  useEffect(() => {
    return () => {
      if (sourceUrl) URL.revokeObjectURL(sourceUrl);
      if (analyzeTimerRef.current !== null) {
        window.clearTimeout(analyzeTimerRef.current);
      }
    };
  }, [sourceUrl]);

  const drawCurrentFrame = useCallback(() => {
    const video = videoRef.current;
    const preview = previewCanvasRef.current;
    if (!video || !preview || !videoDims || video.readyState < 2) return;

    if (!offscreenCanvasRef.current) {
      offscreenCanvasRef.current = document.createElement('canvas');
    }
    const { rgbaBytes } = renderMatrixSource(
      video,
      videoDims.w,
      videoDims.h,
      targetWidth,
      targetHeight,
      { fitMode, focalX, focalY, zoom },
      offscreenCanvasRef.current
    );
    paintLedPreviewCanvas(preview, rgbaBytes, targetWidth, targetHeight, ledDots);
  }, [videoDims, targetWidth, targetHeight, fitMode, focalX, focalY, zoom, ledDots]);

  // Continuously update LED preview while playing; throttle React scrubber updates (~6Hz)
  useEffect(() => {
    if (!isPlaying) {
      drawCurrentFrame();
      return;
    }
    let rafId = 0;
    const tick = (ts: number) => {
      drawCurrentFrame();
      if (videoRef.current && ts - lastUiTimeUpdateRef.current >= 160) {
        lastUiTimeUpdateRef.current = ts;
        setCurrentTime(videoRef.current.currentTime);
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [isPlaying, drawCurrentFrame]);

  // Redraw whenever crop/fit/zoom/dots change while paused
  useEffect(() => {
    drawCurrentFrame();
  }, [drawCurrentFrame]);

  const runSmartAnalysisOnVideo = useCallback(() => {
    const video = videoRef.current;
    if (!video || video.videoWidth <= 0 || video.videoHeight <= 0) return;
    const result = analyzeSmartCropSource(
      video,
      video.videoWidth,
      video.videoHeight,
      targetWidth,
      targetHeight,
      'Video'
    );
    setAnalysis(result);
    setFocalX(result.focalX);
    setFocalY(result.focalY);
    setZoom(1);
    drawCurrentFrame();
  }, [targetWidth, targetHeight, drawCurrentFrame]);

  const loadFile = useCallback(
    (file: File) => {
      const looksLikeVideo =
        file.type.startsWith('video/') ||
        /\.(mp4|mov|webm|mkv|avi|m4v)$/i.test(file.name);
      if (!looksLikeVideo) {
        notify('error', 'Unsupported file', 'Please choose a video file (MP4, MOV, WebM, AVI, MKV).');
        return;
      }

      const nextUrl = URL.createObjectURL(file);
      analyzedRef.current = false;
      setSourceUrl(nextUrl);
      setSelectedFile(file);
      setFilename(file.name.replace(/\.[^.]+$/, ''));
      setVideoDims(null);
      setDuration(0);
      setCurrentTime(0);
      setIsPlaying(false);
      setAnalysis(null);
      setPreviewUnavailable(false);
      setFitMode('crop');
      setFocalX(0.5);
      setFocalY(0.5);
      setZoom(1);
      setTrimEnabled(false);
      setStartSec(0);
      setEndSec(0);
    },
    [notify]
  );

  const handleLoadedMetadata = () => {
    const video = videoRef.current;
    if (!video) return;
    const w = video.videoWidth;
    const h = video.videoHeight;
    const dur = Number.isFinite(video.duration) ? video.duration : 0;
    setVideoDims({ w, h });
    setDuration(dur);
    setEndSec(Math.round(dur * 10) / 10);

    const sampleTime = dur > 0.6 ? Math.min(dur * 0.2, 1.2) : 0;
    if (sampleTime > 0) {
      video.currentTime = sampleTime;
    } else if (!analyzedRef.current) {
      analyzedRef.current = true;
      if (analyzeTimerRef.current !== null) {
        window.clearTimeout(analyzeTimerRef.current);
      }
      analyzeTimerRef.current = window.setTimeout(() => {
        analyzeTimerRef.current = null;
        runSmartAnalysisOnVideo();
      }, 50);
    }
  };

  const handleSeeked = () => {
    const video = videoRef.current;
    if (!video) return;
    setCurrentTime(video.currentTime);
    if (!analyzedRef.current && video.readyState >= 2) {
      analyzedRef.current = true;
      runSmartAnalysisOnVideo();
    } else {
      drawCurrentFrame();
    }
  };

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => setIsPlaying(false));
    } else {
      video.pause();
      setIsPlaying(false);
    }
  };

  const cropRect = useMemo(() => {
    if (!videoDims) return null;
    return computeCropRect(
      videoDims.w,
      videoDims.h,
      targetWidth,
      targetHeight,
      focalX,
      focalY,
      zoom
    );
  }, [videoDims, targetWidth, targetHeight, focalX, focalY, zoom]);

  const cropPercent = useMemo(() => {
    if (!videoDims || !cropRect) return null;
    return {
      left: (cropRect.x / videoDims.w) * 100,
      top: (cropRect.y / videoDims.h) * 100,
      width: (cropRect.width / videoDims.w) * 100,
      height: (cropRect.height / videoDims.h) * 100,
    };
  }, [videoDims, cropRect]);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (fitMode !== 'crop' || !stageRef.current) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    dragStateRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startFocalX: focalX,
      startFocalY: focalY,
    };
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragStateRef.current || !stageRef.current) return;
    const bounds = stageRef.current.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) return;

    const dx = (e.clientX - dragStateRef.current.startX) / bounds.width;
    const dy = (e.clientY - dragStateRef.current.startY) / bounds.height;

    setFocalX(Math.max(0, Math.min(1, dragStateRef.current.startFocalX + dx)));
    setFocalY(Math.max(0, Math.min(1, dragStateRef.current.startFocalY + dy)));
  };

  const handlePointerUp = () => {
    dragStateRef.current = null;
  };

  const trimInvalid = trimEnabled && (startSec < 0 || endSec <= startSec);

  const handleUpload = async () => {
    if (!selectedFile) return;
    if (trimInvalid) {
      notify('error', 'Invalid trim range', 'End time must be greater than start time.');
      return;
    }
    setUploading(true);
    try {
      const ext = selectedFile.name.includes('.')
        ? selectedFile.name.slice(selectedFile.name.lastIndexOf('.'))
        : '.mp4';
      const baseFilename = (filename.trim() || 'video') + ext;

      const res = await api.effects.video.upload(selectedFile, {
        filename: baseFilename,
        width: targetWidth,
        height: targetHeight,
        fitMode,
        cropX: fitMode === 'crop' && cropRect ? cropRect.x : undefined,
        cropY: fitMode === 'crop' && cropRect ? cropRect.y : undefined,
        cropW: fitMode === 'crop' && cropRect ? cropRect.width : undefined,
        cropH: fitMode === 'crop' && cropRect ? cropRect.height : undefined,
        startSec: trimEnabled ? startSec : undefined,
        endSec: trimEnabled ? endSec : undefined,
      });

      notify(
        'success',
        'Video uploaded & resized',
        `Saved ${res.video.file} (${targetWidth}×${targetHeight} MP4).`
      );
      onUploaded(res.video, res.files);
    } catch (err) {
      notify(
        'error',
        'Video upload failed',
        err instanceof Error ? err.message : 'Unable to process video.'
      );
    } finally {
      setUploading(false);
    }
  };

  const clearSelection = () => {
    setSourceUrl(null);
    setSelectedFile(null);
    setVideoDims(null);
    setAnalysis(null);
    setPreviewUnavailable(false);
    setFilename('');
    setIsPlaying(false);
  };

  if (!selectedFile || !sourceUrl) {
    return (
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDraggingFile(true);
        }}
        onDragLeave={() => setIsDraggingFile(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDraggingFile(false);
          const file = e.dataTransfer.files?.[0];
          if (file) loadFile(file);
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-all ${
          isDraggingFile
            ? 'border-cyan-400 bg-cyan-500/10'
            : 'border-slate-700/90 bg-surface-950/60 hover:border-slate-500 hover:bg-surface-950'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*,.mp4,.mov,.webm,.avi,.mkv,.m4v"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) loadFile(file);
            e.target.value = '';
          }}
        />
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-500/12 text-cyan-300 ring-1 ring-cyan-500/30">
          <Film className="h-6 w-6" />
        </div>
        <div className="text-sm font-medium text-white">
          Drop a video here or click to browse
        </div>
        <p className="mt-1 max-w-md text-xs text-slate-400">
          Transcodes via <code className="text-slate-300">ffmpeg</code> to exact{' '}
          <span className="font-mono text-cyan-300">
            {targetWidth}×{targetHeight}
          </span>{' '}
          MP4 inside <code className="text-slate-300">src/effects/video/_uploads/</code>.
          Smart-crops mismatched aspect ratios automatically.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Smart analysis banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-cyan-500/25 bg-cyan-500/8 px-3.5 py-2.5 text-xs">
        <div className="flex items-center gap-2 text-cyan-100">
          <Sparkles className="h-4 w-4 shrink-0 text-cyan-300" />
          <span>
            {previewUnavailable
              ? 'Browser cannot preview this codec directly — ffmpeg will still transcode & center-crop it on upload.'
              : analysis
                ? analysis.summary
                : 'Analyzing video frame for smart crop framing...'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {videoDims && (
            <Badge tone="neutral" className="font-mono">
              {videoDims.w}×{videoDims.h} → {targetWidth}×{targetHeight}
            </Badge>
          )}
          <button
            type="button"
            onClick={clearSelection}
            title="Pick a different video"
            className="rounded-md p-1 text-slate-400 hover:bg-surface-800 hover:text-white cursor-pointer"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Fit Mode Selector + Focal Presets */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex rounded-xl border border-slate-800 bg-surface-950 p-1">
          {FIT_MODES.map((mode) => {
            const Icon = mode.icon;
            const active = fitMode === mode.id;
            return (
              <button
                key={mode.id}
                type="button"
                onClick={() => setFitMode(mode.id)}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                  active
                    ? 'bg-cyan-500/20 text-cyan-200 ring-1 ring-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {mode.label}
              </button>
            );
          })}
        </div>

        {fitMode === 'crop' && analysis && (
          <div className="flex flex-wrap items-center gap-1">
            <button
              type="button"
              onClick={runSmartAnalysisOnVideo}
              title="Re-analyze smart crop on current video frame"
              className="rounded-lg border border-slate-800 bg-surface-950 px-2 py-1 text-[11px] font-medium text-cyan-300 hover:border-cyan-500/40 cursor-pointer"
            >
              Smart Frame
            </button>
            <button
              type="button"
              onClick={() => {
                setFocalX(0.5);
                setFocalY(0.5);
              }}
              className="rounded-lg border border-slate-800 bg-surface-950 px-2 py-1 text-[11px] text-slate-300 hover:border-slate-600 cursor-pointer"
            >
              Center
            </button>
            {analysis.ratioMatch === 'taller' && (
              <>
                <button
                  type="button"
                  onClick={() => setFocalY(0.15)}
                  className="rounded-lg border border-slate-800 bg-surface-950 px-2 py-1 text-[11px] text-slate-300 hover:border-slate-600 cursor-pointer"
                >
                  Top
                </button>
                <button
                  type="button"
                  onClick={() => setFocalY(0.85)}
                  className="rounded-lg border border-slate-800 bg-surface-950 px-2 py-1 text-[11px] text-slate-300 hover:border-slate-600 cursor-pointer"
                >
                  Bottom
                </button>
              </>
            )}
            {analysis.ratioMatch === 'wider' && (
              <>
                <button
                  type="button"
                  onClick={() => setFocalX(0.15)}
                  className="rounded-lg border border-slate-800 bg-surface-950 px-2 py-1 text-[11px] text-slate-300 hover:border-slate-600 cursor-pointer"
                >
                  Left
                </button>
                <button
                  type="button"
                  onClick={() => setFocalX(0.85)}
                  className="rounded-lg border border-slate-800 bg-surface-950 px-2 py-1 text-[11px] text-slate-300 hover:border-slate-600 cursor-pointer"
                >
                  Right
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Dual Preview: Interactive Video Crop Stage + Live Animated LED Preview */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span className="font-medium text-slate-300">Source & Crop Region</span>
            {fitMode === 'crop' && (
              <span className="inline-flex items-center gap-1 text-slate-500">
                <Move className="h-3 w-3" /> Drag to adjust
              </span>
            )}
          </div>
          <div className="flex min-h-[190px] items-center justify-center rounded-xl border border-slate-800 bg-black/70 p-2">
            <div
              ref={stageRef}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerCancel={handlePointerUp}
              className={`relative inline-block max-h-[220px] select-none overflow-hidden rounded-lg ${
                fitMode === 'crop' ? 'cursor-move touch-none' : ''
              }`}
            >
              <video
                ref={videoRef}
                src={sourceUrl}
                muted
                loop
                playsInline
                preload="auto"
                onLoadedMetadata={handleLoadedMetadata}
                onSeeked={handleSeeked}
                onLoadedData={drawCurrentFrame}
                onEnded={() => setIsPlaying(false)}
                onError={() => setPreviewUnavailable(true)}
                className="block max-h-[220px] max-w-full object-contain"
              />
              {fitMode === 'crop' && cropPercent && (
                <div
                  className="pointer-events-none absolute border-2 border-cyan-400 shadow-[0_0_0_9999px_rgba(0,0,0,0.62)]"
                  style={{
                    left: `${cropPercent.left}%`,
                    top: `${cropPercent.top}%`,
                    width: `${cropPercent.width}%`,
                    height: `${cropPercent.height}%`,
                  }}
                >
                  <div className="absolute inset-y-0 left-1/3 border-l border-white/20" />
                  <div className="absolute inset-y-0 left-2/3 border-l border-white/20" />
                  <div className="absolute inset-x-0 top-1/3 border-t border-white/20" />
                  <div className="absolute inset-x-0 top-2/3 border-t border-white/20" />
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span className="font-medium text-slate-300">Live LED Matrix Preview</span>
            <span className="font-mono text-cyan-300">
              {targetWidth}×{targetHeight} px
            </span>
          </div>
          <div className="flex min-h-[190px] items-center justify-center rounded-xl border border-slate-800 bg-black p-3">
            <canvas
              ref={previewCanvasRef}
              className="max-h-[205px] max-w-full rounded border border-slate-800/80"
              style={{ imageRendering: 'pixelated' }}
            />
          </div>
        </div>
      </div>

      {/* Video playback scrubber */}
      {duration > 0 && (
        <div className="flex items-center gap-3 rounded-xl border border-slate-800/90 bg-surface-950/70 px-3 py-2">
          <button
            type="button"
            onClick={togglePlay}
            aria-label={isPlaying ? 'Pause preview' : 'Play preview'}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-cyan-500/15 text-cyan-300 hover:bg-cyan-500/25 cursor-pointer"
          >
            {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          </button>
          <input
            type="range"
            min={0}
            max={duration}
            step={0.05}
            value={Math.min(duration, currentTime)}
            onChange={(e) => {
              const next = parseFloat(e.target.value);
              setCurrentTime(next);
              if (videoRef.current) {
                videoRef.current.currentTime = next;
              }
            }}
            className="led-slider flex-1"
          />
          <span className="shrink-0 font-mono text-[11px] text-slate-400">
            {formatDuration(currentTime)} / {formatDuration(duration)}
          </span>
        </div>
      )}

      {/* Zoom + Filename */}
      <div className="grid gap-4 sm:grid-cols-2">
        {fitMode === 'crop' ? (
          <Field
            label="Crop Zoom"
            rightSlot={
              <Badge tone="neutral" className="font-mono">
                {zoom.toFixed(2)}×
              </Badge>
            }
          >
            <Slider
              min={1}
              max={3}
              step={0.05}
              value={zoom}
              marks={['1.0×', '2.0×', '3.0×']}
              onChange={setZoom}
            />
          </Field>
        ) : (
          <div className="flex items-center text-xs text-slate-400">
            {fitMode === 'contain'
              ? 'Entire video frame preserved with black (#000) LED padding.'
              : 'Video stretched to fill exact matrix width and height.'}
          </div>
        )}

        <Field
          label="Saved Filename"
          description={`Saved as _uploads/<name>_${targetWidth}x${targetHeight}.mp4`}
        >
          <Input
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            placeholder="my_clip"
            rightSlot={<span className="font-mono text-[11px]">.mp4</span>}
          />
        </Field>
      </div>

      {/* Optional clip trim */}
      {duration > 0.5 && (
        <div className="rounded-xl border border-slate-800/80 bg-surface-950/60 p-3">
          <div className="flex items-center justify-between gap-2">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={trimEnabled}
                onChange={(e) => setTrimEnabled(e.target.checked)}
                className="accent-cyan-400"
              />
              <Scissors className="h-3.5 w-3.5 text-slate-400" />
              Trim clip duration (optional)
            </label>
            {trimEnabled && (
              <span className="font-mono text-[11px] text-cyan-300">
                {Math.max(0, endSec - startSec).toFixed(1)}s clip
              </span>
            )}
          </div>
          {trimEnabled && (
            <div className="mt-3 space-y-2">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Start (sec)">
                  <NumberInput
                    min={0}
                    max={Math.ceil(duration * 10) / 10}
                    step={0.5}
                    unit="s"
                    value={startSec}
                    hasError={trimInvalid}
                    onChange={(v) => setStartSec(Math.max(0, v))}
                  />
                </Field>
                <Field label="End (sec)">
                  <NumberInput
                    min={0}
                    max={Math.ceil(duration * 10) / 10}
                    step={0.5}
                    unit="s"
                    value={endSec}
                    hasError={trimInvalid}
                    onChange={(v) => setEndSec(Math.min(duration, Math.max(0, v)))}
                  />
                </Field>
              </div>
              {trimInvalid && (
                <p className="text-xs text-rose-400">
                  End time must be greater than start time.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-end gap-2 pt-1">
        {onCancel && (
          <Button variant="ghost" size="sm" onClick={onCancel} disabled={uploading}>
            Back to Library
          </Button>
        )}
        <Button
          variant="primary"
          size="sm"
          loading={uploading}
          disabled={trimInvalid}
          onClick={() => void handleUpload()}
          leftIcon={<Upload className="h-3.5 w-3.5" />}
        >
          {uploading
            ? 'Transcoding with ffmpeg...'
            : `Upload & Resize (${targetWidth}×${targetHeight})`}
        </Button>
      </div>
    </div>
  );
}
