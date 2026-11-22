import {
  ArrowRight,
  Cpu,
  ListMusic,
  Monitor,
  SlidersHorizontal,
  Sparkles,
  Sun,
} from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  SectionHeader,
} from '@/components/ui';
import { MatrixPreviewGrid } from '@/components/config/MatrixPreviewGrid';
import { formatPlaylistItemLabel } from '@/utils/playlistLabels';
import type { EffectMeta, MatrixConfig, NavSectionId } from '@/types/matrix';

interface OverviewPageProps {
  config: MatrixConfig;
  source: 'custom' | 'default';
  updatedAt: string | null;
  effects: EffectMeta[];
  onNavigate: (section: NavSectionId) => void;
}

export function OverviewPage({
  config,
  source,
  updatedAt,
  effects,
  onNavigate,
}: OverviewPageProps) {
  const uniquePlaylistEffects = new Set(config.playlist.map((p) => p.effect)).size;
  const totalPixels = config.pixel_width * config.pixel_height;

  const stats = [
    {
      label: 'Matrix Geometry',
      value: `${config.pixel_width} × ${config.pixel_height}`,
      sub: `${totalPixels.toLocaleString()} LEDs · ${config.pixel_pins.join(', ')}`,
      icon: Cpu,
      tone: 'text-cyan-400',
    },
    {
      label: 'Active Playlist',
      value: `${config.playlist.length} entries`,
      sub: `${uniquePlaylistEffects} unique · ${config.playlist_delay}s per effect`,
      icon: ListMusic,
      tone: 'text-emerald-400',
    },
    {
      label: 'Brightness & Color',
      value: `${Math.round(config.brightness * 100)}%`,
      sub: `Contrast ${config.contrast} · Color ${config.color} · ${config.color_order.toUpperCase()}`,
      icon: Sun,
      tone: 'text-amber-400',
    },
    {
      label: 'Output Mode',
      value: config.virtual ? 'Virtual Display' : 'Hardware Auto',
      sub: config.virtual
        ? `${config.virtual_framerate}ms frame delay · ${config.virtual_fullscreen ? 'Fullscreen' : 'Windowed'}`
        : 'Uses NeoPixel GPIO on Pi, virtual on macOS',
      icon: Monitor,
      tone: 'text-violet-400',
    },
  ];

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Matrix Overview"
        description="Review your current configuration at a glance or jump straight into editing."
        actions={
          <>
            <Button
              variant="secondary"
              onClick={() => onNavigate('display')}
              leftIcon={<SlidersHorizontal className="h-4 w-4" />}
            >
              Tune Display
            </Button>
            <Button
              variant="primary"
              onClick={() => onNavigate('playlist')}
              leftIcon={<ListMusic className="h-4 w-4" />}
            >
              Edit Playlist
            </Button>
          </>
        }
      />

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-400">{stat.label}</span>
                  <Icon className={`h-4 w-4 ${stat.tone}`} />
                </div>
                <div className="mt-2 font-mono text-xl font-semibold text-white">
                  {stat.value}
                </div>
                <div className="mt-1 truncate text-xs text-slate-400">{stat.sub}</div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Preview + Playlist Summary */}
      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader
            title="Live Panel Layout Preview"
            description="Proportional preview of matrix dimensions, GPIO panel splits, and visual settings."
            action={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onNavigate('display')}
                rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
              >
                Configure
              </Button>
            }
          />
          <CardContent>
            <MatrixPreviewGrid config={config} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title="Playlist Snapshot"
            description={`${config.playlist.length} queued from ${effects.length} discovered effects`}
            action={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onNavigate('playlist')}
                rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
              >
                Manage
              </Button>
            }
          />
          <CardContent className="space-y-3">
            {config.playlist.length === 0 ? (
              <p className="text-xs text-slate-400">
                No effects in the playlist yet. Open the Playlist tab to add some.
              </p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {config.playlist.slice(0, 18).map((entry, idx) => (
                  <Badge
                    key={`${entry.effect}-${idx}`}
                    tone={entry.config ? 'emerald' : 'neutral'}
                  >
                    {entry.effect === 'video' || entry.effect === 'image'
                      ? formatPlaylistItemLabel(entry)
                      : entry.effect}
                  </Badge>
                ))}
                {config.playlist.length > 18 && (
                  <Badge tone="cyan">+{config.playlist.length - 18} more</Badge>
                )}
              </div>
            )}

            <div className="rounded-xl border border-slate-800/80 bg-surface-950/60 p-3.5 text-xs text-slate-400">
              <div className="flex items-center gap-2 font-medium text-slate-200">
                <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                <span>Configuration Source</span>
              </div>
              <p className="mt-1.5 leading-relaxed">
                {source === 'custom'
                  ? `Reading and saving directly to config.json.${
                      updatedAt
                        ? ` Last updated ${new Date(updatedAt).toLocaleString()}.`
                        : ''
                    }`
                  : 'Currently showing default_config.json. Your first save will create config.json while keeping defaults untouched.'}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
