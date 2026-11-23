import { Keyboard } from 'lucide-react';
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  Field,
  NumberInput,
  SectionHeader,
  Slider,
  Switch,
} from '@/components/ui';
import type { MatrixConfig } from '@/types/matrix';

interface VirtualPageProps {
  config: MatrixConfig;
  fieldErrors: Record<string, string>;
  onPatchField: <K extends keyof MatrixConfig>(key: K, value: MatrixConfig[K]) => void;
}

const SHORTCUTS = [
  { key: 'F', action: 'Toggle fullscreen display' },
  { key: 'D', action: 'Toggle round LED dot mask' },
  { key: 'Space / Right / N', action: 'Skip to next playlist effect' },
  { key: 'Q / Esc', action: 'Quit virtual simulator' },
];

export function VirtualPage({
  config,
  fieldErrors,
  onPatchField,
}: VirtualPageProps) {
  const approxFps =
    config.virtual_framerate > 0
      ? Math.round((1000 / config.virtual_framerate) * 10) / 10
      : 0;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Virtual Simulator"
        description="Control how the Pygame virtual monitor renders when testing on macOS or running on a TV/monitor attached to your Pi."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Simulator Settings"
            description="These options map directly to VirtualMatrix in src/main.py."
          />
          <CardContent className="space-y-4">
            <Switch
              checked={config.virtual}
              onChange={(val) => onPatchField('virtual', val)}
              label="Force Virtual Monitor Mode"
              description="Run in a Pygame window even on a Raspberry Pi with Adafruit NeoPixel libraries installed."
            />

            <Switch
              checked={config.virtual_fullscreen}
              onChange={(val) => onPatchField('virtual_fullscreen', val)}
              label="Launch Fullscreen"
              description="Open the virtual matrix fullscreen and hide the mouse cursor automatically."
            />

            <Switch
              checked={config.virtual_led_dots}
              onChange={(val) => onPatchField('virtual_led_dots', val)}
              label="Round LED Dot Mask"
              description="Render pixels as circular LED diodes instead of solid square blocks."
            />

            <div className="rounded-xl border border-slate-800/80 bg-surface-950/60 p-4 space-y-4">
              <Field
                label="Virtual Frame Delay (ms)"
                htmlFor="virtual-framerate"
                description="Delay between frames in milliseconds to mimic physical strip refresh latency."
                error={fieldErrors.virtual_framerate}
                rightSlot={
                  <Badge tone="cyan" className="font-mono">
                    ~{approxFps} FPS
                  </Badge>
                }
              >
                <div className="grid items-center gap-4 sm:grid-cols-3">
                  <div className="sm:col-span-2">
                    <Slider
                      min={1}
                      max={250}
                      step={1}
                      value={Math.min(250, config.virtual_framerate)}
                      marks={['1ms (fast)', '75ms (default)', '250ms (slow)']}
                      onChange={(val) => onPatchField('virtual_framerate', val)}
                    />
                  </div>
                  <NumberInput
                    id="virtual-framerate"
                    integer
                    min={1}
                    max={5000}
                    unit="ms"
                    value={config.virtual_framerate}
                    hasError={Boolean(fieldErrors.virtual_framerate)}
                    onChange={(val) => onPatchField('virtual_framerate', val)}
                  />
                </div>
              </Field>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <Keyboard className="h-4 w-4 text-cyan-400" />
                <span>Simulator Hotkeys</span>
              </span>
            }
            description="Available while the Pygame window is focused."
          />
          <CardContent className="space-y-2.5">
            {SHORTCUTS.map((item) => (
              <div
                key={item.key}
                className="flex items-center justify-between gap-3 rounded-xl border border-slate-800/80 bg-surface-950/60 px-3 py-2.5"
              >
                <span className="text-xs text-slate-300">{item.action}</span>
                <kbd className="shrink-0 rounded-md border border-slate-700 bg-surface-850 px-2 py-0.5 font-mono text-[11px] text-cyan-200">
                  {item.key}
                </kbd>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
