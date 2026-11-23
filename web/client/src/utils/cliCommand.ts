import type { PlaylistItem } from '@/types/matrix';

/**
 * Builds the `make run` terminal command for a playlist entry,
 * including a shell-safe single-quoted JSON `config` argument when present.
 */
export function buildEffectRunCommand(item: PlaylistItem): string {
  const hasConfig =
    item.config && typeof item.config === 'object' && Object.keys(item.config).length > 0;

  if (!hasConfig) {
    return `make run effect=${item.effect}`;
  }

  const serialized = JSON.stringify(item.config);
  const shellSafe = serialized.replace(/'/g, "'\\''");
  return `make run effect=${item.effect} config='${shellSafe}'`;
}

/**
 * Copies text to clipboard with a fallback for non-HTTPS local network origins
 * (e.g. http://<raspberry-pi-ip>:8080 where navigator.clipboard may be unavailable).
 */
export async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  const ok = document.execCommand('copy');
  document.body.removeChild(textarea);
  if (!ok) {
    throw new Error('Unable to copy to clipboard');
  }
}
