import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api, ApiError } from '@/api/client';
import type {
  ConfigSchemaMetadata,
  EffectMeta,
  MatrixConfig,
} from '@/types/matrix';

interface UseMatrixConfigOptions {
  enabled: boolean;
  targetKey?: string;
  onUnauthorized?: (err: unknown) => boolean;
}

export function useMatrixConfig({
  enabled,
  targetKey = 'local',
  onUnauthorized,
}: UseMatrixConfigOptions) {
  const [savedConfig, setSavedConfig] = useState<MatrixConfig | null>(null);
  const [draft, setDraft] = useState<MatrixConfig | null>(null);
  const [source, setSource] = useState<'custom' | 'default'>('default');
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [configPath, setConfigPath] = useState<string>('');
  const [schema, setSchema] = useState<ConfigSchemaMetadata>({
    validPins: ['D10', 'D12', 'D18', 'D21'],
    validColorOrders: ['rgb', 'rbg', 'grb', 'gbr', 'brg', 'bgr'],
  });
  const [effects, setEffects] = useState<EffectMeta[]>([]);
  const [fonts, setFonts] = useState<string[]>([]);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const loadSeqRef = useRef(0);

  const loadAll = useCallback(async () => {
    if (!enabled) return;
    const seq = ++loadSeqRef.current;
    setLoading(true);
    setLoadError(null);
    try {
      const [cfgRes, fxRes] = await Promise.all([
        api.config.get(),
        api.effects.list(),
      ]);
      if (seq !== loadSeqRef.current) return;
      setSavedConfig(cfgRes.config);
      setDraft(structuredClone(cfgRes.config));
      setSource(cfgRes.source);
      setUpdatedAt(cfgRes.updatedAt);
      setConfigPath(cfgRes.configPath);
      setSchema(cfgRes.schema);
      setEffects(fxRes.effects);
      setFonts(fxRes.fonts);
      setFieldErrors({});
    } catch (err) {
      if (seq !== loadSeqRef.current) return;
      if (onUnauthorized?.(err)) return;
      setLoadError(err instanceof Error ? err.message : 'Failed to load configuration');
    } finally {
      if (seq === loadSeqRef.current) {
        setLoading(false);
      }
    }
  }, [enabled, onUnauthorized]);

  useEffect(() => {
    loadSeqRef.current += 1;
    if (enabled) {
      void loadAll();
    } else {
      setSavedConfig(null);
      setDraft(null);
      setLoadError(null);
      setLoading(false);
    }
  }, [enabled, targetKey, loadAll]);

  const isDirty = useMemo(() => {
    if (!savedConfig || !draft) return false;
    return JSON.stringify(savedConfig) !== JSON.stringify(draft);
  }, [savedConfig, draft]);

  const updateDraft = useCallback(
    (updater: (prev: MatrixConfig) => MatrixConfig) => {
      setDraft((prev) => (prev ? updater(prev) : prev));
    },
    []
  );

  const patchField = useCallback(
    <K extends keyof MatrixConfig>(key: K, value: MatrixConfig[K]) => {
      setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
      setFieldErrors((prev) => {
        if (!(String(key) in prev)) return prev;
        const copy = { ...prev };
        delete copy[String(key)];
        return copy;
      });
    },
    []
  );

  const discard = useCallback(() => {
    if (!savedConfig) return;
    setDraft(structuredClone(savedConfig));
    setFieldErrors({});
  }, [savedConfig]);

  const save = useCallback(async (overrideConfig?: MatrixConfig) => {
    const payload = overrideConfig ?? draft;
    if (!payload) return false;
    setSaving(true);
    setFieldErrors({});
    try {
      const res = await api.config.save(payload);
      setSavedConfig(res.config);
      setDraft(structuredClone(res.config));
      setSource(res.source);
      setUpdatedAt(res.updatedAt);
      setConfigPath(res.configPath);
      return true;
    } catch (err) {
      if (onUnauthorized?.(err)) return false;
      if (err instanceof ApiError && err.fields) {
        setFieldErrors(err.fields);
      }
      throw err;
    } finally {
      setSaving(false);
    }
  }, [draft, onUnauthorized]);

  const resetToDefaults = useCallback(async () => {
    setSaving(true);
    setFieldErrors({});
    try {
      const res = await api.config.reset();
      setSavedConfig(res.config);
      setDraft(structuredClone(res.config));
      setSource(res.source);
      setUpdatedAt(res.updatedAt);
      setConfigPath(res.configPath);
      return true;
    } catch (err) {
      if (onUnauthorized?.(err)) return false;
      throw err;
    } finally {
      setSaving(false);
    }
  }, [onUnauthorized]);

  const reloadEffects = useCallback(async () => {
    if (!enabled) return;
    try {
      const fxRes = await api.effects.list();
      setEffects(fxRes.effects);
      setFonts(fxRes.fonts);
    } catch (err) {
      onUnauthorized?.(err);
    }
  }, [enabled, onUnauthorized]);

  const effectMap = useMemo(() => {
    return new Map(effects.map((e) => [e.id, e]));
  }, [effects]);

  return {
    savedConfig,
    draft,
    source,
    updatedAt,
    configPath,
    schema,
    effects,
    effectMap,
    fonts,
    loading,
    saving,
    loadError,
    fieldErrors,
    isDirty,
    reload: loadAll,
    reloadEffects,
    updateDraft,
    patchField,
    discard,
    save,
    resetToDefaults,
  };
}
