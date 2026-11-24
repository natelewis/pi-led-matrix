import type {
  AuthStatus,
  ConfigResponse,
  EffectPreviewResponse,
  EffectsResponse,
  FontMeta,
  GitPullResponse,
  GitStatusResponse,
  ImageFilesResponse,
  ImageUploadResponse,
  LiveFrameData,
  MatrixConfig,
  MatrixTarget,
  PlaybackStatus,
  TargetProbeResult,
  TargetsState,
  VideoFilesResponse,
  VideoUploadResponse,
} from '@/types/matrix';

export class ApiError extends Error {
  status: number;
  fields?: Record<string, string>;
  remoteAuthRequired?: boolean;
  remoteUnreachable?: boolean;
  targetId?: string;

  constructor(
    message: string,
    status: number,
    fields?: Record<string, string>,
    extra?: {
      remoteAuthRequired?: boolean;
      remoteUnreachable?: boolean;
      targetId?: string;
    }
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fields = fields;
    this.remoteAuthRequired = extra?.remoteAuthRequired;
    this.remoteUnreachable = extra?.remoteUnreachable;
    this.targetId = extra?.targetId;
  }
}

let activeTargetHeaderId = 'local';

export function setActiveTargetHeader(targetId: string): void {
  activeTargetHeaderId = targetId || 'local';
}

const LOCAL_ONLY_API_PREFIXES = ['/api/health', '/api/auth/', '/api/targets'];

function isTargetScopedPath(path: string): boolean {
  return !LOCAL_ONLY_API_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(prefix)
  );
}

function parseResponseJson(text: string): Record<string, unknown> {
  if (!text) return {};
  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const targetHeaders: Record<string, string> = isTargetScopedPath(path)
    ? { 'X-Matrix-Target': activeTargetHeaderId }
    : {};

  const response = await fetch(path, {
    ...init,
    credentials: 'include',
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...targetHeaders,
      ...init?.headers,
    },
  });

  const text = await response.text();
  const data = parseResponseJson(text);

  if (!response.ok) {
    throw new ApiError(
      (typeof data.error === 'string' && data.error) ||
        response.statusText ||
        `Request failed (${response.status})`,
      response.status,
      data.fields as Record<string, string> | undefined,
      {
        remoteAuthRequired:
          Boolean(data.remoteAuthRequired) ||
          response.headers.get('X-Remote-Auth-Required') === '1',
        remoteUnreachable: Boolean(data.remoteUnreachable),
        targetId: typeof data.targetId === 'string' ? data.targetId : undefined,
      }
    );
  }

  return data as T;
}

export const api = {
  auth: {
    status: () => request<AuthStatus>('/api/auth/status'),
    setup: (password: string) =>
      request<AuthStatus>('/api/auth/setup', {
        method: 'POST',
        body: JSON.stringify({ password }),
      }),
    login: (password: string) =>
      request<AuthStatus>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
      }),
    logout: () =>
      request<{ authenticated: boolean }>('/api/auth/logout', {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    changePassword: (currentPassword: string, newPassword: string) =>
      request<{ ok: boolean }>('/api/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ currentPassword, newPassword }),
      }),
  },

  fonts: {
    list: () => request<{ fonts: FontMeta[] }>('/api/fonts'),
    fileUrl: (file: string) =>
      `/api/fonts/file?file=${encodeURIComponent(file)}&_target=${encodeURIComponent(activeTargetHeaderId)}`,
    upload: (filename: string, dataBase64: string) =>
      request<{ font: FontMeta; fonts: FontMeta[] }>('/api/fonts/upload', {
        method: 'POST',
        body: JSON.stringify({ filename, dataBase64 }),
      }),
    deleteFile: (file: string) =>
      request<{ deleted: string; fonts: FontMeta[] }>(
        `/api/fonts/file?file=${encodeURIComponent(file)}`,
        { method: 'DELETE' }
      ),
  },

  config: {
    get: () => request<ConfigResponse>('/api/config'),
    save: (config: MatrixConfig) =>
      request<ConfigResponse>('/api/config', {
        method: 'PUT',
        body: JSON.stringify({ config }),
      }),
    reset: () =>
      request<ConfigResponse>('/api/config/reset', {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    defaults: () => request<{ config: MatrixConfig }>('/api/config/defaults'),
  },

  effects: {
    list: () => request<EffectsResponse>('/api/effects'),
    preview: (
      effectId: string,
      payload: { config: Record<string, unknown>; width?: number; height?: number },
      signal?: AbortSignal
    ) =>
      request<EffectPreviewResponse>(
        `/api/effects/${encodeURIComponent(effectId)}/preview`,
        {
          method: 'POST',
          body: JSON.stringify(payload),
          signal,
        }
      ),
    image: {
      listFiles: () => request<ImageFilesResponse>('/api/effects/image/files'),
      upload: (payload: {
        filename: string;
        width: number;
        height: number;
        rgbaBase64: string;
      }) =>
        request<ImageUploadResponse>('/api/effects/image/upload', {
          method: 'POST',
          body: JSON.stringify(payload),
        }),
      deleteFile: (file: string) =>
        request<{ deleted: string; files: ImageFilesResponse['files'] }>(
          `/api/effects/image/file?file=${encodeURIComponent(file)}`,
          { method: 'DELETE' }
        ),
      previewUrl: (file: string) =>
        `/api/effects/image/file?file=${encodeURIComponent(file)}&_target=${encodeURIComponent(activeTargetHeaderId)}`,
    },
    video: {
      listFiles: () => request<VideoFilesResponse>('/api/effects/video/files'),
      upload: async (
        file: File,
        options: {
          filename: string;
          width: number;
          height: number;
          fitMode: 'crop' | 'contain' | 'stretch';
          cropX?: number;
          cropY?: number;
          cropW?: number;
          cropH?: number;
          startSec?: number;
          endSec?: number;
        }
      ): Promise<VideoUploadResponse> => {
        const params = new URLSearchParams({
          filename: options.filename,
          width: String(options.width),
          height: String(options.height),
          fitMode: options.fitMode,
        });
        if (
          options.fitMode === 'crop' &&
          options.cropX !== undefined &&
          options.cropY !== undefined &&
          options.cropW !== undefined &&
          options.cropH !== undefined
        ) {
          params.set('cropX', String(Math.round(options.cropX)));
          params.set('cropY', String(Math.round(options.cropY)));
          params.set('cropW', String(Math.round(options.cropW)));
          params.set('cropH', String(Math.round(options.cropH)));
        }
        if (options.startSec !== undefined && options.startSec > 0) {
          params.set('startSec', String(options.startSec));
        }
        if (options.endSec !== undefined && options.endSec > 0) {
          params.set('endSec', String(options.endSec));
        }

        const response = await fetch(`/api/effects/video/upload?${params.toString()}`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': file.type || 'application/octet-stream',
            'X-Matrix-Target': activeTargetHeaderId,
          },
          body: file,
        });
        const text = await response.text();
        const data = parseResponseJson(text);
        if (!response.ok) {
          throw new ApiError(
            (typeof data.error === 'string' && data.error) ||
              response.statusText ||
              `Upload failed (${response.status})`,
            response.status,
            data.fields as Record<string, string> | undefined,
            {
              remoteAuthRequired:
                Boolean(data.remoteAuthRequired) ||
                response.headers.get('X-Remote-Auth-Required') === '1',
              remoteUnreachable: Boolean(data.remoteUnreachable),
              targetId: typeof data.targetId === 'string' ? data.targetId : undefined,
            }
          );
        }
        return data as unknown as VideoUploadResponse;
      },
      deleteFile: (file: string) =>
        request<{ deleted: string; files: VideoFilesResponse['files'] }>(
          `/api/effects/video/file?file=${encodeURIComponent(file)}`,
          { method: 'DELETE' }
        ),
      previewUrl: (file: string) =>
        `/api/effects/video/file?file=${encodeURIComponent(file)}&_target=${encodeURIComponent(activeTargetHeaderId)}`,
    },
  },

  playback: {
    status: () => request<PlaybackStatus>('/api/playback/status'),
    start: (payload?: {
      index?: number;
      effect?: string;
      config?: Record<string, unknown>;
    }) =>
      request<PlaybackStatus>('/api/playback/start', {
        method: 'POST',
        body: JSON.stringify(payload ?? {}),
      }),
    stop: () =>
      request<PlaybackStatus>('/api/playback/stop', {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    next: () =>
      request<PlaybackStatus>('/api/playback/next', {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    jump: (index: number) =>
      request<PlaybackStatus>('/api/playback/jump', {
        method: 'POST',
        body: JSON.stringify({ index }),
      }),
    playEffect: (effect: string, config?: Record<string, unknown>) =>
      request<PlaybackStatus>('/api/playback/play', {
        method: 'POST',
        body: JSON.stringify({ effect, config: config ?? {} }),
      }),
    fetchFrame: async (signal?: AbortSignal): Promise<LiveFrameData | null> => {
      const response = await fetch('/api/playback/frame', {
        credentials: 'include',
        cache: 'no-store',
        headers: {
          'X-Matrix-Target': activeTargetHeaderId,
        },
        signal,
      });
      if (response.status === 204) return null;
      if (!response.ok) {
        const text = await response.text();
        const data = parseResponseJson(text);
        throw new ApiError(
          (typeof data.error === 'string' && data.error) ||
            response.statusText ||
            `Frame fetch failed (${response.status})`,
          response.status,
          undefined,
          {
            remoteAuthRequired:
              Boolean(data.remoteAuthRequired) ||
              response.headers.get('X-Remote-Auth-Required') === '1',
            remoteUnreachable: Boolean(data.remoteUnreachable),
            targetId: typeof data.targetId === 'string' ? data.targetId : undefined,
          }
        );
      }
      const width = parseInt(response.headers.get('X-Matrix-Width') || '0', 10);
      const height = parseInt(response.headers.get('X-Matrix-Height') || '0', 10);
      const timestamp = parseFloat(response.headers.get('X-Frame-Timestamp') || '0');
      const buf = await response.arrayBuffer();
      if (
        width <= 0 ||
        height <= 0 ||
        width > 1024 ||
        height > 1024 ||
        buf.byteLength !== width * height * 3
      ) {
        return null;
      }
      return {
        width,
        height,
        rgbBytes: new Uint8Array(buf),
        timestamp,
      };
    },
  },

  targets: {
    list: () => request<TargetsState>('/api/targets'),
    add: (name: string, url: string) =>
      request<TargetsState & { target: MatrixTarget }>('/api/targets', {
        method: 'POST',
        body: JSON.stringify({ name, url }),
      }),
    remove: (id: string) =>
      request<TargetsState>(`/api/targets/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      }),
    testUrl: (url: string) =>
      request<TargetProbeResult>('/api/targets/test', {
        method: 'POST',
        body: JSON.stringify({ url }),
      }),
    testSaved: (id: string) =>
      request<TargetProbeResult & { targetsState?: TargetsState }>(
        `/api/targets/${encodeURIComponent(id)}/test`,
        {
          method: 'POST',
          body: JSON.stringify({}),
        }
      ),
    setActive: (targetId: string) =>
      request<TargetsState>('/api/targets/active', {
        method: 'POST',
        body: JSON.stringify({ targetId }),
      }),
    login: (id: string, password: string, setup = false) =>
      request<{
        authenticated: boolean;
        target: MatrixTarget;
        targetsState: TargetsState;
      }>(`/api/targets/${encodeURIComponent(id)}/login`, {
        method: 'POST',
        body: JSON.stringify({ password, setup }),
      }),
    logout: (id: string) =>
      request<{
        authenticated: boolean;
        target: MatrixTarget;
        targetsState: TargetsState;
      }>(`/api/targets/${encodeURIComponent(id)}/logout`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
  },

  system: {
    gitStatus: (fetch = false) =>
      request<GitStatusResponse>(`/api/system/git-status${fetch ? '?fetch=1' : ''}`),
    gitPull: () =>
      request<GitPullResponse>('/api/system/git-pull', {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    restart: () =>
      request<{ restarting: boolean }>('/api/system/restart', {
        method: 'POST',
        body: JSON.stringify({}),
      }),
  },
};
