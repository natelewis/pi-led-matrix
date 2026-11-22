import type {
  AuthStatus,
  ConfigResponse,
  EffectsResponse,
  ImageFilesResponse,
  ImageUploadResponse,
  MatrixConfig,
  PlaybackStatus,
  VideoFilesResponse,
  VideoUploadResponse,
} from '@/types/matrix';

export class ApiError extends Error {
  status: number;
  fields?: Record<string, string>;

  constructor(message: string, status: number, fields?: Record<string, string>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fields = fields;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: 'include',
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    throw new ApiError(
      data.error || `Request failed (${response.status})`,
      response.status,
      data.fields
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
        `/api/effects/image/file?file=${encodeURIComponent(file)}`,
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
          },
          body: file,
        });
        const text = await response.text();
        const data = text ? JSON.parse(text) : {};
        if (!response.ok) {
          throw new ApiError(
            data.error || `Upload failed (${response.status})`,
            response.status,
            data.fields
          );
        }
        return data as VideoUploadResponse;
      },
      deleteFile: (file: string) =>
        request<{ deleted: string; files: VideoFilesResponse['files'] }>(
          `/api/effects/video/file?file=${encodeURIComponent(file)}`,
          { method: 'DELETE' }
        ),
      previewUrl: (file: string) =>
        `/api/effects/video/file?file=${encodeURIComponent(file)}`,
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
  },
};
