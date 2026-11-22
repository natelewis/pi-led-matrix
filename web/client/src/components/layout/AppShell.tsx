import { useState, type ReactNode } from 'react';
import {
  Grid3X3,
  LogOut,
  Menu,
  RotateCcw,
  Save,
  X,
} from 'lucide-react';
import { Badge, Button } from '@/components/ui';
import { NAV_ITEMS } from './navItems';
import type { NavSectionId } from '@/types/matrix';

export interface AppShellProps {
  activeSection: NavSectionId;
  onNavigate: (section: NavSectionId) => void;
  source: 'custom' | 'default';
  playlistCount: number;
  dimensionsLabel: string;
  isDirty: boolean;
  saving: boolean;
  onSave: () => void;
  onDiscard: () => void;
  onLogout: () => void;
  subHeader?: ReactNode;
  children: ReactNode;
}

export function AppShell({
  activeSection,
  onNavigate,
  source,
  playlistCount,
  dimensionsLabel,
  isDirty,
  saving,
  onSave,
  onDiscard,
  onLogout,
  subHeader,
  children,
}: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const workspaceItems = NAV_ITEMS.filter((item) => item.group === 'workspace');
  const systemItems = NAV_ITEMS.filter((item) => item.group === 'system');

  const handleSelect = (id: NavSectionId) => {
    onNavigate(id);
    setMobileOpen(false);
  };

  const renderNavGroup = (title: string, items: typeof NAV_ITEMS) => (
    <div className="space-y-1">
      <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </div>
      {items.map((item) => {
        const Icon = item.icon;
        const active = activeSection === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => handleSelect(item.id)}
            className={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-all cursor-pointer ${
              active
                ? 'bg-cyan-500/12 text-cyan-200 ring-1 ring-inset ring-cyan-500/30'
                : 'text-slate-400 hover:bg-surface-850 hover:text-slate-100'
            }`}
          >
            <Icon
              className={`h-4 w-4 shrink-0 transition-colors ${
                active ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-300'
              }`}
            />
            <span className="flex-1 truncate">{item.label}</span>
            {item.id === 'playlist' && (
              <span
                className={`rounded-md px-1.5 py-0.5 font-mono text-[11px] ${
                  active
                    ? 'bg-cyan-500/20 text-cyan-200'
                    : 'bg-surface-800 text-slate-400'
                }`}
              >
                {playlistCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );

  const sidebarContent = (
    <div className="flex h-full flex-col">
      {/* Brand header */}
      <div className="flex items-center gap-3 border-b border-slate-800/80 px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400/20 to-emerald-400/20 text-cyan-300 ring-1 ring-cyan-400/30">
          <Grid3X3 className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold tracking-tight text-white">
            LED Matrix Studio
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <span className="font-mono">{dimensionsLabel}</span>
            <span>·</span>
            <span>{source === 'custom' ? 'config.json' : 'defaults'}</span>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {renderNavGroup('Configuration', workspaceItems)}
        {renderNavGroup('System', systemItems)}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-800/80 p-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={onLogout}
          leftIcon={<LogOut className="h-3.5 w-3.5" />}
          className="w-full justify-start text-slate-400 hover:text-rose-300"
        >
          Sign out
        </Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-surface-950 text-slate-100">
      {/* Desktop Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-800/80 bg-surface-900/95 lg:block">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-xs lg:hidden"
          onClick={() => setMobileOpen(false)}
        >
          <aside
            className="relative h-full w-72 border-r border-slate-800 bg-surface-900 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation"
              className="absolute right-3 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-surface-800 hover:text-white cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Main Content */}
      <div className="flex min-h-screen flex-col lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-4 border-b border-slate-800/80 bg-surface-950/85 px-4 backdrop-blur-md sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
              className="rounded-lg p-1.5 text-slate-300 hover:bg-surface-800 lg:hidden cursor-pointer"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2">
              <Badge tone={source === 'custom' ? 'emerald' : 'amber'}>
                {source === 'custom' ? 'Custom config.json' : 'Default config'}
              </Badge>
              {isDirty && (
                <Badge tone="cyan" className="animate-pulse">
                  Unsaved changes
                </Badge>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isDirty && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onDiscard}
                disabled={saving}
                leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
              >
                <span className="hidden sm:inline">Discard</span>
              </Button>
            )}
            <Button
              variant="primary"
              size="sm"
              onClick={onSave}
              disabled={!isDirty}
              loading={saving}
              leftIcon={<Save className="h-3.5 w-3.5" />}
            >
              Save Config
            </Button>
          </div>
        </header>

        {subHeader}

        {/* Page body */}
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
