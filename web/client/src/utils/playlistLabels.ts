import type { EffectMeta, PlaylistItem } from '@/types/matrix';

/**
 * Extracts the concise stem of an image/video filename (dropping `_uploads/`,
 * extension, and trailing `_WxH` dimension suffixes).
 * Example: `_uploads/my-cool_clip_128x72.mp4` -> `my-cool_clip`
 */
export function extractMediaShortName(filePath: string, maxLength = 32): string {
  const base = filePath.split('/').pop()?.trim() ?? '';
  if (!base) return '';

  const withoutExt = base.replace(/\.[^.]+$/, '');
  const withoutDims = withoutExt.replace(/_\d+x\d+$/, '');
  const cleaned = withoutDims.replace(/^_+/, '') || withoutExt;

  if (cleaned.length > maxLength) {
    return `${cleaned.slice(0, maxLength - 1)}…`;
  }
  return cleaned;
}

/**
 * Extracts the combined single-line text from a configured marquee effect.
 * Returns null if no non-empty messages are configured.
 */
export function extractMarqueeText(item: PlaylistItem): string | null {
  if (item.effect !== 'marquee') return null;
  const rawMessages = item.config?.messages;
  if (!Array.isArray(rawMessages)) return null;

  const parts = rawMessages
    .map((entry) => {
      if (!entry || typeof entry !== 'object') return '';
      const msg = (entry as Record<string, unknown>).message;
      return typeof msg === 'string' ? msg.replace(/\s+/g, ' ').trim() : '';
    })
    .filter(Boolean);

  if (parts.length === 0) return null;
  return parts.join(' ');
}

/**
 * Returns the human-readable playlist title for an entry.
 * - Configured `video` / `image`: `video: <name>` / `image: <name>`
 * - Configured `marquee`: `marquee: "<text>"`
 */
export function formatPlaylistItemLabel(
  item: PlaylistItem,
  meta?: EffectMeta
): string {
  if (item.effect === 'video' || item.effect === 'image') {
    const rawFile = item.config?.file;
    if (typeof rawFile === 'string' && rawFile.trim().length > 0) {
      const shortName = extractMediaShortName(rawFile);
      if (shortName) {
        return `${item.effect}: ${shortName}`;
      }
    }
  }

  if (item.effect === 'marquee') {
    const text = extractMarqueeText(item);
    if (text) {
      return `marquee: "${text}"`;
    }
  }

  return meta?.label ?? item.effect;
}
