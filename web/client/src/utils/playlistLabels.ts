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
 * Returns the human-readable playlist title for an entry.
 * For configured `video` and `image` entries, formats as `video: <name>` / `image: <name>`.
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

  return meta?.label ?? item.effect;
}
