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
 * Supports both new declarative configs (`text` / `lines[]`) and legacy `messages[]`.
 * Returns null if no non-empty text is configured.
 */
export function extractMarqueeText(item: PlaylistItem): string | null {
  if (item.effect !== 'marquee') return null;
  const cfg = item.config;
  if (!cfg || typeof cfg !== 'object') return null;

  if (cfg.content_mode === 'layers' && Array.isArray(cfg.lines)) {
    const parts = cfg.lines
      .map((entry) => {
        if (!entry || typeof entry !== 'object') return '';
        const text = (entry as Record<string, unknown>).text;
        return typeof text === 'string' ? text.replace(/\s+/g, ' ').trim() : '';
      })
      .filter(Boolean);
    if (parts.length > 0) return parts.join(' · ');
  }

  if (typeof cfg.text === 'string' && cfg.text.trim().length > 0) {
    const cleaned = cfg.text
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l && l !== '---')
      .join(' · ');
    if (cleaned) return cleaned;
  }

  const rawMessages = cfg.messages;
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
