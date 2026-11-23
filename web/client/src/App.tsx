import { useEffect, useState } from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import { LivePlaybackBar } from '@/components/config/LivePlaybackBar';
import { RemoteUnlockCard } from '@/components/config/RemoteUnlockCard';
import { AppShell } from '@/components/layout/AppShell';
import { NAV_ITEMS } from '@/components/layout/navItems';
import { Button, ErrorBoundary, ToastProvider, useToast } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { useMatrixConfig } from '@/hooks/useMatrixConfig';
import { usePlayback } from '@/hooks/usePlayback';
import { useTargets } from '@/hooks/useTargets';
import { AuthPage } from '@/pages/AuthPage';
import { DevicesPage } from '@/pages/DevicesPage';
import { DisplayPage } from '@/pages/DisplayPage';
import { OverviewPage } from '@/pages/OverviewPage';
import { PlaylistPage } from '@/pages/PlaylistPage';
import { RawJsonPage } from '@/pages/RawJsonPage';
import { SecurityPage } from '@/pages/SecurityPage';
import { VirtualPage } from '@/pages/VirtualPage';
import type { NavSectionId, PlaylistItem } from '@/types/matrix';

const VALID_SECTIONS = new Set<NavSectionId>(NAV_ITEMS.map((item) => item.id));

function readSectionFromHash(): NavSectionId {
  const hash = window.location.hash.replace('#', '') as NavSectionId;
  return VALID_SECTIONS.has(hash) ? hash : 'overview';
}

function MatrixStudioApp() {
  const { notify } = useToast();
  const auth = useAuth();
  const [section, setSection] = useState<NavSectionId>(readSectionFromHash);

  const localAuthenticated = Boolean(auth.status?.authenticated);

  const targets = useTargets({
    enabled: localAuthenticated,
    onLocalUnauthorized: auth.handleUnauthorized,
  });

  const remoteBlocked =
    targets.isRemote &&
    (targets.remoteAuthNeeded ||
      Boolean(targets.remoteUnreachableError) ||
      !targets.activeTarget.hasSession);

  const targetDataEnabled = localAuthenticated && targets.initialized && !remoteBlocked;

  const matrix = useMatrixConfig({
    enabled: targetDataEnabled,
    targetKey: targets.activeTargetId,
    onUnauthorized: targets.handleApiError,
  });

  const playback = usePlayback({
    enabled: targetDataEnabled,
    targetKey: targets.activeTargetId,
    onUnauthorized: targets.handleApiError,
  });

  useEffect(() => {
    const onHashChange = () => setSection(readSectionFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    if (!matrix.isDirty) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [matrix.isDirty]);

  const navigate = (next: NavSectionId) => {
    setSection(next);
    if (window.location.hash !== `#${next}`) {
      window.history.replaceState(null, '', `#${next}`);
    }
  };

  const handleSelectTarget = async (targetId: string) => {
    if (matrix.isDirty) {
      const ok = window.confirm(
        'You have unsaved configuration changes. Switch devices and discard them?'
      );
      if (!ok) return;
    }
    try {
      const next = await targets.selectTarget(targetId);
      const chosen = next.targets.find((t) => t.id === next.activeTargetId);
      if (chosen) {
        notify('info', `Switched to ${chosen.name}`);
      }
    } catch (err) {
      notify(
        'error',
        'Could not switch device',
        err instanceof Error ? err.message : undefined
      );
    }
  };

  const handlePlaybackAction = async (
    action: () => Promise<unknown>,
    errorTitle: string
  ) => {
    try {
      await action();
    } catch (err) {
      notify(
        'error',
        errorTitle,
        err instanceof Error ? err.message : 'Unable to reach playlist runner.'
      );
    }
  };

  const handlePlayPlaylistItem = async (index: number, item: PlaylistItem) => {
    await handlePlaybackAction(async () => {
      if (matrix.isDirty) {
        await playback.playEffect(item.effect, item.config);
      } else {
        await playback.jump(index);
      }
      notify('info', `Playing ${item.effect}`);
    }, 'Could not play effect');
  };

  const handleSave = async () => {
    try {
      const ok = await matrix.save();
      if (ok) {
        notify(
          'success',
          'Configuration saved',
          playback.status.running
            ? `Updated config.json on ${targets.activeTarget.name} and hot-reloaded live playlist.`
            : `Updated config.json on ${targets.activeTarget.name}.`
        );
      }
    } catch (err) {
      notify(
        'error',
        'Could not save configuration',
        err instanceof Error ? err.message : 'Check validation errors and try again.'
      );
    }
  };

  const handleReset = async () => {
    try {
      await matrix.resetToDefaults();
      notify('success', 'Reset to defaults', 'config.json restored from default_config.json.');
    } catch (err) {
      notify(
        'error',
        'Reset failed',
        err instanceof Error ? err.message : 'Unable to reset configuration.'
      );
    }
  };

  if (auth.loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-950 text-slate-400">
        <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (auth.error || !auth.status) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface-950 px-4 text-center">
        <p className="text-sm text-rose-300">
          {auth.error || 'Unable to connect to the LED Matrix web server.'}
        </p>
        <Button
          variant="secondary"
          onClick={() => void auth.refresh()}
          leftIcon={<RefreshCw className="h-4 w-4" />}
        >
          Retry
        </Button>
      </div>
    );
  }

  if (!auth.status.authenticated) {
    return (
      <AuthPage
        initialized={auth.status.initialized}
        onSetup={auth.setup}
        onLogin={auth.login}
      />
    );
  }

  const isLocalOnlySection = section === 'devices' || section === 'security';
  const showRemoteUnlock = remoteBlocked && !isLocalOnlySection;

  const dimensionsLabel = matrix.draft
    ? `${matrix.draft.pixel_width}×${matrix.draft.pixel_height}`
    : targets.isRemote
      ? 'Remote'
      : '—';

  return (
    <AppShell
      activeSection={section}
      onNavigate={navigate}
      targets={targets.targets}
      activeTarget={targets.activeTarget}
      switchingTarget={targets.switching}
      onSelectTarget={(id) => void handleSelectTarget(id)}
      source={matrix.source}
      playlistCount={matrix.draft?.playlist.length ?? 0}
      dimensionsLabel={dimensionsLabel}
      isDirty={Boolean(matrix.draft) && matrix.isDirty}
      saving={matrix.saving}
      onSave={() => void handleSave()}
      onDiscard={matrix.discard}
      onLogout={() => void auth.logout()}
      subHeader={
        targetDataEnabled ? (
          <LivePlaybackBar
            playback={playback.status}
            effectMap={matrix.effectMap}
            targetName={targets.activeTarget.name}
            isRemote={targets.isRemote}
            busy={playback.busy}
            onStart={() =>
              void handlePlaybackAction(() => playback.start(), 'Could not start playlist')
            }
            onStop={() =>
              void handlePlaybackAction(() => playback.stop(), 'Could not stop playlist')
            }
            onNext={() =>
              void handlePlaybackAction(() => playback.next(), 'Could not skip effect')
            }
          />
        ) : undefined
      }
    >
      {section === 'devices' ? (
        <DevicesPage
          targets={targets.targets}
          activeTarget={targets.activeTarget}
          activeTargetId={targets.activeTargetId}
          targetDataEnabled={targetDataEnabled}
          switching={targets.switching}
          onSyncTargetsState={targets.applyTargetsState}
          onSelectTarget={handleSelectTarget}
          onAddTarget={targets.addTarget}
          onRemoveTarget={targets.removeTarget}
          onLoginTarget={targets.loginTarget}
          onLogoutTarget={targets.logoutTarget}
          onPushLocalConfig={targets.pushLocalConfig}
          onApiError={targets.handleApiError}
          onRepoUpdated={() => {
            void matrix.reloadEffects();
            if (!matrix.isDirty) {
              void matrix.reload();
            }
          }}
        />
      ) : section === 'security' ? (
        <SecurityPage
          authStatus={auth.status}
          onChangePassword={auth.changePassword}
          onLogout={auth.logout}
        />
      ) : showRemoteUnlock ? (
        <RemoteUnlockCard
          key={targets.activeTarget.id}
          target={targets.activeTarget}
          unreachableError={targets.remoteUnreachableError}
          onLogin={async (password, setup) => {
            await targets.loginTarget(targets.activeTarget.id, password, setup);
            notify('success', `Connected to ${targets.activeTarget.name}`);
          }}
          onSwitchLocal={() => void handleSelectTarget('local')}
          onRetry={() => targets.clearRemoteErrors()}
        />
      ) : matrix.loading || !matrix.draft ? (
        <div className="flex min-h-[320px] flex-col items-center justify-center gap-3 text-slate-400">
          {matrix.loadError ? (
            <>
              <p className="text-sm text-rose-300">{matrix.loadError}</p>
              <Button variant="secondary" onClick={() => void matrix.reload()}>
                Retry
              </Button>
            </>
          ) : (
            <>
              <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
              <span className="text-xs">
                Loading configuration from {targets.activeTarget.name}...
              </span>
            </>
          )}
        </div>
      ) : (
        <>
          {section === 'overview' && (
            <OverviewPage
              config={matrix.draft}
              source={matrix.source}
              updatedAt={matrix.updatedAt}
              effects={matrix.effects}
              isPlaying={playback.status.running}
              targetId={targets.activeTargetId}
              targetName={targets.activeTarget.name}
              onApiError={targets.handleApiError}
              onNavigate={navigate}
            />
          )}

          {section === 'playlist' && (
            <PlaylistPage
              config={matrix.draft}
              effects={matrix.effects}
              effectMap={matrix.effectMap}
              fonts={matrix.fonts}
              fieldErrors={matrix.fieldErrors}
              playingIndex={
                playback.status.running && playback.status.mode === 'playlist'
                  ? playback.status.currentIndex
                  : null
              }
              playbackBusy={playback.busy}
              isDirty={matrix.isDirty}
              onPlayPlaylistItem={(idx, item) => void handlePlayPlaylistItem(idx, item)}
              onUpdateConfig={matrix.updateDraft}
              onEffectsChanged={() => void matrix.reloadEffects()}
            />
          )}

          {section === 'display' && (
            <DisplayPage
              config={matrix.draft}
              schema={matrix.schema}
              fieldErrors={matrix.fieldErrors}
              onPatchField={matrix.patchField}
            />
          )}

          {section === 'virtual' && (
            <VirtualPage
              config={matrix.draft}
              fieldErrors={matrix.fieldErrors}
              onPatchField={matrix.patchField}
            />
          )}

          {section === 'json' && (
            <RawJsonPage
              config={matrix.draft}
              configPath={matrix.configPath}
              saving={matrix.saving}
              onApplyDraft={(next) => matrix.updateDraft(() => next)}
              onResetToDefaults={handleReset}
            />
          )}
        </>
      )}
    </AppShell>
  );
}

export function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <MatrixStudioApp />
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;
