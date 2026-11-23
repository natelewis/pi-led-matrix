import { useMemo } from 'react';
import type { MatrixConfig } from '@/types/matrix';

interface MatrixPreviewGridProps {
  config: MatrixConfig;
  compact?: boolean;
}

/**
 * Interactive visual representation of the LED matrix geometry, panel splits
 * per GPIO pin, LED dot rendering, alternating wiring, and color/brightness feel.
 */
export function MatrixPreviewGrid({ config, compact = false }: MatrixPreviewGridProps) {
  const cols = Math.max(1, Math.min(config.pixel_width, 60));
  const rows = Math.max(1, Math.min(config.pixel_height, 30));

  const sampleCols = compact ? Math.min(cols, 30) : Math.min(cols, 40);
  const sampleRows = compact ? Math.min(rows, 15) : Math.min(rows, 20);

  const cells = useMemo(() => {
    const out: { x: number; y: number; hue: number; lightness: number }[] = [];
    for (let y = 0; y < sampleRows; y++) {
      for (let x = 0; x < sampleCols; x++) {
        const dx = (x / Math.max(1, sampleCols - 1)) - 0.5;
        const dy = (y / Math.max(1, sampleRows - 1)) - 0.5;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const hue = (190 + x * 4 + y * 5 + Math.sin(dist * 10) * 35) % 360;
        const wave = 0.5 + 0.5 * Math.cos(dist * 9.5);
        const lightness = 22 + wave * 42;
        out.push({ x, y, hue, lightness });
      }
    }
    return out;
  }, [sampleCols, sampleRows]);

  const pinCount = Math.max(1, config.pixel_pins.length);
  const panelWidth = config.pixel_width / pinCount;
  const isEvenSplit = config.pixel_width % pinCount === 0;
  const effectiveOpacity = Math.max(0.22, Math.min(1, 0.25 + config.brightness * 0.75));
  const effectiveSaturation = Math.max(0, Math.min(250, Math.round(config.color * 100)));
  const effectiveContrast = Math.max(40, Math.min(200, Math.round(config.contrast * 65 + 35)));

  return (
    <div className="space-y-3">
      <div className="relative overflow-hidden rounded-xl border border-slate-800 bg-black p-3 shadow-inner">
        <div
          className="relative mx-auto w-full"
          style={{
            aspectRatio: `${Math.max(1, config.pixel_width)} / ${Math.max(1, config.pixel_height)}`,
            maxHeight: compact ? '160px' : '240px',
          }}
        >
          <div
            className="grid h-full w-full gap-[2px]"
            style={{
              gridTemplateColumns: `repeat(${sampleCols}, minmax(0, 1fr))`,
              gridTemplateRows: `repeat(${sampleRows}, minmax(0, 1fr))`,
              filter: `saturate(${effectiveSaturation}%) contrast(${effectiveContrast}%)`,
              opacity: effectiveOpacity,
            }}
          >
            {cells.map((cell) => (
              <div
                key={`${cell.x}-${cell.y}`}
                className={config.virtual_led_dots ? 'rounded-full' : 'rounded-[1px]'}
                style={{
                  backgroundColor: `hsl(${cell.hue}, 92%, ${cell.lightness}%)`,
                }}
              />
            ))}
          </div>

          {/* Panel division overlays */}
          <div className="pointer-events-none absolute inset-0 flex">
            {config.pixel_pins.map((pin, idx) => (
              <div
                key={`${pin}-${idx}`}
                className={`relative flex-1 ${
                  idx > 0 ? 'border-l border-dashed border-cyan-400/60' : ''
                }`}
              >
                <span className="absolute left-1.5 top-1.5 rounded bg-black/80 px-1.5 py-0.5 font-mono text-[10px] font-medium text-cyan-300 ring-1 ring-cyan-400/30">
                  {pin}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono">
          <span>
            {config.pixel_width}×{config.pixel_height} ({config.pixel_width * config.pixel_height}{' '}
            LEDs)
          </span>
          <span>
            {pinCount} {pinCount === 1 ? 'panel' : 'panels'}{' '}
            {isEvenSplit ? `(${panelWidth}px wide each)` : '(uneven split!)'}
          </span>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="uppercase">{config.color_order}</span>
          <span>·</span>
          <span>{config.alternating ? 'Zigzag' : 'Progressive'}</span>
          <span>·</span>
          <span>{config.virtual_led_dots ? 'LED dots' : 'Square'}</span>
        </div>
      </div>
    </div>
  );
}
