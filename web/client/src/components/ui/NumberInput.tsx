import { Input } from './Input';

export interface NumberInputProps {
  id?: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  hasError?: boolean;
  disabled?: boolean;
  integer?: boolean;
}

export function NumberInput({
  id,
  value,
  onChange,
  min,
  max,
  step = 1,
  unit,
  hasError,
  disabled,
  integer = false,
}: NumberInputProps) {
  return (
    <Input
      id={id}
      type="number"
      value={Number.isFinite(value) ? value : ''}
      min={min}
      max={max}
      step={step}
      hasError={hasError}
      disabled={disabled}
      className="font-mono"
      rightSlot={
        unit ? <span className="font-mono text-[11px] text-slate-400">{unit}</span> : undefined
      }
      onChange={(e) => {
        const raw = e.target.value;
        if (raw === '') return;
        const parsed = integer ? parseInt(raw, 10) : parseFloat(raw);
        if (!Number.isNaN(parsed)) {
          onChange(parsed);
        }
      }}
    />
  );
}
