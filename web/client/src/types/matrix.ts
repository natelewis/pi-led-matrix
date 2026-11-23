export type GpioPin = 'D10' | 'D12' | 'D18' | 'D21';
export type ColorOrder = 'rgb' | 'rbg' | 'grb' | 'gbr' | 'brg' | 'bgr';

export interface MarqueeMessage {
  left: number;
  right: number;
  r: number;
  g: number;
  b: number;
  message: string;
  font: string;
}

export interface PlaylistItem {
  effect: string;
  config?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface MatrixConfig {
  pixel_width: number;
  pixel_height: number;
  brightness: number;
  contrast: number;
  color: number;
  virtual: boolean;
  virtual_fullscreen: boolean;
  virtual_led_dots: boolean;
  virtual_framerate: number;
  playlist_delay: number;
  color_order: ColorOrder;
  alternating: boolean;
  pixel_pins: GpioPin[];
  playlist: PlaylistItem[];
  [key: string]: unknown;
}

export interface ConfigSchemaMetadata {
  validPins: GpioPin[];
  validColorOrders: ColorOrder[];
}

export interface ConfigResponse {
  config: MatrixConfig;
  source: 'custom' | 'default';
  configPath: string;
  defaultConfigPath: string;
  updatedAt: string | null;
  schema: ConfigSchemaMetadata;
}

export type EffectCategory = 'animation' | 'game' | 'media' | 'text' | 'utility';
export type EffectConfigSchema = 'none' | 'marquee' | 'image' | 'video';

export interface EffectMeta {
  id: string;
  label: string;
  description: string;
  category: EffectCategory;
  configSchema: EffectConfigSchema;
  isUtility: boolean;
  availableFiles?: string[];
}

export interface EffectsResponse {
  effects: EffectMeta[];
  fonts: string[];
}

export interface UploadedImageMeta {
  file: string;
  name: string;
  uploaded: boolean;
  sizeBytes: number;
  width: number | null;
  height: number | null;
}

export interface ImageFilesResponse {
  files: UploadedImageMeta[];
}

export interface ImageUploadResponse {
  image: UploadedImageMeta;
  files: UploadedImageMeta[];
}

export interface UploadedVideoMeta {
  file: string;
  name: string;
  uploaded: boolean;
  sizeBytes: number;
  width: number | null;
  height: number | null;
  duration: number | null;
}

export interface VideoFilesResponse {
  files: UploadedVideoMeta[];
}

export interface VideoUploadResponse {
  video: UploadedVideoMeta;
  files: UploadedVideoMeta[];
}

export interface PlaybackStatus {
  running: boolean;
  managed: boolean;
  pid: number | null;
  status: 'playing' | 'idle' | 'starting' | 'stopped';
  mode: 'playlist' | 'single' | 'idle' | 'stopped';
  currentIndex: number | null;
  currentEffect: string | null;
  currentConfig: Record<string, unknown> | null;
  playlistLength: number | null;
  playlistDelay: number | null;
  startedAt: number | null;
  elapsedSeconds: number;
  virtual: boolean | null;
}

export interface AuthStatus {
  initialized: boolean;
  authenticated: boolean;
  envManaged: boolean;
  expiresAt?: number | null;
}

export type NavSectionId =
  | 'overview'
  | 'playlist'
  | 'display'
  | 'virtual'
  | 'json'
  | 'security';
