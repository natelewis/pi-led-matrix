import { RotateCcw } from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  Field,
  NumberInput,
  SectionHeader,
  Slider,
  Switch,
} from '@/components/ui';
import { MatrixPreviewGrid } from '@/components/config/MatrixPreviewGrid';
import type {
  ColorOrder,
  ConfigSchemaMetadata,
  GpioPin,
  MatrixConfig,
} from '@/types/matrix';

interface DisplayPageProps {
  config: MatrixConfig;
  schema: ConfigSchemaMetadata;
  fieldErrors: Record<string, string>;
  onPatchField: <K extends keyof MatrixConfig>(key: K, value: MatrixConfig[K]) => void;
}

const DIMENSION_PRESETS = [
  { label: '128 × 72', width: 128, height: 72 },
  { label: '60 × 30', width: 60, height: 30 },
  { label: '32 × 32', width: 32, height: 32 },
  { label: '64 × 32', width: 64, height: 32 },
  { label: '120 × 30', width: 120, height: 30 },
];

const CHANNEL_COLORS: Record<string, string> = {
  r: 'bg-rose-500',
  g: 'bg-emerald-500',
  b: 'bg-sky-500',
};

export function DisplayPage({
  config,
  schema,
  fieldErrors,
  onPatchField,
}: DisplayPageProps) {
  const togglePin = (pin: GpioPin) => {
    const exists = config.pixel_pins.includes(pin);
    if (exists) {
      if (config.pixel_pins.length <= 1) return; // Require at least one pin
      onPatchField(
        'pixel_pins',
        config.pixel_pins.filter((p) => p !== pin)
      );
    } else {
      onPatchField('pixel_pins', [...config.pixel_pins, pin]);
    }
  };

  const panelDivisible =
    config.pixel_pins.length > 0 &&
    config.pixel_width % config.pixel_pins.length === 0;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Display & Hardware"
        description="Configure your LED matrix dimensions, GPIO data pins, strip wiring, color channel order, and image tuning."
      />

      {/* Live Preview Card */}
      <Card>
        <CardHeader
          title="Matrix Preview"
          description="Reflects your width, height, GPIO panel splits, and brightness/contrast/color values in real time."
        />
        <CardContent>
          <MatrixPreviewGrid config={config} />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Hardware & Wiring */}
        <Card>
          <CardHeader
            title="Panel Dimensions & Wiring"
            description="Total resolution across all chained or multi-pin panels."
          />
          <CardContent className="space-y-5">
            <div className="flex flex-wrap gap-1.5">
              {DIMENSION_PRESETS.map((preset) => {
                const active =
                  config.pixel_width === preset.width &&
                  config.pixel_height === preset.height;
                return (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => {
                      onPatchField('pixel_width', preset.width);
                      onPatchField('pixel_height', preset.height);
                    }}
                    className={`rounded-lg border px-2.5 py-1 font-mono text-xs transition-colors cursor-pointer ${
                      active
                        ? 'border-cyan-400/60 bg-cyan-500/15 text-cyan-200'
                        : 'border-slate-800 bg-surface-950 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                    }`}
                  >
                    {preset.label}
                  </button>
                );
              })}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Field
                label="Pixel Width"
                htmlFor="pixel-width"
                error={fieldErrors.pixel_width}
              >
                <NumberInput
                  id="pixel-width"
                  integer
                  min={1}
                  max={1024}
                  unit="px"
                  value={config.pixel_width}
                  hasError={Boolean(fieldErrors.pixel_width)}
                  onChange={(val) => onPatchField('pixel_width', val)}
                />
              </Field>

              <Field
                label="Pixel Height"
                htmlFor="pixel-height"
                error={fieldErrors.pixel_height}
              >
                <NumberInput
                  id="pixel-height"
                  integer
                  min={1}
                  max={1024}
                  unit="px"
                  value={config.pixel_height}
                  hasError={Boolean(fieldErrors.pixel_height)}
                  onChange={(val) => onPatchField('pixel_height', val)}
                />
              </Field>
            </div>

            <Field
              label="GPIO Pixel Pins"
              description="NeoPixel data pins driving the matrix. Multiple pins slice pixel_width evenly."
              error={
                fieldErrors.pixel_pins ||
                (!panelDivisible
                  ? `Width (${config.pixel_width}) must be evenly divisible by ${config.pixel_pins.length} pins.`
                  : undefined)
              }
            >
              <div className="grid grid-cols-4 gap-2">
                {schema.validPins.map((pin) => {
                  const selected = config.pixel_pins.includes(pin);
                  const orderIdx = config.pixel_pins.indexOf(pin);
                  return (
                    <button
                      key={pin}
                      type="button"
                      onClick={() => togglePin(pin)}
                      className={`flex items-center justify-center gap-1.5 rounded-xl border py-2.5 font-mono text-xs font-medium transition-all cursor-pointer ${
                        selected
                          ? 'border-cyan-400/70 bg-cyan-500/15 text-cyan-200 shadow-sm shadow-cyan-500/10'
                          : 'border-slate-800 bg-surface-950/70 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                      }`}
                    >
                      <span>{pin}</span>
                      {selected && config.pixel_pins.length > 1 && (
                        <span className="rounded bg-cyan-400/20 px-1 text-[10px] text-cyan-200">
                          #{orderIdx + 1}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </Field>

            <Switch
              checked={config.alternating}
              onChange={(val) => onPatchField('alternating', val)}
              label="Alternating (Zigzag) Wiring"
              description="Enable when LED strips snake up and down in a serpentine chain pattern."
            />
          </CardContent>
        </Card>

        {/* Image Tuning & Color Order */}
        <Card>
          <CardHeader
            title="Image Tuning & Color Order"
            description="Fine-tune brightness, contrast, saturation, and RGB strip channel order."
            action={
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
                onClick={() => {
                  onPatchField('brightness', 0.2);
                  onPatchField('contrast', 2);
                  onPatchField('color', 1.5);
                }}
              >
                Defaults
              </Button>
            }
          />
          <CardContent className="space-y-5">
            <Field
              label="Brightness"
              htmlFor="brightness-slider"
              error={fieldErrors.brightness}
              description="Global NeoPixel intensity (0.0 – 1.0). Keep lower on large panels to manage PSU draw."
              rightSlot={
                <Badge tone="cyan" className="font-mono">
                  {config.brightness.toFixed(2)} ({Math.round(config.brightness * 100)}%)
                </Badge>
              }
            >
              <Slider
                id="brightness-slider"
                min={0}
                max={1}
                step={0.01}
                value={config.brightness}
                marks={['0%', '25%', '50%', '75%', '100%']}
                onChange={(val) => onPatchField('brightness', val)}
              />
            </Field>

            <Field
              label="Contrast"
              htmlFor="contrast-slider"
              error={fieldErrors.contrast}
              description="Image contrast multiplier (1.0 = unchanged)."
              rightSlot={
                <Badge tone="neutral" className="font-mono">
                  {config.contrast.toFixed(2)}×
                </Badge>
              }
            >
              <Slider
                id="contrast-slider"
                min={0}
                max={5}
                step={0.1}
                value={config.contrast}
                marks={['0.0', '1.0', '2.5', '5.0']}
                onChange={(val) => onPatchField('contrast', val)}
              />
            </Field>

            <Field
              label="Color Saturation"
              htmlFor="color-slider"
              error={fieldErrors.color}
              description="Color saturation multiplier (1.0 = unchanged, 0.0 = grayscale)."
              rightSlot={
                <Badge tone="neutral" className="font-mono">
                  {config.color.toFixed(2)}×
                </Badge>
              }
            >
              <Slider
                id="color-slider"
                min={0}
                max={5}
                step={0.1}
                value={config.color}
                marks={['0.0', '1.0', '2.5', '5.0']}
                onChange={(val) => onPatchField('color', val)}
              />
            </Field>

            <Field
              label="LED Strip Color Order"
              description="Match your WS281x strip channel wiring if red/green/blue look swapped in rgb_test."
              error={fieldErrors.color_order}
            >
              <div className="grid grid-cols-3 gap-2">
                {schema.validColorOrders.map((order: ColorOrder) => {
                  const active = config.color_order === order;
                  return (
                    <button
                      key={order}
                      type="button"
                      onClick={() => onPatchField('color_order', order)}
                      className={`flex items-center justify-center gap-2 rounded-xl border py-2 font-mono text-xs uppercase transition-all cursor-pointer ${
                        active
                          ? 'border-cyan-400/70 bg-cyan-500/15 text-white'
                          : 'border-slate-800 bg-surface-950/70 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                      }`}
                    >
                      <span className="flex items-center gap-0.5">
                        {order.split('').map((ch, idx) => (
                          <span
                            key={`${ch}-${idx}`}
                            className={`h-2 w-2 rounded-full ${CHANNEL_COLORS[ch]}`}
                          />
                        ))}
                      </span>
                      <span>{order}</span>
                    </button>
                  );
                })}
              </div>
            </Field>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
