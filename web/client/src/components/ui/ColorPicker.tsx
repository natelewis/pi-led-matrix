import { useEffect, useState } from 'react';

const DEFAULT_PRESETS = [
  { hex: '#ff2a2a', label: 'Red' },
  { hex: '#ff8c00', label: 'Orange' },
  { hex: '#ffd700', label: 'Gold' },
  { hex: '#00e676', label: 'Emerald' },
  { hex: '#00e5ff', label: 'Cyan' },
  { hex: '#2979ff', label: 'Blue' },
  { hex: '#b388ff', label: 'Violet' },
  { hex: '#ff4081', label: 'Magenta' },
  { hex: '#ffffff', label: 'White' },
];

export function normalizeHexColor(raw: string, fallback = '#ffffff'): string {
  const text = raw.trim().toLowerCase();
  const body = text.startsWith('#') ? text.slice(1) : text;
  if (/^[0-9a-f]{3}$/.test(body)) {
    return `#${body[0]}${body[0]}${body[1]}${body[1]}${body[2]}${body[2]}`;
  }
  if (/^[0-9a-f]{6}$/.test(body)) {
    return `#${body}`;
  }
  return fallback;
}

function hexToRgbLabel(hex: string): string {
  const norm = normalizeHexColor(hex);
  const r = parseInt(norm.slice(1, 3), 16);
  const g = parseInt(norm.slice(3, 5), 16);
  const b = parseInt(norm.slice(5, 7), 16);
  return `${r}, ${g}, ${b}`;
}

export interface ColorPickerProps {
  id?: string;
  value: string;
  onChange: (hex: string) => void;
  presets?: { hex: string; label: string }[];
  disabled?: boolean;
}

export function ColorPicker({
  id,
  value,
  onChange,
  presets = DEFAULT_PRESETS,
  disabled = false,
}: ColorPickerProps) {
  const normalized = normalizeHexColor(value);
  const [draft, setDraft] = useState(normalized);

  useEffect(() => {
    setDraft(normalized);
  }, [normalized]);

  const handleHexInput = (nextRaw: string) => {
    setDraft(nextRaw);
    const trimmed = nextRaw.trim();
    if (/^#?[0-9a-fA-F]{6}$/.test(trimmed)) {
      onChange(normalizeHexColor(trimmed, normalized));
    }
  };

  const handleBlur = () => {
    const resolved = normalizeHexColor(draft, normalized);
    setDraft(resolved);
    if (resolved !== normalized) {
      onChange(resolved);
    }
  };

  return (
    <div className="space-y-2 rounded-xl border border-slate-800/80 bg-surface-950/60 p-3">
      <div className="flex items-center gap-2.5">
        <label
          className="relative flex h-9 w-11 shrink-0 cursor-pointer items-center justify-center overflow-hidden rounded-lg border border-slate-700/90 shadow-inner"
          style={{ backgroundColor: normalized }}
          title="Open color picker"
        >
          <input
            id={id}
            type="color"
            value={normalized}
            disabled={disabled}
            onChange={(e) => {
              const next = normalizeHexColor(e.target.value, normalized);
              setDraft(next);
              onChange(next);
            }}
            className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
          />
        </label>

        <input
          type="text"
          value={draft}
          disabled={disabled}
          spellCheck={false}
          aria-label="Hex color value"
          onChange={(e) => handleHexInput(e.target.value)}
          onBlur={handleBlur}
          placeholder="#ffffff"
          className="h-9 w-28 rounded-lg border border-slate-700/90 bg-surface-950/90 px-2.5 font-mono text-xs text-slate-100 focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/20 disabled:opacity-50"
        />

        <span className="ml-auto font-mono text-[11px] text-slate-400">
          RGB ({hexToRgbLabel(normalized)})
        </span>
      </div>

      {presets.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          {presets.map((preset) => {
            const active = normalized === preset.hex.toLowerCase();
            return (
              <button
                key={preset.hex}
                type="button"
                disabled={disabled}
                title={`${preset.label} (${preset.hex})`}
                aria-label={`Select ${preset.label}`}
                onClick={() => {
                  const next = normalizeHexColor(preset.hex);
                  setDraft(next);
                  onChange(next);
                }}
                className={`h-5 w-5 rounded-full border transition-transform cursor-pointer hover:scale-110 disabled:cursor-not-allowed disabled:opacity-50 ${
                  active
                    ? 'scale-110 border-white ring-2 ring-cyan-400/70'
                    : 'border-slate-700/90'
                }`}
                style={{ backgroundColor: preset.hex }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
