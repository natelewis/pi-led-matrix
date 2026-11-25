import { useEffect, useMemo, useRef, useState } from 'react';
import { Check, Trash2, Type, Upload } from 'lucide-react';
import { api } from '@/api/client';
import { Badge } from './Badge';
import { Button } from './Button';
import { Dropdown } from './Dropdown';
import { useToast } from './Toast';
import { uint8ToBase64 } from '@/utils/smartCrop';
import type { FontMeta } from '@/types/matrix';

const loadedFontFamilies = new Map<string, string>();
const loadingFontPromises = new Map<string, Promise<string | null>>();

function cssFamilyName(fontId: string): string {
  const safe = fontId.replace(/[^a-zA-Z0-9]/g, '_');
  return `LedMatrixFont_${safe}`;
}

async function ensureFontFaceLoaded(font: FontMeta): Promise<string | null> {
  if (font.builtin || font.id === 'pixel_5x7') return null;
  const existing = loadedFontFamilies.get(font.id);
  if (existing) return existing;
  const pending = loadingFontPromises.get(font.id);
  if (pending) return pending;

  const family = cssFamilyName(font.id);
  const promise = (async () => {
    try {
      if (typeof FontFace === 'undefined' || !document.fonts) return null;
      const face = new FontFace(family, `url("${api.fonts.fileUrl(font.file)}")`, {
        weight: String(font.cssWeight ?? 400),
      });
      const loaded = await face.load();
      document.fonts.add(loaded);
      loadedFontFamilies.set(font.id, family);
      return family;
    } catch {
      return null;
    } finally {
      loadingFontPromises.delete(font.id);
    }
  })();

  loadingFontPromises.set(font.id, promise);
  return promise;
}

const CATEGORY_LABELS: Record<string, string> = {
  all: 'All',
  pixel: 'Pixel',
  sans: 'Sans',
  condensed: 'Condensed',
  mono: 'Mono',
  display: 'Display',
  uploaded: 'Uploaded',
};

export interface FontPickerProps {
  value: string;
  fonts: FontMeta[];
  pixelHeight?: number;
  sampleText?: string;
  compact?: boolean;
  disabled?: boolean;
  onChange: (fontId: string) => void;
  onFontsChanged?: (nextFonts: FontMeta[]) => void;
}

export function FontPicker({
  value,
  fonts,
  pixelHeight = 72,
  sampleText,
  compact = false,
  disabled = false,
  onChange,
  onFontsChanged,
}: FontPickerProps) {
  const { notify } = useToast();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState<string>('all');
  const [loadedMap, setLoadedMap] = useState<Record<string, string>>(() =>
    Object.fromEntries(loadedFontFamilies)
  );
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const selectedFont = useMemo(
    () => fonts.find((f) => f.id === value || f.file === value),
    [fonts, value]
  );

  // Load selected font immediately so the closed trigger renders its real face
  useEffect(() => {
    if (!selectedFont || selectedFont.builtin) return;
    let cancelled = false;
    void ensureFontFaceLoaded(selectedFont).then((fam) => {
      if (!cancelled && fam) {
        setLoadedMap((prev) =>
          prev[selectedFont.id] === fam ? prev : { ...prev, [selectedFont.id]: fam }
        );
      }
    });
    return () => {
      cancelled = true;
    };
  }, [selectedFont]);

  // Load all visible catalog fonts when the dropdown opens
  useEffect(() => {
    if (!open || fonts.length === 0) return;
    let cancelled = false;
    for (const font of fonts) {
      if (font.builtin || loadedFontFamilies.has(font.id)) continue;
      void ensureFontFaceLoaded(font).then((fam) => {
        if (!cancelled && fam) {
          setLoadedMap((prev) =>
            prev[font.id] === fam ? prev : { ...prev, [font.id]: fam }
          );
        }
      });
    }
    return () => {
      cancelled = true;
    };
  }, [open, fonts]);

  const categories = useMemo(() => {
    const present = new Set<string>(fonts.map((f) => f.category));
    const ordered = [
      'all',
      'pixel',
      'sans',
      'condensed',
      'mono',
      'display',
      'uploaded',
      'custom',
    ];
    return ordered.filter((c) => c === 'all' || present.has(c));
  }, [fonts]);

  const filteredFonts = useMemo(() => {
    if (category === 'all') return fonts;
    return fonts.filter((f) => f.category === category);
  }, [fonts, category]);

  const specimen = useMemo(() => {
    const raw = (sampleText ?? '')
      .split('\n')
      .find((line) => line.trim() && line.trim() !== '---');
    const cleaned = (raw ?? 'LED Matrix 123').trim();
    return cleaned.length > 26 ? `${cleaned.slice(0, 25)}…` : cleaned;
  }, [sampleText]);

  const handleUploadFile = async (file: File) => {
    setUploading(true);
    try {
      const buf = new Uint8Array(await file.arrayBuffer());
      const dataBase64 = uint8ToBase64(buf);
      const res = await api.fonts.upload(file.name, dataBase64);
      onFontsChanged?.(res.fonts);
      onChange(res.font.id);
      notify('success', 'Font uploaded', `${res.font.name} is ready to use.`);
    } catch (err) {
      notify(
        'error',
        'Font upload failed',
        err instanceof Error ? err.message : 'Unable to upload font.'
      );
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteFont = async (font: FontMeta) => {
    setDeletingId(font.id);
    try {
      const res = await api.fonts.deleteFile(font.file);
      onFontsChanged?.(res.fonts);
      if (value === font.id || value === font.file) {
        onChange(res.fonts[0]?.id ?? 'dosis.ttf');
      }
      notify('info', 'Font removed', font.name);
    } catch (err) {
      notify(
        'error',
        'Delete failed',
        err instanceof Error ? err.message : 'Could not delete font.'
      );
    } finally {
      setDeletingId(null);
    }
  };

  const renderSpecimenStyle = (font?: FontMeta): React.CSSProperties => {
    if (!font || font.builtin || font.id === 'pixel_5x7') {
      return {
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
        letterSpacing: '0.08em',
      };
    }
    const fam = loadedMap[font.id] ?? loadedFontFamilies.get(font.id);
    return {
      fontFamily: fam ? `"${fam}", sans-serif` : 'inherit',
      fontWeight: font.cssWeight ?? 400,
    };
  };

  return (
    <Dropdown
      open={open}
      onOpenChange={setOpen}
      disabled={disabled}
      minPanelWidth={360}
      triggerClassName={compact ? 'min-h-9 px-3 py-2' : 'px-3.5 py-2.5'}
      panelClassName="p-3"
      trigger={
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Type className="h-3.5 w-3.5 shrink-0 text-cyan-400" />
            <span className="truncate text-xs font-medium text-slate-100">
              {selectedFont?.name ?? value}
            </span>
            {selectedFont?.crispDefault && (
              <Badge tone="emerald" className="text-[10px]">
                crisp
              </Badge>
            )}
            {selectedFont && pixelHeight < selectedFont.minHeight && (
              <Badge tone="amber" className="text-[10px]">
                best ≥{selectedFont.minHeight}px
              </Badge>
            )}
          </div>
          {!compact && (
            <div
              className="mt-1 truncate text-base leading-snug text-cyan-100"
              style={renderSpecimenStyle(selectedFont)}
            >
              {specimen}
            </div>
          )}
        </div>
      }
    >
      <div className="flex min-h-0 flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-1">
            {categories.map((cat) => {
              const active = category === cat;
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setCategory(cat)}
                  className={`rounded-md px-2 py-1 text-[11px] font-medium transition-colors cursor-pointer ${
                    active
                      ? 'bg-cyan-500/20 text-cyan-200 ring-1 ring-cyan-500/40'
                      : 'bg-surface-900 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {CATEGORY_LABELS[cat] ?? cat}
                </button>
              );
            })}
          </div>

          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".ttf,.otf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleUploadFile(file);
              }}
            />
            <Button
              variant="outline"
              size="sm"
              loading={uploading}
              onClick={() => fileInputRef.current?.click()}
              leftIcon={<Upload className="h-3 w-3" />}
            >
              Upload TTF/OTF
            </Button>
          </div>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
          {filteredFonts.map((font) => {
            const isSelected = value === font.id || value === font.file;
            const fitsScreen = pixelHeight >= font.minHeight;
            return (
              <div
                key={font.id}
                onClick={() => {
                  onChange(font.id);
                  setOpen(false);
                }}
                className={`group relative flex cursor-pointer flex-col justify-between rounded-lg border p-2.5 transition-all ${
                  isSelected
                    ? 'border-cyan-400 bg-cyan-500/12 ring-1 ring-cyan-400/35'
                    : 'border-slate-800/90 bg-surface-900/70 hover:border-slate-600'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate text-xs font-semibold text-slate-100">
                        {font.name}
                      </span>
                      {isSelected && (
                        <Check className="h-3.5 w-3.5 shrink-0 text-cyan-300" />
                      )}
                    </div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-1">
                      <Badge tone="neutral" className="text-[9px]">
                        {CATEGORY_LABELS[font.category] ?? font.category}
                      </Badge>
                      {font.crispDefault ? (
                        <Badge tone="emerald" className="text-[9px]">
                          tiny-screen crisp
                        </Badge>
                      ) : !fitsScreen ? (
                        <Badge tone="amber" className="text-[9px]">
                          best ≥{font.minHeight}px
                        </Badge>
                      ) : null}
                    </div>
                  </div>

                  {font.uploaded && (
                    <button
                      type="button"
                      disabled={deletingId === font.id}
                      title={`Delete ${font.name}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDeleteFont(font);
                      }}
                      className="rounded p-1 text-slate-500 transition-colors hover:bg-rose-500/15 hover:text-rose-300 cursor-pointer"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}
                </div>

                <div
                  className="mt-2 truncate rounded bg-black/65 px-2 py-1.5 text-sm leading-tight text-slate-100"
                  style={renderSpecimenStyle(font)}
                >
                  {specimen}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Dropdown>
  );
}
