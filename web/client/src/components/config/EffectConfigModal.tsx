import { useEffect, useMemo, useState } from 'react';
import {
  Check,
  Copy,
  Film,
  Image as ImageIcon,
  Plus,
  Terminal,
  Trash2,
  Upload,
} from 'lucide-react';
import { api } from '@/api/client';
import {
  Badge,
  Button,
  Field,
  Input,
  Modal,
  NumberInput,
  Select,
  useToast,
} from '@/components/ui';
import { ImageUploadCropper } from '@/components/config/ImageUploadCropper';
import { VideoUploadCropper } from '@/components/config/VideoUploadCropper';
import { buildEffectRunCommand, copyToClipboard } from '@/utils/cliCommand';
import type {
  EffectMeta,
  MarqueeMessage,
  PlaylistItem,
  UploadedImageMeta,
  UploadedVideoMeta,
} from '@/types/matrix';

interface EffectConfigModalProps {
  open: boolean;
  item: PlaylistItem | null;
  effectMeta?: EffectMeta;
  fonts: string[];
  pixelWidth: number;
  pixelHeight: number;
  ledDots: boolean;
  onEffectsChanged?: () => void;
  onClose: () => void;
  onSave: (config?: Record<string, unknown>) => void;
}

function defaultMarqueeMessage(defaultFont: string): MarqueeMessage {
  return {
    left: 0,
    right: 5,
    r: 0,
    g: 220,
    b: 255,
    message: 'Hello LED Matrix',
    font: defaultFont || 'dosis.ttf',
  };
}

function rgbToHex(r: number, g: number, b: number): string {
  const clamp = (n: number) => Math.max(0, Math.min(255, Math.round(n)));
  return (
    '#' +
    [clamp(r), clamp(g), clamp(b)]
      .map((c) => c.toString(16).padStart(2, '0'))
      .join('')
  );
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const clean = hex.replace('#', '');
  return {
    r: parseInt(clean.slice(0, 2), 16) || 0,
    g: parseInt(clean.slice(2, 4), 16) || 0,
    b: parseInt(clean.slice(4, 6), 16) || 0,
  };
}

export function EffectConfigModal({
  open,
  item,
  effectMeta,
  fonts,
  pixelWidth,
  pixelHeight,
  ledDots,
  onEffectsChanged,
  onClose,
  onSave,
}: EffectConfigModalProps) {
  const { notify } = useToast();
  const schema = effectMeta?.configSchema ?? 'none';
  const defaultFont = fonts[0] ?? 'dosis.ttf';

  const [messages, setMessages] = useState<MarqueeMessage[]>([]);
  const [fileName, setFileName] = useState('');
  const [rawJson, setRawJson] = useState('{}');
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [useRawMode, setUseRawMode] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState(false);

  // Image & video library + uploader state
  const [imageTab, setImageTab] = useState<'library' | 'upload'>('library');
  const [imageFiles, setImageFiles] = useState<UploadedImageMeta[]>([]);
  const [loadingImages, setLoadingImages] = useState(false);

  const [videoTab, setVideoTab] = useState<'library' | 'upload'>('library');
  const [videoFiles, setVideoFiles] = useState<UploadedVideoMeta[]>([]);
  const [loadingVideos, setLoadingVideos] = useState(false);

  const [deletingFile, setDeletingFile] = useState<string | null>(null);

  const previewCommand = useMemo(() => {
    if (!item) return '';
    let cfg: Record<string, unknown> | undefined;
    if (useRawMode || schema === 'none') {
      try {
        const parsed = JSON.parse(rawJson.trim() || '{}');
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          cfg = parsed as Record<string, unknown>;
        }
      } catch {
        cfg = item.config;
      }
    } else if (schema === 'marquee') {
      cfg = { messages };
    } else if (schema === 'image' || schema === 'video') {
      cfg = fileName.trim() ? { file: fileName.trim() } : undefined;
    }
    return buildEffectRunCommand({ effect: item.effect, config: cfg });
  }, [item, useRawMode, schema, rawJson, messages, fileName]);

  useEffect(() => {
    if (!open || !item) return;
    setJsonError(null);
    const existing = item.config ?? {};

    if (schema === 'marquee') {
      const existingMsgs = Array.isArray(existing.messages)
        ? (existing.messages as MarqueeMessage[])
        : [];
      setMessages(
        existingMsgs.length > 0
          ? existingMsgs.map((m) => ({
              left: Number(m.left ?? 0),
              right: Number(m.right ?? 5),
              r: Number(m.r ?? 255),
              g: Number(m.g ?? 255),
              b: Number(m.b ?? 255),
              message: String(m.message ?? ''),
              font: String(m.font ?? defaultFont),
            }))
          : [defaultMarqueeMessage(defaultFont)]
      );
      setUseRawMode(false);
    } else if (schema === 'image' || schema === 'video') {
      setFileName(typeof existing.file === 'string' ? existing.file : '');
      setUseRawMode(false);
    } else {
      setUseRawMode(true);
    }

    setRawJson(JSON.stringify(existing, null, 2));
  }, [open, item, schema, defaultFont]);

  useEffect(() => {
    if (!open || schema !== 'image') return;
    let cancelled = false;
    setLoadingImages(true);
    api.effects.image
      .listFiles()
      .then((res) => {
        if (cancelled) return;
        setImageFiles(res.files);
        setImageTab(res.files.length === 0 ? 'upload' : 'library');
      })
      .catch(() => {
        if (!cancelled) setImageFiles([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingImages(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, schema]);

  useEffect(() => {
    if (!open || schema !== 'video') return;
    let cancelled = false;
    setLoadingVideos(true);
    api.effects.video
      .listFiles()
      .then((res) => {
        if (cancelled) return;
        setVideoFiles(res.files);
        setVideoTab(res.files.length === 0 ? 'upload' : 'library');
      })
      .catch(() => {
        if (!cancelled) setVideoFiles([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingVideos(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, schema]);

  if (!item) return null;

  const handleSave = () => {
    if (useRawMode || schema === 'none') {
      const trimmed = rawJson.trim();
      if (!trimmed || trimmed === '{}') {
        onSave(undefined);
        onClose();
        return;
      }
      try {
        const parsed = JSON.parse(trimmed);
        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
          setJsonError('Effect config must be a JSON object.');
          return;
        }
        onSave(Object.keys(parsed).length > 0 ? parsed : undefined);
        onClose();
      } catch {
        setJsonError('Invalid JSON syntax.');
      }
      return;
    }

    if (schema === 'marquee') {
      const filtered = messages.filter((m) => m.message.trim().length > 0);
      if (filtered.length === 0) {
        setJsonError('Add at least one marquee message.');
        return;
      }
      onSave({ ...(item.config ?? {}), messages: filtered });
      onClose();
      return;
    }

    if (schema === 'image' || schema === 'video') {
      const trimmed = fileName.trim();
      if (!trimmed) {
        setJsonError(`Enter a ${schema} filename.`);
        return;
      }
      onSave({ ...(item.config ?? {}), file: trimmed });
      onClose();
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Configure ${effectMeta?.label ?? item.effect}`}
      description={
        schema === 'none'
          ? 'Optional JSON config passed to this effect when it runs.'
          : effectMeta?.description
      }
      size="lg"
      footer={
        <>
          {schema !== 'none' && (
            <Button
              variant="ghost"
              size="sm"
              className="mr-auto"
              onClick={() => {
                if (!useRawMode) {
                  const previewObj =
                    schema === 'marquee'
                      ? { ...(item.config ?? {}), messages }
                      : { ...(item.config ?? {}), file: fileName };
                  setRawJson(JSON.stringify(previewObj, null, 2));
                  setUseRawMode(true);
                  setJsonError(null);
                } else {
                  try {
                    const parsed = JSON.parse(rawJson.trim() || '{}');
                    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
                      setJsonError('Fix invalid JSON object before switching back to Form Editor.');
                      return;
                    }
                    if (schema === 'marquee' && Array.isArray(parsed.messages)) {
                      setMessages(
                        parsed.messages.map((m: Record<string, unknown>) => ({
                          left: Number(m.left ?? 0),
                          right: Number(m.right ?? 5),
                          r: Number(m.r ?? 255),
                          g: Number(m.g ?? 255),
                          b: Number(m.b ?? 255),
                          message: String(m.message ?? ''),
                          font: String(m.font ?? defaultFont),
                        }))
                      );
                    } else if ((schema === 'image' || schema === 'video') && typeof parsed.file === 'string') {
                      setFileName(parsed.file);
                    }
                    setUseRawMode(false);
                    setJsonError(null);
                  } catch {
                    setJsonError('Fix invalid JSON syntax before switching back to Form Editor.');
                  }
                }
              }}
            >
              {useRawMode ? 'Switch to Form Editor' : 'Edit Raw JSON'}
            </Button>
          )}
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSave}>
            Apply Effect Config
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {!useRawMode && schema === 'marquee' && (
          <div className="space-y-3">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className="space-y-3 rounded-xl border border-slate-800 bg-surface-950/70 p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Message #{idx + 1}
                  </span>
                  {messages.length > 1 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setMessages((prev) => prev.filter((_, i) => i !== idx))
                      }
                      leftIcon={<Trash2 className="h-3.5 w-3.5 text-rose-400" />}
                    >
                      Remove
                    </Button>
                  )}
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Text">
                    <Input
                      value={msg.message}
                      placeholder="Scrolling message..."
                      onChange={(e) =>
                        setMessages((prev) =>
                          prev.map((m, i) =>
                            i === idx ? { ...m, message: e.target.value } : m
                          )
                        )
                      }
                    />
                  </Field>

                  <Field label="Font">
                    {fonts.length > 0 ? (
                      <Select
                        value={msg.font}
                        options={
                          msg.font && !fonts.includes(msg.font)
                            ? [
                                { value: msg.font, label: `${msg.font} (missing)` },
                                ...fonts.map((f) => ({ value: f, label: f })),
                              ]
                            : fonts.map((f) => ({ value: f, label: f }))
                        }
                        onChange={(e) =>
                          setMessages((prev) =>
                            prev.map((m, i) =>
                              i === idx ? { ...m, font: e.target.value } : m
                            )
                          )
                        }
                      />
                    ) : (
                      <Input
                        value={msg.font}
                        onChange={(e) =>
                          setMessages((prev) =>
                            prev.map((m, i) =>
                              i === idx ? { ...m, font: e.target.value } : m
                            )
                          )
                        }
                      />
                    )}
                  </Field>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <Field label="X Offset (left)">
                    <NumberInput
                      integer
                      value={msg.left}
                      onChange={(val) =>
                        setMessages((prev) =>
                          prev.map((m, i) => (i === idx ? { ...m, left: val } : m))
                        )
                      }
                    />
                  </Field>
                  <Field label="Y Offset (right)">
                    <NumberInput
                      integer
                      value={msg.right}
                      onChange={(val) =>
                        setMessages((prev) =>
                          prev.map((m, i) => (i === idx ? { ...m, right: val } : m))
                        )
                      }
                    />
                  </Field>
                  <Field label="Color">
                    <div className="flex h-9 items-center gap-2 rounded-lg border border-slate-700/90 bg-surface-950/90 px-2.5">
                      <input
                        type="color"
                        value={rgbToHex(msg.r, msg.g, msg.b)}
                        onChange={(e) => {
                          const rgb = hexToRgb(e.target.value);
                          setMessages((prev) =>
                            prev.map((m, i) => (i === idx ? { ...m, ...rgb } : m))
                          );
                        }}
                        className="h-5 w-7 cursor-pointer rounded border-0 bg-transparent p-0"
                      />
                      <span className="font-mono text-xs text-slate-300">
                        {msg.r},{msg.g},{msg.b}
                      </span>
                    </div>
                  </Field>
                </div>
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              leftIcon={<Plus className="h-3.5 w-3.5" />}
              onClick={() =>
                setMessages((prev) => [...prev, defaultMarqueeMessage(defaultFont)])
              }
            >
              Add Message Layer
            </Button>
          </div>
        )}

        {!useRawMode && schema === 'image' && (
          <div className="space-y-4">
            {/* Switch between saved image library & smart uploader */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="inline-flex rounded-xl border border-slate-800 bg-surface-950 p-1">
                <button
                  type="button"
                  onClick={() => setImageTab('library')}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                    imageTab === 'library'
                      ? 'bg-cyan-500/20 text-cyan-200 ring-1 ring-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ImageIcon className="h-3.5 w-3.5" />
                  Saved Images ({imageFiles.length})
                </button>
                <button
                  type="button"
                  onClick={() => setImageTab('upload')}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                    imageTab === 'upload'
                      ? 'bg-cyan-500/20 text-cyan-200 ring-1 ring-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Upload className="h-3.5 w-3.5" />
                  Upload & Smart Crop
                </button>
              </div>
              <Badge tone="neutral" className="font-mono">
                Target: {pixelWidth}×{pixelHeight}
              </Badge>
            </div>

            {imageTab === 'upload' ? (
              <ImageUploadCropper
                targetWidth={pixelWidth}
                targetHeight={pixelHeight}
                ledDots={ledDots}
                onCancel={imageFiles.length > 0 ? () => setImageTab('library') : undefined}
                onUploaded={(uploaded, allFiles) => {
                  setImageFiles(allFiles);
                  setFileName(uploaded.file);
                  setJsonError(null);
                  setImageTab('library');
                  onEffectsChanged?.();
                }}
              />
            ) : (
              <div className="space-y-3">
                {loadingImages ? (
                  <p className="py-6 text-center text-xs text-slate-400">
                    Loading image library...
                  </p>
                ) : imageFiles.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-800 bg-surface-950/60 p-6 text-center">
                    <p className="text-xs text-slate-400">
                      No images found in <code>src/effects/image/</code> or{' '}
                      <code>_uploads/</code> yet.
                    </p>
                    <Button
                      variant="primary"
                      size="sm"
                      className="mt-3"
                      onClick={() => setImageTab('upload')}
                      leftIcon={<Upload className="h-3.5 w-3.5" />}
                    >
                      Upload an Image
                    </Button>
                  </div>
                ) : (
                  <div className="grid max-h-[260px] grid-cols-2 gap-2.5 overflow-y-auto pr-1 sm:grid-cols-3">
                    {imageFiles.map((img) => {
                      const selected = fileName === img.file;
                      const sizeMatches =
                        img.width === pixelWidth && img.height === pixelHeight;
                      return (
                        <div
                          key={img.file}
                          onClick={() => {
                            setFileName(img.file);
                            setJsonError(null);
                          }}
                          className={`group relative cursor-pointer overflow-hidden rounded-xl border transition-all ${
                            selected
                              ? 'border-cyan-400 bg-cyan-500/10 ring-1 ring-cyan-400/40'
                              : 'border-slate-800 bg-surface-950/80 hover:border-slate-600'
                          }`}
                        >
                          <div className="flex h-24 items-center justify-center bg-black p-1.5">
                            <img
                              src={api.effects.image.previewUrl(img.file)}
                              alt={img.name}
                              className="max-h-full max-w-full object-contain"
                              style={{ imageRendering: 'pixelated' }}
                            />
                          </div>
                          <div className="space-y-1 p-2">
                            <div className="truncate font-mono text-[11px] text-slate-200">
                              {img.name}
                            </div>
                            <div className="flex items-center justify-between gap-1">
                              {img.width && img.height ? (
                                <Badge
                                  tone={sizeMatches ? 'emerald' : 'amber'}
                                  className="font-mono text-[10px]"
                                >
                                  {img.width}×{img.height}
                                </Badge>
                              ) : (
                                <Badge tone="neutral" className="text-[10px]">
                                  image
                                </Badge>
                              )}
                              {img.uploaded && (
                                <button
                                  type="button"
                                  disabled={deletingFile === img.file}
                                  title="Delete uploaded image"
                                  onClick={async (e) => {
                                    e.stopPropagation();
                                    setDeletingFile(img.file);
                                    try {
                                      const res = await api.effects.image.deleteFile(img.file);
                                      setImageFiles(res.files);
                                      if (fileName === img.file) setFileName('');
                                      onEffectsChanged?.();
                                      notify('info', 'Deleted uploaded image', img.name);
                                    } catch (err) {
                                      notify(
                                        'error',
                                        'Delete failed',
                                        err instanceof Error ? err.message : 'Unable to delete.'
                                      );
                                    } finally {
                                      setDeletingFile(null);
                                    }
                                  }}
                                  className="rounded p-1 text-slate-500 hover:bg-rose-500/15 hover:text-rose-300 cursor-pointer"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                <Field
                  label="Selected File Path"
                  description="Relative to src/effects/image/ (uploaded images live in _uploads/)."
                >
                  <Input
                    value={fileName}
                    placeholder="_uploads/my_photo_128x72.png"
                    onChange={(e) => {
                      setFileName(e.target.value);
                      setJsonError(null);
                    }}
                  />
                </Field>
              </div>
            )}
          </div>
        )}

        {!useRawMode && schema === 'video' && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="inline-flex rounded-xl border border-slate-800 bg-surface-950 p-1">
                <button
                  type="button"
                  onClick={() => setVideoTab('library')}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                    videoTab === 'library'
                      ? 'bg-cyan-500/20 text-cyan-200 ring-1 ring-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Film className="h-3.5 w-3.5" />
                  Saved Videos ({videoFiles.length})
                </button>
                <button
                  type="button"
                  onClick={() => setVideoTab('upload')}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                    videoTab === 'upload'
                      ? 'bg-cyan-500/20 text-cyan-200 ring-1 ring-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Upload className="h-3.5 w-3.5" />
                  Upload & Smart Crop
                </button>
              </div>
              <Badge tone="neutral" className="font-mono">
                Target: {pixelWidth}×{pixelHeight}
              </Badge>
            </div>

            {videoTab === 'upload' ? (
              <VideoUploadCropper
                targetWidth={pixelWidth}
                targetHeight={pixelHeight}
                ledDots={ledDots}
                onCancel={videoFiles.length > 0 ? () => setVideoTab('library') : undefined}
                onUploaded={(uploaded, allFiles) => {
                  setVideoFiles(allFiles);
                  setFileName(uploaded.file);
                  setJsonError(null);
                  setVideoTab('library');
                  onEffectsChanged?.();
                }}
              />
            ) : (
              <div className="space-y-3">
                {loadingVideos ? (
                  <p className="py-6 text-center text-xs text-slate-400">
                    Loading video library...
                  </p>
                ) : videoFiles.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-800 bg-surface-950/60 p-6 text-center">
                    <p className="text-xs text-slate-400">
                      No videos found in <code>src/effects/video/</code> or{' '}
                      <code>_uploads/</code> yet.
                    </p>
                    <Button
                      variant="primary"
                      size="sm"
                      className="mt-3"
                      onClick={() => setVideoTab('upload')}
                      leftIcon={<Upload className="h-3.5 w-3.5" />}
                    >
                      Upload a Video
                    </Button>
                  </div>
                ) : (
                  <div className="grid max-h-[260px] grid-cols-2 gap-2.5 overflow-y-auto pr-1 sm:grid-cols-3">
                    {videoFiles.map((vid) => {
                      const selected = fileName === vid.file;
                      const sizeMatches =
                        vid.width === pixelWidth && vid.height === pixelHeight;
                      return (
                        <div
                          key={vid.file}
                          onClick={() => {
                            setFileName(vid.file);
                            setJsonError(null);
                          }}
                          className={`group relative cursor-pointer overflow-hidden rounded-xl border transition-all ${
                            selected
                              ? 'border-cyan-400 bg-cyan-500/10 ring-1 ring-cyan-400/40'
                              : 'border-slate-800 bg-surface-950/80 hover:border-slate-600'
                          }`}
                        >
                          <div className="flex h-24 items-center justify-center bg-black p-1.5">
                            <video
                              src={api.effects.video.previewUrl(vid.file)}
                              muted
                              loop
                              playsInline
                              preload="metadata"
                              onMouseEnter={(e) => {
                                void e.currentTarget.play().catch(() => {});
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.pause();
                              }}
                              className="max-h-full max-w-full object-contain"
                              style={{ imageRendering: 'pixelated' }}
                            />
                          </div>
                          <div className="space-y-1 p-2">
                            <div className="truncate font-mono text-[11px] text-slate-200">
                              {vid.name}
                            </div>
                            <div className="flex items-center justify-between gap-1">
                              <div className="flex items-center gap-1">
                                {vid.width && vid.height ? (
                                  <Badge
                                    tone={sizeMatches ? 'emerald' : 'amber'}
                                    className="font-mono text-[10px]"
                                  >
                                    {vid.width}×{vid.height}
                                  </Badge>
                                ) : (
                                  <Badge tone="neutral" className="text-[10px]">
                                    video
                                  </Badge>
                                )}
                                {vid.duration !== null && (
                                  <span className="font-mono text-[10px] text-slate-400">
                                    {vid.duration.toFixed(1)}s
                                  </span>
                                )}
                              </div>
                              {vid.uploaded && (
                                <button
                                  type="button"
                                  disabled={deletingFile === vid.file}
                                  title="Delete uploaded video"
                                  onClick={async (e) => {
                                    e.stopPropagation();
                                    setDeletingFile(vid.file);
                                    try {
                                      const res = await api.effects.video.deleteFile(vid.file);
                                      setVideoFiles(res.files);
                                      if (fileName === vid.file) setFileName('');
                                      onEffectsChanged?.();
                                      notify('info', 'Deleted uploaded video', vid.name);
                                    } catch (err) {
                                      notify(
                                        'error',
                                        'Delete failed',
                                        err instanceof Error ? err.message : 'Unable to delete.'
                                      );
                                    } finally {
                                      setDeletingFile(null);
                                    }
                                  }}
                                  className="rounded p-1 text-slate-500 hover:bg-rose-500/15 hover:text-rose-300 cursor-pointer"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                <Field
                  label="Selected File Path"
                  description="Relative to src/effects/video/ (uploaded videos live in _uploads/)."
                >
                  <Input
                    value={fileName}
                    placeholder="_uploads/my_clip_128x72.mp4"
                    onChange={(e) => {
                      setFileName(e.target.value);
                      setJsonError(null);
                    }}
                  />
                </Field>
              </div>
            )}
          </div>
        )}

        {(useRawMode || schema === 'none') && (
          <Field
            label="Effect Config JSON"
            description="Leave empty or {} for effects that need no extra parameters."
          >
            <textarea
              rows={8}
              value={rawJson}
              onChange={(e) => {
                setRawJson(e.target.value);
                setJsonError(null);
              }}
              spellCheck={false}
              className="w-full rounded-xl border border-slate-700/90 bg-surface-950 p-3 font-mono text-xs text-slate-100 focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
            />
          </Field>
        )}

        {jsonError && <p className="text-xs text-rose-400">{jsonError}</p>}

        {/* Terminal Command Preview */}
        <div className="space-y-1.5 rounded-xl border border-slate-800 bg-surface-950/90 p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-400">
              <Terminal className="h-3.5 w-3.5 text-cyan-400" />
              Terminal Command
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                try {
                  await copyToClipboard(previewCommand);
                  setCopiedCmd(true);
                  notify('success', 'Copied terminal command');
                  window.setTimeout(() => setCopiedCmd(false), 1800);
                } catch {
                  notify('error', 'Copy failed');
                }
              }}
              leftIcon={
                copiedCmd ? (
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )
              }
            >
              {copiedCmd ? 'Copied' : 'Copy'}
            </Button>
          </div>
          <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-lg bg-black/50 px-2.5 py-2 font-mono text-[11px] text-cyan-200">
            {previewCommand}
          </pre>
        </div>
      </div>
    </Modal>
  );
}
