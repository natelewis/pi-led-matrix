import { useEffect, useMemo, useState } from 'react';
import {
  Check,
  Copy,
  Film,
  Image as ImageIcon,
  Terminal,
  Trash2,
  Upload,
} from 'lucide-react';
import { api } from '@/api/client';
import {
  Badge,
  Button,
  ConfirmDialog,
  Field,
  Input,
  Modal,
  useToast,
} from '@/components/ui';
import { EffectLivePreview } from '@/components/config/EffectLivePreview';
import { ImageUploadCropper } from '@/components/config/ImageUploadCropper';
import {
  buildInitialFieldValues,
  SchemaFieldsEditor,
  serializeFieldValues,
} from '@/components/config/SchemaFieldsEditor';
import { VideoUploadCropper } from '@/components/config/VideoUploadCropper';
import { buildEffectRunCommand, copyToClipboard } from '@/utils/cliCommand';
import type {
  EffectConfigPreset,
  EffectFieldValue,
  EffectMeta,
  FontMeta,
  PlaylistItem,
  UploadedImageMeta,
  UploadedVideoMeta,
} from '@/types/matrix';

interface EffectConfigModalProps {
  open: boolean;
  item: PlaylistItem | null;
  effectMeta?: EffectMeta;
  fonts: string[];
  fontCatalog?: FontMeta[];
  pixelWidth: number;
  pixelHeight: number;
  ledDots: boolean;
  onEffectsChanged?: () => void;
  onFontsChanged?: (nextFonts: FontMeta[]) => void;
  onClose: () => void;
  onSave: (config?: Record<string, unknown>) => void;
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

/**
 * Seamlessly migrates legacy `{ messages: [...] }` marquee configs into the
 * declarative `content_mode: 'layers'` form shape when opened in the editor.
 */
function normalizeExistingConfig(
  effectId: string,
  raw: Record<string, unknown>,
  defaultFont: string
): Record<string, unknown> {
  if (
    effectId === 'marquee' &&
    Array.isArray(raw.messages) &&
    raw.messages.length > 0 &&
    !('content_mode' in raw) &&
    !('text' in raw) &&
    !('lines' in raw)
  ) {
    const rest = { ...raw };
    delete rest.messages;
    const lines = (raw.messages as Record<string, unknown>[]).map((m) => ({
      text: String(m.message ?? ''),
      font: String(m.font ?? defaultFont),
      size: m.font_size !== undefined ? Number(m.font_size) : 'auto',
      color: rgbToHex(Number(m.r ?? 255), Number(m.g ?? 255), Number(m.b ?? 255)),
      color_mode: 'solid',
      color2: '#ff4081',
      align: 'center',
      motion: 'scroll_left',
    }));
    return {
      ...rest,
      content_mode: 'layers',
      mode: 'scroll_left',
      lines,
    };
  }
  return raw;
}

export function EffectConfigModal({
  open,
  item,
  effectMeta,
  fonts,
  fontCatalog = [],
  pixelWidth,
  pixelHeight,
  ledDots,
  onEffectsChanged,
  onFontsChanged,
  onClose,
  onSave,
}: EffectConfigModalProps) {
  const { notify } = useToast();
  const schema = effectMeta?.configSchema ?? 'none';
  const configFields = useMemo(
    () => effectMeta?.configFields ?? [],
    [effectMeta]
  );
  const configPresets = useMemo(
    () => effectMeta?.configPresets ?? [],
    [effectMeta]
  );
  const hasPreview = Boolean(effectMeta?.hasPreview);
  const defaultFont = fonts[0] ?? 'dosis.ttf';

  const [localFontCatalog, setLocalFontCatalog] = useState<FontMeta[]>(fontCatalog);
  const [fileName, setFileName] = useState('');
  const [fieldValues, setFieldValues] = useState<Record<string, EffectFieldValue>>({});
  const [extraConfig, setExtraConfig] = useState<Record<string, unknown>>({});
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
  const [confirmDelete, setConfirmDelete] = useState<{
    kind: 'image' | 'video';
    file: string;
    name: string;
  } | null>(null);

  useEffect(() => {
    setLocalFontCatalog(fontCatalog);
  }, [fontCatalog]);

  // If modal opens for an effect with font fields and catalog is empty, fetch it
  useEffect(() => {
    if (!open || localFontCatalog.length > 0) return;
    const usesFonts = configFields.some(
      (f) =>
        f.type === 'font' ||
        (f.type === 'list' && f.itemFields?.some((sf) => sf.type === 'font'))
    );
    if (!usesFonts) return;
    let cancelled = false;
    api.fonts
      .list()
      .then((res) => {
        if (!cancelled) {
          setLocalFontCatalog(res.fonts);
          onFontsChanged?.(res.fonts);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [open, configFields, localFontCatalog.length, onFontsChanged]);

  const liveConfigObject = useMemo<Record<string, unknown>>(() => {
    if (!item) return {};
    if (useRawMode || schema === 'none') {
      try {
        const parsed = JSON.parse(rawJson.trim() || '{}');
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          return parsed as Record<string, unknown>;
        }
      } catch {
        return item.config ?? {};
      }
      return {};
    }
    if (schema === 'image') {
      return fileName.trim() ? { ...extraConfig, file: fileName.trim() } : {};
    }
    if (schema === 'video') {
      const merged = serializeFieldValues(configFields, fieldValues, extraConfig);
      if (fileName.trim()) {
        merged.file = fileName.trim();
      } else {
        delete merged.file;
      }
      return merged;
    }
    if (schema === 'fields') {
      return serializeFieldValues(configFields, fieldValues, extraConfig);
    }
    return {};
  }, [item, useRawMode, schema, rawJson, fileName, configFields, fieldValues, extraConfig]);

  const previewCommand = useMemo(() => {
    if (!item) return '';
    const cfg = Object.keys(liveConfigObject).length > 0 ? liveConfigObject : undefined;
    return buildEffectRunCommand({ effect: item.effect, config: cfg });
  }, [item, liveConfigObject]);

  useEffect(() => {
    if (!open || !item) return;
    setJsonError(null);
    const existing = normalizeExistingConfig(
      item.effect,
      item.config ?? {},
      defaultFont
    );
    setExtraConfig(existing);

    if (configFields.length > 0) {
      setFieldValues(buildInitialFieldValues(configFields, existing));
    } else {
      setFieldValues({});
    }

    if (schema === 'image' || schema === 'video') {
      setFileName(typeof existing.file === 'string' ? existing.file : '');
      setUseRawMode(false);
    } else if (schema === 'fields' && configFields.length > 0) {
      setUseRawMode(false);
    } else {
      setUseRawMode(true);
    }

    setRawJson(JSON.stringify(item.config ?? {}, null, 2));
  }, [open, item, schema, configFields, defaultFont]);

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

  const handleApplyPreset = (preset: EffectConfigPreset) => {
    const nextValues = buildInitialFieldValues(configFields, preset.config);
    setFieldValues(nextValues);
    setExtraConfig({});
    setJsonError(null);
    notify('info', `Applied "${preset.label}" preset`);
  };

  const handleApplyDiagnosticPatch = (patch: Record<string, unknown>) => {
    const merged = { ...liveConfigObject, ...patch };
    setFieldValues(buildInitialFieldValues(configFields, merged));
    if (useRawMode) {
      setRawJson(JSON.stringify(merged, null, 2));
    }
    setJsonError(null);
  };

  const handleFontsUpdated = (nextFonts: FontMeta[]) => {
    setLocalFontCatalog(nextFonts);
    onFontsChanged?.(nextFonts);
    onEffectsChanged?.();
  };

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

    if (schema === 'fields') {
      for (const field of configFields) {
        if (field.required) {
          const val = fieldValues[field.key];
          if (val === undefined || val === null || String(val).trim() === '') {
            setJsonError(`${field.label} is required.`);
            return;
          }
        }
      }
      const serialized = serializeFieldValues(configFields, fieldValues, extraConfig);
      onSave(Object.keys(serialized).length > 0 ? serialized : undefined);
      onClose();
      return;
    }

    if (schema === 'image' || schema === 'video') {
      const trimmed = fileName.trim();
      if (!trimmed) {
        setJsonError(`Enter a ${schema} filename.`);
        return;
      }
      if (schema === 'video' && configFields.length > 0) {
        const merged = serializeFieldValues(configFields, fieldValues, extraConfig);
        merged.file = trimmed;
        onSave(merged);
      } else {
        onSave({ ...extraConfig, file: trimmed });
      }
      onClose();
    }
  };

  const showTwoColumnPreview = hasPreview && schema === 'fields' && !useRawMode;

  return (
    <>
      <Modal
        open={open}
        onClose={() => {
          setConfirmDelete(null);
          onClose();
        }}
        title={`Configure ${effectMeta?.label ?? item.effect}`}
        description={
          schema === 'none'
            ? 'Optional JSON config passed to this effect when it runs.'
            : effectMeta?.description
        }
        size={showTwoColumnPreview ? 'xl' : 'lg'}
        footer={
          <>
            {schema !== 'none' && (
              <Button
                variant="ghost"
                size="sm"
                className="mr-auto"
                onClick={() => {
                  if (!useRawMode) {
                    setRawJson(JSON.stringify(liveConfigObject, null, 2));
                    setUseRawMode(true);
                    setJsonError(null);
                  } else {
                    try {
                      const parsed = JSON.parse(rawJson.trim() || '{}');
                      if (
                        typeof parsed !== 'object' ||
                        parsed === null ||
                        Array.isArray(parsed)
                      ) {
                        setJsonError(
                          'Fix invalid JSON object before switching back to Form Editor.'
                        );
                        return;
                      }
                      const parsedObj = normalizeExistingConfig(
                        item.effect,
                        parsed as Record<string, unknown>,
                        defaultFont
                      );
                      setExtraConfig(parsedObj);
                      if (schema === 'image' || schema === 'video') {
                        if (typeof parsedObj.file === 'string') {
                          setFileName(parsedObj.file);
                        }
                        if (schema === 'video' && configFields.length > 0) {
                          setFieldValues(buildInitialFieldValues(configFields, parsedObj));
                        }
                      } else if (schema === 'fields') {
                        setFieldValues(buildInitialFieldValues(configFields, parsedObj));
                      }
                      setUseRawMode(false);
                      setJsonError(null);
                    } catch {
                      setJsonError(
                        'Fix invalid JSON syntax before switching back to Form Editor.'
                      );
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
          {!useRawMode && schema === 'image' && (
            <div className="space-y-4">
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
                                <button
                                  type="button"
                                  disabled={deletingFile === img.file}
                                  title={`Delete ${img.name}`}
                                  aria-label={`Delete ${img.name}`}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setConfirmDelete({
                                      kind: 'image',
                                      file: img.file,
                                      name: img.name,
                                    });
                                  }}
                                  className="rounded p-1 text-slate-400 transition-colors hover:bg-rose-500/15 hover:text-rose-300 cursor-pointer"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
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
                                <button
                                  type="button"
                                  disabled={deletingFile === vid.file}
                                  title={`Delete ${vid.name}`}
                                  aria-label={`Delete ${vid.name}`}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setConfirmDelete({
                                      kind: 'video',
                                      file: vid.file,
                                      name: vid.name,
                                    });
                                  }}
                                  className="rounded p-1 text-slate-400 transition-colors hover:bg-rose-500/15 hover:text-rose-300 cursor-pointer"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
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

                  {configFields.length > 0 && (
                    <SchemaFieldsEditor
                      heading="Playback Options"
                      fields={configFields}
                      values={fieldValues}
                      fontCatalog={localFontCatalog}
                      pixelHeight={pixelHeight}
                      onFontsChanged={handleFontsUpdated}
                      onChange={(key, val) => {
                        setFieldValues((prev) => ({ ...prev, [key]: val }));
                        setJsonError(null);
                      }}
                      onResetDefaults={() => {
                        setFieldValues(buildInitialFieldValues(configFields));
                        setJsonError(null);
                      }}
                    />
                  )}
                </div>
              )}
            </div>
          )}

          {!useRawMode && schema === 'fields' && configFields.length > 0 && (
            <div
              className={
                showTwoColumnPreview
                  ? 'grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.12fr)] lg:items-start'
                  : ''
              }
            >
              {showTwoColumnPreview && (
                <div className="lg:sticky lg:top-0">
                  <EffectLivePreview
                    effectId={item.effect}
                    config={liveConfigObject}
                    pixelWidth={pixelWidth}
                    pixelHeight={pixelHeight}
                    defaultLedDots={ledDots}
                    onApplyPatch={handleApplyDiagnosticPatch}
                  />
                </div>
              )}

              <SchemaFieldsEditor
                fields={configFields}
                values={fieldValues}
                presets={configPresets}
                fontCatalog={localFontCatalog}
                pixelHeight={pixelHeight}
                onFontsChanged={handleFontsUpdated}
                onApplyPreset={handleApplyPreset}
                onChange={(key, val) => {
                  setFieldValues((prev) => ({ ...prev, [key]: val }));
                  setJsonError(null);
                }}
                onResetDefaults={() => {
                  setFieldValues(buildInitialFieldValues(configFields));
                  setExtraConfig({});
                  setJsonError(null);
                }}
              />
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

      <ConfirmDialog
        open={Boolean(confirmDelete)}
        onClose={() => setConfirmDelete(null)}
        onConfirm={async () => {
          if (!confirmDelete) return;
          const target = confirmDelete;
          setDeletingFile(target.file);
          try {
            if (target.kind === 'image') {
              const res = await api.effects.image.deleteFile(target.file);
              setImageFiles(res.files);
            } else {
              const res = await api.effects.video.deleteFile(target.file);
              setVideoFiles(res.files);
            }
            if (fileName === target.file) setFileName('');
            onEffectsChanged?.();
            notify('info', `Deleted ${target.kind}`, target.name);
            setConfirmDelete(null);
          } catch (err) {
            notify(
              'error',
              'Delete failed',
              err instanceof Error ? err.message : 'Unable to delete file.'
            );
          } finally {
            setDeletingFile(null);
          }
        }}
        title={`Delete ${confirmDelete?.name ?? 'file'}?`}
        description={`This permanently removes ${confirmDelete?.file ?? 'this file'} from the active device. Any playlist entries referencing it will need another file selected.`}
        confirmLabel={`Delete ${confirmDelete?.kind === 'video' ? 'Video' : 'Image'}`}
        danger
        loading={Boolean(deletingFile)}
      />
    </>
  );
}
