import {
  Braces,
  LayoutDashboard,
  ListMusic,
  Monitor,
  Shield,
  SlidersHorizontal,
  type LucideIcon,
} from 'lucide-react';
import type { NavSectionId } from '@/types/matrix';

export interface NavItem {
  id: NavSectionId;
  label: string;
  description: string;
  icon: LucideIcon;
  group: 'workspace' | 'system';
}

/**
 * Declarative navigation registry.
 * Add new feature pages (e.g. Live Controls, Media Library, Schedules) right here.
 */
export const NAV_ITEMS: NavItem[] = [
  {
    id: 'overview',
    label: 'Overview',
    description: 'Matrix status & quick summary',
    icon: LayoutDashboard,
    group: 'workspace',
  },
  {
    id: 'playlist',
    label: 'Playlist',
    description: 'Curate & configure effects',
    icon: ListMusic,
    group: 'workspace',
  },
  {
    id: 'display',
    label: 'Display & Hardware',
    description: 'Size, GPIO pins, color & brightness',
    icon: SlidersHorizontal,
    group: 'workspace',
  },
  {
    id: 'virtual',
    label: 'Virtual Simulator',
    description: 'Desktop / monitor preview options',
    icon: Monitor,
    group: 'workspace',
  },
  {
    id: 'json',
    label: 'Raw JSON',
    description: 'Inspect, export & reset config',
    icon: Braces,
    group: 'system',
  },
  {
    id: 'security',
    label: 'Security',
    description: 'Password & session settings',
    icon: Shield,
    group: 'system',
  },
];
