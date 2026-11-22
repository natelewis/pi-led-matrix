import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Crop,
  ImagePlus,
  Maximize2,
  Move,
  Sparkles,
  StretchHorizontal,
  Upload,
  X,
} from 'lucide-react';
import { api } from '@/api/client';
import { Badge, Button, Field, Input, Slider, useToast } from '@/components/ui';
import type { UploadedImageMeta } from '@/types/matrix';
import {
  analyzeSmartCrop,
  computeCropRect,
  paintLedPreviewCanvas,
  renderMatrixImage,
  uint8ToBase64,
  type ImageFitMode,
  type SmartCropAnalysis,
} from '@/utils/smartCrop';

export interface ImageUploadCropperProps {
  targetWidth: number;
  targetHeight: number;
  ledDots?: boolean;
  onUploaded: (image: UploadedImageMeta, allFiles: UploadedImageMeta[]) => void;
  onCancel?: () => void;
}

const FIT_MODES: { id: ImageFitMode; label: string; icon: typeof Crop }[] = [
  { id: 'crop', label: 'Smart Crop', icon: Crop },
  { id: 'contain', label: 'Fit (Pad)', icon: Maximize2 },
  { id: 'stretch', label: 'Stretch', icon: StretchHorizontal },
];

export function ImageUploadCropper({
  targetWidth,
  targetHeight,
  ledDots = true,
  onUploaded,
  onCancel,
}: ImageUploadCropperProps) {
  const { notify } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const previewCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);

  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [imageEl, setImageEl] = useState<HTMLImageElement | null>(null);
  const [filename, setFilename] = useState('');
  const [analysis, setAnalysis] = useState<SmartCropAnalysis | null>(null);

  const [fitMode, setFitMode] = useState<ImageFitMode>('crop');
  const [focalX, setFocalX] = useState(0.5);
  const [focalY, setFocalY] = useState(0.5);
  const [zoom, setZoom] = useState(1);
  const [uploading, setUploading] = useState(false);

  const mountedRef = useRef(true);
  const loadSeqRef = useRef(0);
  const dragStateRef = useRef<{
    startX: number;
    startY: number;
    startFocalX: number;
    startFocalY: number;
  } | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    return () => {
      if (sourceUrl) URL.revokeObjectURL(sourceUrl);
    };
  }, [sourceUrl]);

  const loadFile = useCallback(
    (file: File) => {
      if (!file.type.startsWith('image/')) {
        notify('error', 'Unsupported file', 'Please choose an image file (PNG, JPG, WebP, GIF).');
        return;
      }

      const seq = ++loadSeqRef.current;
      const nextUrl = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        if (!mountedRef.current || seq !== loadSeqRef.current) {
          URL.revokeObjectURL(nextUrl);
          return;
        }
        setSourceUrl(nextUrl);
        setImageEl(img);
        setFilename(file.name.replace(/\.[^.]+$/, ''));
        setFitMode('crop');
      };
      img.onerror = () => {
        URL.revokeObjectURL(nextUrl);
        if (mountedRef.current && seq === loadSeqRef.current) {
          notify('error', 'Could not read image', 'The selected image could not be decoded.');
        }
      };
      img.src = nextUrl;
    },
    [notify]
  );

  // Run smart crop analysis once per loaded image or whenever target dimensions change
  useEffect(() => {
    if (!imageEl) return;
    const result = analyzeSmartCrop(imageEl, targetWidth, targetHeight);
    setAnalysis(result);
    setFocalX(result.focalX);
    setFocalY(result.focalY);
    setZoom(1);
  }, [imageEl, targetWidth, targetHeight]);

  // Compute crop overlay percentages relative to the source image box
  const cropPercent = useMemo(() => {
    if (!imageEl) return null;
    const rect = computeCropRect(
      imageEl.naturalWidth,
      imageEl.naturalHeight,
      targetWidth,
      targetHeight,
      focalX,
      focalY,
      zoom
    );
    return {
      left: (rect.x / imageEl.naturalWidth) * 100,
      top: (rect.y / imageEl.naturalHeight) * 100,
      width: (rect.width / imageEl.naturalWidth) * 100,
      height: (rect.height / imageEl.naturalHeight) * 100,
    };
  }, [imageEl, targetWidth, targetHeight, focalX, focalY, zoom]);

  // Render live pixel-accurate LED matrix preview canvas
  useEffect(() => {
    const canvas = previewCanvasRef.current;
    if (!canvas || !imageEl) return;

    const { rgbaBytes } = renderMatrixImage(imageEl, targetWidth, targetHeight, {
      fitMode,
      focalX,
      focalY,
      zoom,
    });
    paintLedPreviewCanvas(canvas, rgbaBytes, targetWidth, targetHeight, ledDots);
  }, [imageEl, targetWidth, targetHeight, fitMode, focalX, focalY, zoom, ledDots]);

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

  const handleUpload = async () => {
    if (!imageEl) return;
    setUploading(true);
    try {
      const { rgbaBytes } = renderMatrixImage(imageEl, targetWidth, targetHeight, {
        fitMode,
        focalX,
        focalY,
        zoom,
      });
      const rgbaBase64 = uint8ToBase64(rgbaBytes);
      const res = await api.effects.image.upload({
        filename: filename.trim() || 'image',
        width: targetWidth,
        height: targetHeight,
        rgbaBase64,
      });
      notify(
        'success',
        'Image uploaded & resized',
        `Saved ${res.image.file} (${targetWidth}×${targetHeight} RGBA PNG).`
      );
      onUploaded(res.image, res.files);
    } catch (err) {
      notify(
        'error',
        'Upload failed',
        err instanceof Error ? err.message : 'Unable to upload image.'
      );
    } finally {
      setUploading(false);
    }
  };

  const clearSelection = () => {
    loadSeqRef.current += 1;
    setSourceUrl(null);
    setImageEl(null);
    setAnalysis(null);
    setFilename('');
  };

  if (!imageEl || !sourceUrl) {
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
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) loadFile(file);
            e.target.value = '';
          }}
        />
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-500/12 text-cyan-300 ring-1 ring-cyan-500/30">
          <ImagePlus className="h-6 w-6" />
        </div>
        <div className="text-sm font-medium text-white">
          Drop an image here or click to browse
        </div>
        <p className="mt-1 max-w-md text-xs text-slate-400">
          Auto-sizes to <span className="font-mono text-cyan-300">{targetWidth}×{targetHeight}</span>{' '}
          and saves to <code className="text-slate-300">src/effects/image/_uploads/</code>.
          Non-matching aspect ratios are automatically smart-cropped to the focal subject.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Smart analysis banner */}
      {analysis && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-cyan-500/25 bg-cyan-500/8 px-3.5 py-2.5 text-xs">
          <div className="flex items-center gap-2 text-cyan-100">
            <Sparkles className="h-4 w-4 shrink-0 text-cyan-300" />
            <span>{analysis.summary}</span>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone="neutral" className="font-mono">
              {imageEl.naturalWidth}×{imageEl.naturalHeight} → {targetWidth}×{targetHeight}
            </Badge>
            <button
              type="button"
              onClick={clearSelection}
              title="Pick a different image"
              className="rounded-md p-1 text-slate-400 hover:bg-surface-800 hover:text-white cursor-pointer"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Fit Mode Selector */}
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
              onClick={() => {
                setFocalX(analysis.focalX);
                setFocalY(analysis.focalY);
                setZoom(1);
              }}
              className="rounded-lg border border-slate-800 bg-surface-950 px-2 py-1 text-[11px] font-medium text-cyan-300 hover:border-cyan-500/40 cursor-pointer"
            >
              Smart
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

      {/* Dual Preview: Interactive Crop Stage + LED Matrix Output */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Source image with draggable crop box */}
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
              <img
                src={sourceUrl}
                alt="Upload source"
                draggable={false}
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
                  {/* Rule of thirds guides */}
                  <div className="absolute inset-y-0 left-1/3 border-l border-white/20" />
                  <div className="absolute inset-y-0 left-2/3 border-l border-white/20" />
                  <div className="absolute inset-x-0 top-1/3 border-t border-white/20" />
                  <div className="absolute inset-x-0 top-2/3 border-t border-white/20" />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Exact LED matrix output preview */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span className="font-medium text-slate-300">LED Matrix Preview</span>
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

      {/* Zoom slider (crop mode) + filename */}
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
              ? 'Entire image preserved with black (#000) LED padding.'
              : 'Image stretched to fill exact matrix width and height.'}
          </div>
        )}

        <Field
          label="Saved Filename"
          description={`Saved as _uploads/<name>_${targetWidth}x${targetHeight}.png`}
        >
          <Input
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            placeholder="my_image"
            rightSlot={<span className="font-mono text-[11px]">.png</span>}
          />
        </Field>
      </div>

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
          onClick={() => void handleUpload()}
          leftIcon={<Upload className="h-3.5 w-3.5" />}
        >
          Upload & Resize ({targetWidth}×{targetHeight})
        </Button>
      </div>
    </div>
  );
}
