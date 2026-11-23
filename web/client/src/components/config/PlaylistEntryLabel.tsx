import {
  extractMarqueeText,
  formatPlaylistItemLabel,
} from '@/utils/playlistLabels';
import type { EffectMeta, PlaylistItem } from '@/types/matrix';

export interface PlaylistEntryLabelProps {
  item: PlaylistItem;
  meta?: EffectMeta;
  /** When true, falls back to raw effect ID for unconfigured non-media items (e.g. compact badges). */
  compact?: boolean;
  className?: string;
}

/**
 * Renders a playlist entry's label with dynamic CSS ellipsis truncation.
 * Configured marquee entries keep both quotes intact while dynamically
 * truncating the inner message text (`marquee: “something something…”`).
 */
export function PlaylistEntryLabel({
  item,
  meta,
  compact = false,
  className = '',
}: PlaylistEntryLabelProps) {
  const marqueeText = extractMarqueeText(item);
  if (marqueeText) {
    return (
      <span
        className={`inline-flex min-w-0 max-w-full items-baseline ${className}`}
        title={`marquee: "${marqueeText}"`}
      >
        <span className="shrink-0">marquee: &ldquo;</span>
        <span className="min-w-0 truncate">{marqueeText}</span>
        <span className="shrink-0">&rdquo;</span>
      </span>
    );
  }

  const label =
    compact && item.effect !== 'video' && item.effect !== 'image'
      ? item.effect
      : formatPlaylistItemLabel(item, meta);

  return (
    <span className={`min-w-0 truncate ${className}`} title={label}>
      {label}
    </span>
  );
}
