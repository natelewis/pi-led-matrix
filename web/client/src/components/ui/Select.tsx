import { useCallback, useEffect, useState, type ChangeEvent } from 'react';
import { Check } from 'lucide-react';
import { Dropdown } from './Dropdown';

export interface SelectOption {
  value: string;
  label: string;
  description?: string;
}

export interface SelectProps {
  id?: string;
  value?: string;
  options: SelectOption[];
  hasError?: boolean;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
  'aria-label'?: string;
  onChange?: (event: ChangeEvent<HTMLSelectElement>) => void;
  onValueChange?: (value: string) => void;
}

export function Select({
  id,
  value = '',
  options,
  hasError = false,
  disabled = false,
  className = '',
  placeholder = 'Select...',
  'aria-label': ariaLabel,
  onChange,
  onValueChange,
}: SelectProps) {
  const [open, setOpen] = useState(false);
  const selectedIndex = options.findIndex((opt) => opt.value === value);
  const [highlightedIndex, setHighlightedIndex] = useState<number>(
    selectedIndex >= 0 ? selectedIndex : 0
  );

  const selected = selectedIndex >= 0 ? options[selectedIndex] : undefined;

  const handleChoose = useCallback(
    (nextValue: string) => {
      setOpen(false);
      if (nextValue === value) return;
      onValueChange?.(nextValue);
      if (onChange) {
        const syntheticEvent = {
          target: { value: nextValue },
          currentTarget: { value: nextValue },
        } as ChangeEvent<HTMLSelectElement>;
        onChange(syntheticEvent);
      }
    },
    [value, onChange, onValueChange]
  );

  useEffect(() => {
    if (!open) return;
    setHighlightedIndex(selectedIndex >= 0 ? selectedIndex : 0);
  }, [open, selectedIndex]);

  useEffect(() => {
    if (!open || options.length === 0) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setHighlightedIndex((prev) => (prev + 1) % options.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setHighlightedIndex((prev) => (prev - 1 + options.length) % options.length);
      } else if (e.key === 'Home') {
        e.preventDefault();
        setHighlightedIndex(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        setHighlightedIndex(options.length - 1);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const opt = options[highlightedIndex];
        if (opt) handleChoose(opt.value);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, options, highlightedIndex, handleChoose]);

  return (
    <Dropdown
      id={id}
      open={open}
      onOpenChange={setOpen}
      disabled={disabled}
      hasError={hasError}
      ariaLabel={ariaLabel}
      triggerClassName={`min-h-9 ${className}`}
      trigger={
        <span className="block truncate text-xs font-medium text-slate-100">
          {selected?.label ?? (value || placeholder)}
        </span>
      }
    >
      <div role="listbox" className="overflow-y-auto p-1">
        {options.map((opt, idx) => {
          const isSelected = opt.value === value;
          const isHighlighted = idx === highlightedIndex;
          return (
            <button
              key={opt.value}
              type="button"
              role="option"
              aria-selected={isSelected}
              onMouseEnter={() => setHighlightedIndex(idx)}
              onClick={() => handleChoose(opt.value)}
              className={`flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-left transition-colors cursor-pointer ${
                isSelected
                  ? 'bg-cyan-500/15 text-cyan-100'
                  : isHighlighted
                    ? 'bg-surface-800/90 text-white'
                    : 'text-slate-300 hover:bg-surface-800/90 hover:text-white'
              }`}
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-medium">{opt.label}</div>
                {opt.description && (
                  <div className="truncate text-[11px] text-slate-400">
                    {opt.description}
                  </div>
                )}
              </div>
              {isSelected && <Check className="h-3.5 w-3.5 shrink-0 text-cyan-300" />}
            </button>
          );
        })}
      </div>
    </Dropdown>
  );
}
