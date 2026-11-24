import { RotateCcw } from 'lucide-react';
import {
  Badge,
  Button,
  ColorPicker,
  Field,
  Input,
  normalizeHexColor,
  NumberInput,
  Select,
  Slider,
  Switch,
} from '@/components/ui';
import type { EffectConfigField } from '@/types/matrix';

export function getFieldDefault(field: EffectConfigField): string | number | boolean {
  if (field.default !== undefined) return field.default;
  if (field.type === 'select') return field.options?.[0]?.value ?? '';
  if (field.type === 'number') return field.min ?? 0;
  if (field.type === 'boolean') return false;
  if (field.type === 'color') return '#ffffff';
  return '';
}

function coerceFieldValue(
  field: EffectConfigField,
  raw: unknown
): string | number | boolean {
  const fallback = getFieldDefault(field);
  if (raw === undefined || raw === null) return fallback;

  if (field.type === 'number') {
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

  return String(raw);
}

export function buildInitialFieldValues(
  fields: EffectConfigField[],
  existing?: Record<string, unknown>
): Record<string, string | number | boolean> {
  const result: Record<string, string | number | boolean> = {};
  for (const field of fields) {
    result[field.key] = coerceFieldValue(field, existing?.[field.key]);
  }
  return result;
}

export function isFieldModified(
  field: EffectConfigField,
  value: string | number | boolean | undefined
): boolean {
  const def = getFieldDefault(field);
  if (field.type === 'number' && typeof value === 'number' && typeof def === 'number') {
    return Math.abs(value - def) > 1e-6;
  }
  if (field.type === 'color') {
    return (
      normalizeHexColor(String(value ?? def)) !== normalizeHexColor(String(def))
    );
  }
  return value !== def;
}

export function serializeFieldValues(
  fields: EffectConfigField[],
  values: Record<string, string | number | boolean>,
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
  values: Record<string, string | number | boolean>;
  onChange: (key: string, value: string | number | boolean) => void;
  onResetDefaults: () => void;
  heading?: string;
}

export function SchemaFieldsEditor({
  fields,
  values,
  onChange,
  onResetDefaults,
  heading,
}: SchemaFieldsEditorProps) {
  const modifiedCount = fields.filter((f) => isFieldModified(f, values[f.key])).length;

  return (
    <div className="space-y-4">
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

      <div className="space-y-3.5">
        {fields.map((field) => {
          const val = values[field.key] ?? getFieldDefault(field);
          const modified = isFieldModified(field, val);

          if (field.type === 'select') {
            const strVal = String(val);
            const opts = field.options ?? [];
            const hasOption = opts.some((opt) => opt.value === strVal);
            const selectOptions = hasOption
              ? opts
              : [{ value: strVal, label: `${strVal} (custom)` }, ...opts];

            return (
              <Field
                key={field.key}
                label={field.label}
                htmlFor={`effect-field-${field.key}`}
                description={field.description}
                rightSlot={
                  modified ? (
                    <Badge tone="cyan" className="text-[10px]">
                      custom
                    </Badge>
                  ) : undefined
                }
              >
                <Select
                  id={`effect-field-${field.key}`}
                  value={strVal}
                  options={selectOptions}
                  onChange={(e) => onChange(field.key, e.target.value)}
                />
              </Field>
            );
          }

          if (field.type === 'number') {
            const numVal = typeof val === 'number' ? val : Number(getFieldDefault(field));
            const hasRange = field.min !== undefined && field.max !== undefined;
            const step = field.step ?? (field.integer ? 1 : 0.1);

            if (hasRange) {
              const min = field.min as number;
              const max = field.max as number;
              return (
                <div
                  key={field.key}
                  className="rounded-xl border border-slate-800/80 bg-surface-950/60 px-4 py-3"
                >
                  <Field
                    label={field.label}
                    htmlFor={`effect-field-${field.key}`}
                    description={field.description}
                    rightSlot={
                      <span
                        className={`rounded-md px-2 py-0.5 font-mono text-xs ${
                          modified
                            ? 'bg-cyan-500/15 text-cyan-200 ring-1 ring-cyan-500/30'
                            : 'bg-surface-900 text-slate-300'
                        }`}
                      >
                        {formatNumberDisplay(field, numVal)}
                      </span>
                    }
                  >
                    <Slider
                      id={`effect-field-${field.key}`}
                      value={numVal}
                      min={min}
                      max={max}
                      step={step}
                      marks={[
                        formatNumberDisplay(field, min),
                        formatNumberDisplay(field, max),
                      ]}
                      onChange={(next) =>
                        onChange(
                          field.key,
                          field.integer ? Math.round(next) : Number(next.toFixed(4))
                        )
                      }
                    />
                  </Field>
                </div>
              );
            }

            return (
              <Field
                key={field.key}
                label={field.label}
                htmlFor={`effect-field-${field.key}`}
                description={field.description}
              >
                <NumberInput
                  id={`effect-field-${field.key}`}
                  value={numVal}
                  min={field.min}
                  max={field.max}
                  step={step}
                  integer={field.integer}
                  unit={field.unit}
                  onChange={(next) => onChange(field.key, next)}
                />
              </Field>
            );
          }

          if (field.type === 'boolean') {
            return (
              <Switch
                key={field.key}
                checked={Boolean(val)}
                label={field.label}
                description={field.description}
                onChange={(next) => onChange(field.key, next)}
              />
            );
          }

          if (field.type === 'color') {
            const hexVal = normalizeHexColor(
              String(val || getFieldDefault(field))
            );
            return (
              <Field
                key={field.key}
                label={field.label}
                htmlFor={`effect-field-${field.key}`}
                description={field.description}
                rightSlot={
                  modified ? (
                    <Badge tone="cyan" className="text-[10px]">
                      custom
                    </Badge>
                  ) : undefined
                }
              >
                <ColorPicker
                  id={`effect-field-${field.key}`}
                  value={hexVal}
                  onChange={(nextHex) => onChange(field.key, nextHex)}
                />
              </Field>
            );
          }

          return (
            <Field
              key={field.key}
              label={field.label}
              htmlFor={`effect-field-${field.key}`}
              description={field.description}
            >
              <Input
                id={`effect-field-${field.key}`}
                value={String(val)}
                placeholder={field.placeholder}
                onChange={(e) => onChange(field.key, e.target.value)}
              />
            </Field>
          );
        })}
      </div>
    </div>
  );
}
