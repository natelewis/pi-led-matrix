export interface SliderProps {
  id?: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  marks?: string[];
  disabled?: boolean;
}

export function Slider({
  id,
  value,
  onChange,
  min,
  max,
  step = 0.05,
  marks,
  disabled,
}: SliderProps) {
  return (
    <div className="space-y-1.5">
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="led-slider w-full disabled:opacity-50"
      />
      {marks && marks.length > 0 && (
        <div className="flex justify-between font-mono text-[10px] text-slate-500">
          {marks.map((mark) => (
            <span key={mark}>{mark}</span>
          ))}
        </div>
      )}
    </div>
  );
}
