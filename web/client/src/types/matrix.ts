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
export type EffectConfigSchema = 'none' | 'fields' | 'marquee' | 'image' | 'video';
export type EffectConfigFieldType =
  | 'select'
  | 'number'
  | 'boolean'
  | 'text'
  | 'textarea'
  | 'color'
  | 'font'
  | 'alignment'
  | 'list';

export interface EffectConfigFieldOption {
  value: string;
  label: string;
}

export interface EffectConfigFieldShowWhen {
  key: string;
  equals?: unknown;
  notEquals?: unknown;
  in?: unknown[];
  gt?: number;
  truthy?: boolean;
}

export interface EffectConfigTokenOption {
  token: string;
  label: string;
}

export type EffectFieldValue =
  | string
  | number
  | boolean
  | Record<string, unknown>[];

export interface EffectConfigField {
  key: string;
  label: string;
  type: EffectConfigFieldType;
  description?: string;
  section?: string;
  showWhen?: EffectConfigFieldShowWhen;
  required?: boolean;
  default?: EffectFieldValue;
  options?: EffectConfigFieldOption[];
  min?: number;
  max?: number;
  step?: number;
  integer?: boolean;
  allowAuto?: boolean;
  unit?: string;
  placeholder?: string;
  tokens?: EffectConfigTokenOption[];
  previewTextKey?: string;
  mode?: 'horizontal' | 'grid';
  itemFields?: EffectConfigField[];
  itemLabel?: string;
  addLabel?: string;
  minItems?: number;
  maxItems?: number;
  reorderable?: boolean;
}

export interface EffectConfigPreset {
  id: string;
  label: string;
  description?: string;
  config: Record<string, unknown>;
}

export interface FontMeta {
  id: string;
  file: string;
  name: string;
  category: string;
  description: string;
  minHeight: number;
  recommendedMinSize: number;
  crispDefault: boolean;
  variation?: string | null;
  cssWeight?: number;
  builtin: boolean;
  uploaded: boolean;
  license?: string;
  sizeBytes: number;
}

export interface EffectPreviewDiagnosticAction {
  label: string;
  patch: Record<string, unknown>;
}

export interface EffectPreviewDiagnostic {
  level: 'ok' | 'info' | 'warn';
  message: string;
  actions?: EffectPreviewDiagnosticAction[];
}

export interface EffectPreviewResponse {
  effect: string;
  width: number;
  height: number;
  fps: number;
  frameCount: number;
  framesBase64: string;
  diagnostics: EffectPreviewDiagnostic[];
  summary?: Record<string, unknown>;
}

export interface EffectMeta {
  id: string;
  label: string;
  description: string;
  category: EffectCategory;
  configSchema: EffectConfigSchema;
  requiresConfig?: boolean;
  configFields?: EffectConfigField[];
  configPresets?: EffectConfigPreset[];
  hasPreview?: boolean;
  isUtility: boolean;
  availableFiles?: string[];
}

export interface EffectsResponse {
  effects: EffectMeta[];
  fonts: string[];
  fontCatalog?: FontMeta[];
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
  | 'devices'
  | 'json'
  | 'security';

export interface MatrixTarget {
  id: string;
  name: string;
  url: string | null;
  isLocal: boolean;
  hasSession: boolean;
  createdAt: number | null;
}

export interface TargetsState {
  activeTargetId: string;
  targets: MatrixTarget[];
}

export interface TargetProbeResult {
  reachable: boolean;
  url: string;
  initialized?: boolean;
  authenticated?: boolean;
  envManaged?: boolean;
  error?: string;
}

export interface LiveFrameData {
  width: number;
  height: number;
  rgbBytes: Uint8Array;
  timestamp: number;
}

export interface GitStatusResponse {
  isGitRepo: boolean;
  branch: string | null;
  detached: boolean;
  commit: string | null;
  commitMessage: string | null;
  commitDate: string | null;
  remoteUrl: string | null;
  upstream: string | null;
  dirty: boolean;
  dirtyFiles: string[];
  ahead: number | null;
  behind: number | null;
  fetchError: string | null;
  canRestart?: boolean;
}

export interface GitRebuildStep {
  name: string;
  status: 'ok' | 'skipped' | 'failed';
  detail: string;
}

export interface GitPullResponse {
  updated: boolean;
  beforeCommit: string;
  afterCommit: string;
  changedFiles: string[];
  totalChangedFiles: number;
  serverFilesChanged: boolean;
  clientFilesChanged: boolean;
  playbackFilesChanged: boolean;
  pythonDepsChanged?: boolean;
  nodeDepsChanged?: boolean;
  rebuildSteps?: GitRebuildStep[];
  rebuilt?: boolean;
  rebuildFailed?: boolean;
  output: string;
  status: GitStatusResponse;
  canRestart?: boolean;
}
