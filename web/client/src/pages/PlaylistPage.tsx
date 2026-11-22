import { useMemo, useState } from 'react';
import {
  Check,
  Clock,
  Copy,
  ListMusic,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  EmptyState,
  Field,
  Input,
  NumberInput,
  SectionHeader,
  useToast,
} from '@/components/ui';
import { EffectConfigModal } from '@/components/config/EffectConfigModal';
import { PlaylistItemRow } from '@/components/config/PlaylistItemRow';
import { copyToClipboard } from '@/utils/cliCommand';
import type {
  EffectCategory,
  EffectMeta,
  MatrixConfig,
  PlaylistItem,
} from '@/types/matrix';

interface PlaylistPageProps {
  config: MatrixConfig;
  effects: EffectMeta[];
  effectMap: Map<string, EffectMeta>;
  fonts: string[];
  fieldErrors: Record<string, string>;
  playingIndex: number | null;
  playbackBusy: boolean;
  isDirty: boolean;
  onPlayPlaylistItem: (index: number, item: PlaylistItem) => void;
  onUpdateConfig: (updater: (prev: MatrixConfig) => MatrixConfig) => void;
  onEffectsChanged?: () => void;
}

const CATEGORIES: { id: 'all' | EffectCategory; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'animation', label: 'Animations' },
  { id: 'game', label: 'Games' },
  { id: 'text', label: 'Text' },
  { id: 'media', label: 'Media' },
  { id: 'utility', label: 'Utility' },
];

export function PlaylistPage({
  config,
  effects,
  effectMap,
  fonts,
  fieldErrors,
  playingIndex,
  playbackBusy,
  isDirty,
  onPlayPlaylistItem,
  onUpdateConfig,
  onEffectsChanged,
}: PlaylistPageProps) {
  const { notify } = useToast();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<'all' | EffectCategory>('all');
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [copiedPlaylistJson, setCopiedPlaylistJson] = useState(false);

  const handleCopyCommand = async (command: string) => {
    try {
      await copyToClipboard(command);
      notify('success', 'Copied terminal command', command);
    } catch {
      notify('error', 'Copy failed', 'Could not access clipboard.');
    }
  };

  const handleCopyPlaylistJson = async () => {
    try {
      const json = JSON.stringify(config.playlist, null, 4);
      await copyToClipboard(json);
      setCopiedPlaylistJson(true);
      notify('success', 'Copied playlist JSON', `${config.playlist.length} entries copied.`);
      window.setTimeout(() => setCopiedPlaylistJson(false), 1800);
    } catch {
      notify('error', 'Copy failed', 'Could not access clipboard.');
    }
  };

  const countsInPlaylist = useMemo(() => {
    const map = new Map<string, number>();
    for (const entry of config.playlist) {
      map.set(entry.effect, (map.get(entry.effect) ?? 0) + 1);
    }
    return map;
  }, [config.playlist]);

  const filteredCatalog = useMemo(() => {
    const query = search.trim().toLowerCase();
    return effects.filter((fx) => {
      if (category !== 'all' && fx.category !== category) return false;
      if (!query) return true;
      return (
        fx.id.toLowerCase().includes(query) ||
        fx.label.toLowerCase().includes(query) ||
        fx.description.toLowerCase().includes(query)
      );
    });
  }, [effects, search, category]);

  const addEffect = (fx: EffectMeta) => {
    const nextItem: PlaylistItem = { effect: fx.id };
    const newIndex = config.playlist.length;
    onUpdateConfig((prev) => ({
      ...prev,
      playlist: [...prev.playlist, nextItem],
    }));
    if (fx.configSchema !== 'none') {
      setEditingIndex(newIndex);
    }
  };

  const addAllStandard = () => {
    const standard = effects
      .filter((fx) => !fx.isUtility && fx.configSchema === 'none')
      .map((fx) => ({ effect: fx.id }));
    onUpdateConfig((prev) => ({
      ...prev,
      playlist: [...prev.playlist, ...standard],
    }));
  };

  const removeAt = (index: number) => {
    onUpdateConfig((prev) => ({
      ...prev,
      playlist: prev.playlist.filter((_, i) => i !== index),
    }));
  };

  const duplicateAt = (index: number) => {
    onUpdateConfig((prev) => {
      const target = prev.playlist[index];
      if (!target) return prev;
      const next = [...prev.playlist];
      next.splice(index + 1, 0, structuredClone(target));
      return { ...prev, playlist: next };
    });
  };

  const moveItem = (from: number, to: number) => {
    if (from === to || to < 0 || to >= config.playlist.length) return;
    onUpdateConfig((prev) => {
      const next = [...prev.playlist];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return { ...prev, playlist: next };
    });
  };

  const updateItemConfig = (index: number, nextEffectConfig?: Record<string, unknown>) => {
    onUpdateConfig((prev) => ({
      ...prev,
      playlist: prev.playlist.map((entry, i) => {
        if (i !== index) return entry;
        const copy = { ...entry };
        if (nextEffectConfig && Object.keys(nextEffectConfig).length > 0) {
          copy.config = nextEffectConfig;
        } else {
          delete copy.config;
        }
        return copy;
      }),
    }));
  };

  const editingItem =
    editingIndex !== null ? config.playlist[editingIndex] ?? null : null;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Playlist Builder"
        description="Build your effect rotation, drag to reorder, duplicate favorites to weight random playback, and configure per-effect parameters."
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={addAllStandard}
              leftIcon={<Sparkles className="h-3.5 w-3.5" />}
            >
              Add All Visual Effects
            </Button>
            {config.playlist.length > 0 && (
              <Button
                variant="danger"
                size="sm"
                onClick={() =>
                  onUpdateConfig((prev) => ({ ...prev, playlist: [] }))
                }
                leftIcon={<Trash2 className="h-3.5 w-3.5" />}
              >
                Clear Playlist
              </Button>
            )}
          </>
        }
      />

      {/* Timing bar */}
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/12 text-cyan-300">
              <Clock className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-medium text-white">Effect Rotation Delay</div>
              <p className="text-xs text-slate-400">
                How long each effect runs before switching to the next random entry in the playlist.
              </p>
            </div>
          </div>

          <div className="w-full sm:w-44">
            <Field
              label="Delay (seconds)"
              htmlFor="playlist-delay"
              error={fieldErrors.playlist_delay}
            >
              <NumberInput
                id="playlist-delay"
                integer
                min={1}
                max={86400}
                unit="sec"
                value={config.playlist_delay}
                hasError={Boolean(fieldErrors.playlist_delay)}
                onChange={(val) =>
                  onUpdateConfig((prev) => ({ ...prev, playlist_delay: val }))
                }
              />
            </Field>
          </div>
        </CardContent>
      </Card>

      {/* Split View: Active Playlist + Effects Catalog */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Active Playlist */}
        <Card className="lg:col-span-7">
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <span>Active Playlist</span>
                <Badge tone="cyan">{config.playlist.length}</Badge>
              </span>
            }
            description="Drag to reorder, click the terminal icon to copy a `make run` command, or duplicate to weight random picks."
            action={
              config.playlist.length > 0 ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => void handleCopyPlaylistJson()}
                  leftIcon={
                    copiedPlaylistJson ? (
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )
                  }
                >
                  {copiedPlaylistJson ? 'Copied JSON' : 'Copy JSON'}
                </Button>
              ) : undefined
            }
          />
          <CardContent className="space-y-2">
            {fieldErrors.playlist && (
              <p className="mb-2 text-xs text-rose-400">{fieldErrors.playlist}</p>
            )}

            {config.playlist.length === 0 ? (
              <EmptyState
                icon={<ListMusic className="h-5 w-5" />}
                title="Your playlist is empty"
                description="Pick effects from the catalog on the right to start building your LED matrix rotation."
                action={
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={addAllStandard}
                    leftIcon={<Sparkles className="h-3.5 w-3.5" />}
                  >
                    Populate with All Visual Effects
                  </Button>
                }
              />
            ) : (
              config.playlist.map((item, idx) => (
                <PlaylistItemRow
                  key={`${item.effect}-${idx}`}
                  index={idx}
                  total={config.playlist.length}
                  item={item}
                  meta={effectMap.get(item.effect)}
                  isPlaying={!isDirty && playingIndex === idx}
                  playDisabled={playbackBusy}
                  errorMessage={fieldErrors[`playlist.${idx}`]}
                  isDragging={dragIndex === idx}
                  isDragOver={dragOverIndex === idx && dragIndex !== idx}
                  onDragStart={() => setDragIndex(idx)}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOverIndex(idx);
                  }}
                  onDrop={() => {
                    if (dragIndex !== null) {
                      moveItem(dragIndex, idx);
                    }
                    setDragIndex(null);
                    setDragOverIndex(null);
                  }}
                  onDragEnd={() => {
                    setDragIndex(null);
                    setDragOverIndex(null);
                  }}
                  onMoveUp={() => moveItem(idx, idx - 1)}
                  onMoveDown={() => moveItem(idx, idx + 1)}
                  onPlayNow={() => onPlayPlaylistItem(idx, item)}
                  onCopyCommand={(cmd) => void handleCopyCommand(cmd)}
                  onDuplicate={() => duplicateAt(idx)}
                  onConfigure={() => setEditingIndex(idx)}
                  onRemove={() => removeAt(idx)}
                />
              ))
            )}
          </CardContent>
        </Card>

        {/* Effects Catalog */}
        <Card className="lg:col-span-5">
          <CardHeader
            title="Effects Catalog"
            description={`Auto-discovered from src/effects/ (${effects.length} available)`}
          />
          <CardContent className="space-y-4">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search effects..."
              leftIcon={<Search className="h-4 w-4" />}
            />

            <div className="flex flex-wrap gap-1.5">
              {CATEGORIES.map((cat) => {
                const active = category === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setCategory(cat.id)}
                    className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
                      active
                        ? 'bg-cyan-500/20 text-cyan-200 ring-1 ring-cyan-500/40'
                        : 'bg-surface-950 text-slate-400 hover:bg-surface-800 hover:text-slate-200'
                    }`}
                  >
                    {cat.label}
                  </button>
                );
              })}
            </div>

            <div className="max-h-[540px] space-y-2 overflow-y-auto pr-1">
              {filteredCatalog.map((fx) => {
                const count = countsInPlaylist.get(fx.id) ?? 0;
                return (
                  <div
                    key={fx.id}
                    className="flex items-center justify-between gap-3 rounded-xl border border-slate-800/80 bg-surface-950/70 px-3 py-2.5 transition-colors hover:border-slate-700"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium text-slate-100">
                          {fx.label}
                        </span>
                        {count > 0 && <Badge tone="cyan">×{count}</Badge>}
                        {fx.configSchema !== 'none' && (
                          <Badge tone="amber">configurable</Badge>
                        )}
                      </div>
                      <p className="mt-0.5 truncate text-xs text-slate-400">
                        {fx.description}
                      </p>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => addEffect(fx)}
                      leftIcon={<Plus className="h-3.5 w-3.5" />}
                    >
                      Add
                    </Button>
                  </div>
                );
              })}
              {filteredCatalog.length === 0 && (
                <p className="py-8 text-center text-xs text-slate-500">
                  No effects match "{search}".
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <EffectConfigModal
        open={editingIndex !== null}
        item={editingItem}
        effectMeta={editingItem ? effectMap.get(editingItem.effect) : undefined}
        fonts={fonts}
        pixelWidth={config.pixel_width}
        pixelHeight={config.pixel_height}
        ledDots={config.virtual_led_dots}
        onEffectsChanged={onEffectsChanged}
        onClose={() => setEditingIndex(null)}
        onSave={(nextCfg) => {
          if (editingIndex !== null) {
            updateItemConfig(editingIndex, nextCfg);
          }
        }}
      />
    </div>
  );
}
