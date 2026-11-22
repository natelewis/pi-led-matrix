import { useEffect, useState } from 'react';
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
  const [text, setText] = useState<string>(() =>
    Number.isFinite(value) ? String(value) : ''
  );
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!focused) {
      setText(Number.isFinite(value) ? String(value) : '');
    }
  }, [value, focused]);

  return (
    <Input
      id={id}
      type="number"
      value={text}
      min={min}
      max={max}
      step={step}
      hasError={hasError}
      disabled={disabled}
      className="font-mono"
      rightSlot={
        unit ? <span className="font-mono text-[11px] text-slate-400">{unit}</span> : undefined
      }
      onFocus={() => setFocused(true)}
      onBlur={() => {
        setFocused(false);
        const parsed = integer ? parseInt(text, 10) : parseFloat(text);
        if (text.trim() === '' || Number.isNaN(parsed)) {
          setText(Number.isFinite(value) ? String(value) : '');
        } else {
          setText(String(parsed));
          if (parsed !== value) onChange(parsed);
        }
      }}
      onChange={(e) => {
        const raw = e.target.value;
        setText(raw);
        if (raw.trim() === '' || raw === '-' || raw === '.') return;
        const parsed = integer ? parseInt(raw, 10) : parseFloat(raw);
        if (!Number.isNaN(parsed) && Number.isFinite(parsed)) {
          onChange(parsed);
        }
      }}
    />
  );
}
