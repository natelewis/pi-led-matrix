import { useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  Plus,
  RotateCcw,
  Sparkles,
  Trash2,
} from 'lucide-react';
import {
  AlignmentPicker,
  Badge,
  Button,
  ColorPicker,
  Field,
  FontPicker,
  Input,
  normalizeHexColor,
  NumberInput,
  Select,
  Slider,
  Switch,
} from '@/components/ui';
import type {
  EffectConfigField,
  EffectConfigFieldShowWhen,
  EffectConfigPreset,
  EffectFieldValue,
  FontMeta,
} from '@/types/matrix';

export function getFieldDefault(field: EffectConfigField): EffectFieldValue {
  if (field.default !== undefined) {
    if (Array.isArray(field.default)) {
      return structuredClone(field.default);
    }
    return field.default;
  }
  if (field.type === 'select') return field.options?.[0]?.value ?? '';
  if (field.type === 'number') return field.allowAuto ? 'auto' : (field.min ?? 0);
  if (field.type === 'boolean') return false;
  if (field.type === 'color') return '#ffffff';
  if (field.type === 'font') return 'dosis.ttf';
  if (field.type === 'alignment') {
    return field.mode === 'grid' ? 'center-middle' : 'center';
  }
  if (field.type === 'list') return [];
  return '';
}

function buildDefaultListItem(itemFields: EffectConfigField[]): Record<string, unknown> {
  const obj: Record<string, unknown> = {};
  for (const sub of itemFields) {
    obj[sub.key] = getFieldDefault(sub);
  }
  return obj;
}

function coerceFieldValue(
  field: EffectConfigField,
  raw: unknown
): EffectFieldValue {
  const fallback = getFieldDefault(field);
  if (raw === undefined || raw === null) return fallback;

  if (field.type === 'number') {
    if (field.allowAuto && typeof raw === 'string' && raw.trim().toLowerCase() === 'auto') {
      return 'auto';
    }
    const parsed = typeof raw === 'number' ? raw : Number(raw);
    if (!Number.isFinite(parsed)) return fallback;
    let clamped = parsed;
    if (field.min !== undefined) clamped = Math.max(field.min, clamped);
    if (field.max !== undefined) clamped = Math.min(field.max, clamped);
    return field.integer ? Math.round(clamped) : Number(clamped.toFixed(4));
  }

  if (field.type === 'boolean') {
    if (typeof raw === 'boolean') return raw;
    if (typeof raw === 'string') {
      const low = raw.trim().toLowerCase();
      return !['0', 'false', 'no', 'off'].includes(low);
    }
    return Boolean(raw);
  }

  if (field.type === 'color') {
    return normalizeHexColor(String(raw), String(fallback));
  }

  if (field.type === 'list') {
    if (!Array.isArray(raw)) return Array.isArray(fallback) ? fallback : [];
    const subFields = field.itemFields ?? [];
    return raw
      .filter((entry): entry is Record<string, unknown> => Boolean(entry && typeof entry === 'object'))
      .map((entry) => {
        const coerced: Record<string, unknown> = { ...entry };
        for (const sub of subFields) {
          coerced[sub.key] = coerceFieldValue(sub, entry[sub.key]);
        }
        return coerced;
      });
  }

  return String(raw);
}

export function buildInitialFieldValues(
  fields: EffectConfigField[],
  existing?: Record<string, unknown>
): Record<string, EffectFieldValue> {
  const result: Record<string, EffectFieldValue> = {};
  for (const field of fields) {
    result[field.key] = coerceFieldValue(field, existing?.[field.key]);
  }
  return result;
}

export function isFieldModified(
  field: EffectConfigField,
  value: EffectFieldValue | undefined
): boolean {
  const def = getFieldDefault(field);
  if (field.type === 'number') {
    if (value === 'auto' || def === 'auto') return value !== def;
    if (typeof value === 'number' && typeof def === 'number') {
      return Math.abs(value - def) > 1e-6;
    }
  }
  if (field.type === 'color') {
    return (
      normalizeHexColor(String(value ?? def)) !== normalizeHexColor(String(def))
    );
  }
  if (field.type === 'list') {
    return JSON.stringify(value ?? []) !== JSON.stringify(def ?? []);
  }
  return value !== def;
}

export function evaluateShowWhen(
  cond: EffectConfigFieldShowWhen | undefined,
  values: Record<string, unknown>
): boolean {
  if (!cond) return true;
  const target = values[cond.key];
  if (cond.equals !== undefined && target !== cond.equals) return false;
  if (cond.notEquals !== undefined && target === cond.notEquals) return false;
  if (cond.in !== undefined && !cond.in.includes(target)) return false;
  if (cond.gt !== undefined) {
    const num = typeof target === 'number' ? target : Number(target);
    if (!Number.isFinite(num) || num <= cond.gt) return false;
  }
  if (cond.truthy !== undefined && Boolean(target) !== cond.truthy) return false;
  return true;
}

export function serializeFieldValues(
  fields: EffectConfigField[],
  values: Record<string, EffectFieldValue>,
  existing?: Record<string, unknown>
): Record<string, unknown> {
  const fieldKeys = new Set(fields.map((f) => f.key));
  const out: Record<string, unknown> = {};

  // Preserve any custom/extra keys not managed by CONFIG_SCHEMA
  if (existing) {
    for (const [key, val] of Object.entries(existing)) {
      if (!fieldKeys.has(key)) {
        out[key] = val;
      }
    }
  }

  for (const field of fields) {
    const val = values[field.key] ?? getFieldDefault(field);
    if (field.required || isFieldModified(field, val)) {
      out[field.key] = val;
    }
  }

  return out;
}

function formatNumberDisplay(field: EffectConfigField, value: number): string {
  const formatted = field.integer
    ? String(Math.round(value))
    : Number(value.toFixed(2)).toString();
  return field.unit ? `${formatted}${field.unit}` : formatted;
}

interface SchemaFieldsEditorProps {
  fields: EffectConfigField[];
  values: Record<string, EffectFieldValue>;
  presets?: EffectConfigPreset[];
  fontCatalog?: FontMeta[];
  pixelHeight?: number;
  onChange: (key: string, value: EffectFieldValue) => void;
  onApplyPreset?: (preset: EffectConfigPreset) => void;
  onResetDefaults: () => void;
  onFontsChanged?: (nextFonts: FontMeta[]) => void;
  heading?: string;
}

export function SchemaFieldsEditor({
  fields,
  values,
  presets,
  fontCatalog = [],
  pixelHeight = 72,
  onChange,
  onApplyPreset,
  onResetDefaults,
  onFontsChanged,
  heading,
}: SchemaFieldsEditorProps) {
  const sections = useMemo(() => {
    const ordered: string[] = [];
    for (const f of fields) {
      if (f.section && !ordered.includes(f.section)) {
        ordered.push(f.section);
      }
    }
    return ordered;
  }, [fields]);

  const [activeSection, setActiveSection] = useState<string>(() => sections[0] ?? '');

  const effectiveSection =
    sections.length > 0 && sections.includes(activeSection)
      ? activeSection
      : (sections[0] ?? '');

  const visibleFields = useMemo(() => {
    return fields.filter((f) => {
      if (sections.length > 0 && f.section && f.section !== effectiveSection) {
        return false;
      }
      return evaluateShowWhen(f.showWhen, values);
    });
  }, [fields, sections, effectiveSection, values]);

  const modifiedCount = fields.filter((f) => isFieldModified(f, values[f.key])).length;

  const renderControl = (
    field: EffectConfigField,
    val: EffectFieldValue,
    siblingValues: Record<string, unknown>,
    handleValueChange: (next: EffectFieldValue) => void,
    idPrefix: string,
    compact = false
  ) => {
    const modified = isFieldModified(field, val);
    const controlId = `${idPrefix}-${field.key}`;

    if (field.type === 'select') {
      const strVal = String(val ?? getFieldDefault(field));
      const opts = field.options ?? [];
      const hasOption = opts.some((opt) => opt.value === strVal);
      const selectOptions = hasOption
        ? opts
        : [{ value: strVal, label: `${strVal} (custom)` }, ...opts];

      return (
        <Field
          key={field.key}
          label={field.label}
          htmlFor={controlId}
          description={compact ? undefined : field.description}
          rightSlot={
            !compact && modified ? (
              <Badge tone="cyan" className="text-[10px]">
                custom
              </Badge>
            ) : undefined
          }
        >
          <Select
            id={controlId}
            value={strVal}
            options={selectOptions}
            onChange={(e) => handleValueChange(e.target.value)}
          />
        </Field>
      );
    }

    if (field.type === 'number') {
      const isAuto = Boolean(field.allowAuto && val === 'auto');
      const fallbackNum = Math.max(
        field.min ?? 8,
        Math.min(field.max ?? 96, Math.round(pixelHeight * 0.4))
      );
      const numVal =
        typeof val === 'number'
          ? val
          : typeof getFieldDefault(field) === 'number'
            ? (getFieldDefault(field) as number)
            : fallbackNum;
      const hasRange = field.min !== undefined && field.max !== undefined;
      const step = field.step ?? (field.integer ? 1 : 0.1);

      const autoToggle = field.allowAuto ? (
        <button
          type="button"
          onClick={() => handleValueChange(isAuto ? fallbackNum : 'auto')}
          className={`rounded-md px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer ${
            isAuto
              ? 'bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-500/40'
              : 'bg-surface-900 text-slate-400 hover:text-slate-200'
          }`}
        >
          {isAuto ? 'Auto ✓' : 'Auto'}
        </button>
      ) : null;

      if (hasRange) {
        const min = field.min as number;
        const max = field.max as number;
        return (
          <div
            key={field.key}
            className="rounded-xl border border-slate-800/80 bg-surface-950/60 px-3.5 py-2.5"
          >
            <Field
              label={field.label}
              htmlFor={controlId}
              description={compact ? undefined : field.description}
              rightSlot={
                <div className="flex items-center gap-1.5">
                  {autoToggle}
                  <span
                    className={`rounded-md px-2 py-0.5 font-mono text-xs ${
                      modified
                        ? 'bg-cyan-500/15 text-cyan-200 ring-1 ring-cyan-500/30'
                        : 'bg-surface-900 text-slate-300'
                    }`}
                  >
                    {isAuto ? 'auto' : formatNumberDisplay(field, numVal)}
                  </span>
                </div>
              }
            >
              {!isAuto && (
                <Slider
                  id={controlId}
                  value={numVal}
                  min={min}
                  max={max}
                  step={step}
                  marks={[
                    formatNumberDisplay(field, min),
                    formatNumberDisplay(field, max),
                  ]}
                  onChange={(next) =>
                    handleValueChange(
                      field.integer ? Math.round(next) : Number(next.toFixed(4))
                    )
                  }
                />
              )}
            </Field>
          </div>
        );
      }

      return (
        <Field
          key={field.key}
          label={field.label}
          htmlFor={controlId}
          description={compact ? undefined : field.description}
          rightSlot={autoToggle ?? undefined}
        >
          {!isAuto && (
            <NumberInput
              id={controlId}
              value={numVal}
              min={field.min}
              max={field.max}
              step={step}
              integer={field.integer}
              unit={field.unit}
              onChange={(next) => handleValueChange(next)}
            />
          )}
        </Field>
      );
    }

    if (field.type === 'boolean') {
      return (
        <Switch
          key={field.key}
          checked={Boolean(val)}
          label={field.label}
          description={compact ? undefined : field.description}
          onChange={(next) => handleValueChange(next)}
        />
      );
    }

    if (field.type === 'color') {
      const hexVal = normalizeHexColor(String(val || getFieldDefault(field)));
      return (
        <Field
          key={field.key}
          label={field.label}
          htmlFor={controlId}
          description={compact ? undefined : field.description}
          rightSlot={
            !compact && modified ? (
              <Badge tone="cyan" className="text-[10px]">
                custom
              </Badge>
            ) : undefined
          }
        >
          <ColorPicker
            id={controlId}
            value={hexVal}
            onChange={(nextHex) => handleValueChange(nextHex)}
          />
        </Field>
      );
    }

    if (field.type === 'font') {
      const sampleText = field.previewTextKey
        ? String(siblingValues[field.previewTextKey] ?? '')
        : undefined;
      return (
        <Field
          key={field.key}
          label={field.label}
          description={compact ? undefined : field.description}
          rightSlot={
            !compact && modified ? (
              <Badge tone="cyan" className="text-[10px]">
                custom
              </Badge>
            ) : undefined
          }
        >
          <FontPicker
            value={String(val || getFieldDefault(field))}
            fonts={fontCatalog}
            pixelHeight={pixelHeight}
            sampleText={sampleText}
            compact={compact}
            onChange={(nextFont) => handleValueChange(nextFont)}
            onFontsChanged={onFontsChanged}
          />
        </Field>
      );
    }

    if (field.type === 'alignment') {
      return (
        <Field
          key={field.key}
          label={field.label}
          description={compact ? undefined : field.description}
        >
          <AlignmentPicker
            value={String(val || getFieldDefault(field))}
            mode={field.mode ?? 'horizontal'}
            onChange={(nextAlign) => handleValueChange(nextAlign)}
          />
        </Field>
      );
    }

    if (field.type === 'textarea') {
      const strVal = String(val ?? '');
      const lineCount = strVal ? strVal.split('\n').length : 0;
      return (
        <Field
          key={field.key}
          label={field.label}
          htmlFor={controlId}
          description={field.description}
          rightSlot={
            <span className="font-mono text-[11px] text-slate-400">
              {lineCount} {lineCount === 1 ? 'line' : 'lines'}
            </span>
          }
        >
          <div className="space-y-2">
            <textarea
              id={controlId}
              rows={4}
              value={strVal}
              placeholder={field.placeholder}
              onChange={(e) => handleValueChange(e.target.value)}
              className="w-full resize-y rounded-xl border border-slate-700/90 bg-surface-950/90 px-3 py-2 font-mono text-sm text-slate-100 placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
            />
            {field.tokens && field.tokens.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] text-slate-500">Insert live token:</span>
                {field.tokens.map((tok) => (
                  <button
                    key={tok.token}
                    type="button"
                    onClick={() => {
                      const sep = strVal && !strVal.endsWith(' ') && !strVal.endsWith('\n') ? ' ' : '';
                      handleValueChange(`${strVal}${sep}${tok.token}`);
                    }}
                    className="rounded-md border border-slate-800 bg-surface-900 px-2 py-0.5 font-mono text-[11px] text-cyan-300 transition-colors hover:border-cyan-500/40 hover:bg-cyan-500/10 cursor-pointer"
                  >
                    + {tok.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </Field>
      );
    }

    if (field.type === 'list') {
      const items = Array.isArray(val) ? val : [];
      const subFields = field.itemFields ?? [];
      const minItems = field.minItems ?? 0;
      const maxItems = field.maxItems ?? 20;
      const itemLabel = field.itemLabel ?? 'Item';

      const updateItem = (idx: number, key: string, nextSubVal: EffectFieldValue) => {
        const nextList = items.map((entry, i) =>
          i === idx ? { ...entry, [key]: nextSubVal } : entry
        );
        handleValueChange(nextList);
      };

      const moveItem = (idx: number, delta: -1 | 1) => {
        const target = idx + delta;
        if (target < 0 || target >= items.length) return;
        const copy = [...items];
        const [moved] = copy.splice(idx, 1);
        copy.splice(target, 0, moved);
        handleValueChange(copy);
      };

      return (
        <div key={field.key} className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <div className="text-xs font-semibold text-slate-200">{field.label}</div>
              {field.description && (
                <p className="text-[11px] text-slate-400">{field.description}</p>
              )}
            </div>
            <Badge tone="neutral" className="font-mono text-[10px]">
              {items.length}/{maxItems}
            </Badge>
          </div>

          <div className="space-y-2.5">
            {items.map((itemObj, idx) => (
              <div
                key={idx}
                className="space-y-3 rounded-xl border border-slate-800 bg-surface-950/75 p-3.5"
              >
                <div className="flex items-center justify-between gap-2 border-b border-slate-800/70 pb-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-cyan-300/90">
                    {itemLabel} #{idx + 1}
                  </span>
                  <div className="flex items-center gap-1">
                    {field.reorderable && (
                      <>
                        <button
                          type="button"
                          disabled={idx === 0}
                          title="Move up"
                          onClick={() => moveItem(idx, -1)}
                          className="rounded p-1 text-slate-400 hover:bg-surface-800 hover:text-slate-100 disabled:opacity-25 cursor-pointer"
                        >
                          <ArrowUp className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          disabled={idx === items.length - 1}
                          title="Move down"
                          onClick={() => moveItem(idx, 1)}
                          className="rounded p-1 text-slate-400 hover:bg-surface-800 hover:text-slate-100 disabled:opacity-25 cursor-pointer"
                        >
                          <ArrowDown className="h-3.5 w-3.5" />
                        </button>
                      </>
                    )}
                    {items.length > minItems && (
                      <button
                        type="button"
                        title={`Remove ${itemLabel}`}
                        onClick={() =>
                          handleValueChange(items.filter((_, i) => i !== idx))
                        }
                        className="rounded p-1 text-slate-400 hover:bg-rose-500/15 hover:text-rose-300 cursor-pointer"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid items-start gap-3 sm:grid-cols-2">
                  {subFields
                    .filter((sub) => evaluateShowWhen(sub.showWhen, itemObj))
                    .map((sub) => {
                      const subVal = (itemObj[sub.key] ?? getFieldDefault(sub)) as EffectFieldValue;
                      const fullSpan = sub.type !== 'select' && sub.type !== 'boolean';
                      return (
                        <div key={sub.key} className={fullSpan ? 'sm:col-span-2' : ''}>
                          {renderControl(
                            sub,
                            subVal,
                            itemObj,
                            (nextSub) => updateItem(idx, sub.key, nextSub),
                            `${controlId}-${idx}`,
                            true
                          )}
                        </div>
                      );
                    })}
                </div>
              </div>
            ))}
          </div>

          {items.length < maxItems && (
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Plus className="h-3.5 w-3.5" />}
              onClick={() =>
                handleValueChange([...items, buildDefaultListItem(subFields)])
              }
            >
              {field.addLabel ?? `Add ${itemLabel}`}
            </Button>
          )}
        </div>
      );
    }

    return (
      <Field
        key={field.key}
        label={field.label}
        htmlFor={controlId}
        description={compact ? undefined : field.description}
      >
        <Input
          id={controlId}
          value={String(val ?? '')}
          placeholder={field.placeholder}
          onChange={(e) => handleValueChange(e.target.value)}
        />
      </Field>
    );
  };

  return (
    <div className="space-y-4">
      {/* Optional Presets Bar (works for any effect exporting CONFIG_PRESETS) */}
      {presets && presets.length > 0 && onApplyPreset && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            <Sparkles className="h-3 w-3 text-cyan-400" />
            Quick Presets
          </div>
          <div className="flex flex-wrap gap-1.5">
            {presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                title={preset.description}
                onClick={() => onApplyPreset(preset)}
                className="rounded-lg border border-slate-800 bg-surface-950/90 px-2.5 py-1 text-xs font-medium text-slate-200 transition-all hover:border-cyan-400/60 hover:bg-cyan-500/10 hover:text-cyan-100 cursor-pointer"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Header + Reset Defaults */}
      {(heading || modifiedCount > 0) && (
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            {heading ?? 'Effect Options'}
          </span>
          {modifiedCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onResetDefaults}
              leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
            >
              Reset Defaults ({modifiedCount})
            </Button>
          )}
        </div>
      )}

      {/* Optional Section Tabs */}
      {sections.length > 1 && (
        <div className="flex flex-wrap gap-1 rounded-xl border border-slate-800/90 bg-surface-950 p-1">
          {sections.map((sec) => {
            const active = effectiveSection === sec;
            const secModCount = fields.filter(
              (f) => f.section === sec && isFieldModified(f, values[f.key])
            ).length;
            return (
              <button
                key={sec}
                type="button"
                onClick={() => setActiveSection(sec)}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
                  active
                    ? 'bg-cyan-500/20 text-cyan-100 ring-1 ring-cyan-500/40'
                    : 'text-slate-400 hover:bg-surface-900 hover:text-slate-200'
                }`}
              >
                <span>{sec}</span>
                {secModCount > 0 && (
                  <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Fields */}
      <div className="space-y-3.5">
        {visibleFields.map((field) =>
          renderControl(
            field,
            values[field.key] ?? getFieldDefault(field),
            values,
            (next) => onChange(field.key, next),
            'effect-field',
            false
          )
        )}
      </div>
    </div>
  );
}
