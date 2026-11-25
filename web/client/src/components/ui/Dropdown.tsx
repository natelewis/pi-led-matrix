import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown } from 'lucide-react';

export interface DropdownProps {
  id?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  disabled?: boolean;
  hasError?: boolean;
  ariaLabel?: string;
  trigger: ReactNode;
  triggerClassName?: string;
  panelClassName?: string;
  /** Minimum pixel width for the floating panel (defaults to trigger width). */
  minPanelWidth?: number;
  children: ReactNode;
}

/**
 * Shared custom dark dropdown primitive used by Select, FontPicker, and other
 * popover pickers so every dropdown across Studio shares identical styling,
 * focus rings, chevron animation, viewport-aware positioning, and keyboard/outside-click behavior.
 */
export function Dropdown({
  id,
  open,
  onOpenChange,
  disabled = false,
  hasError = false,
  ariaLabel,
  trigger,
  triggerClassName = '',
  panelClassName = '',
  minPanelWidth,
  children,
}: DropdownProps) {
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [coords, setCoords] = useState<{
    top: number;
    left: number;
    width: number;
    maxHeight: number;
    placeAbove: boolean;
  } | null>(null);

  const updatePosition = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const viewportW = window.innerWidth;
    const viewportH = window.innerHeight;
    const margin = 12;
    const desiredWidth = Math.min(
      viewportW - margin * 2,
      Math.max(rect.width, minPanelWidth ?? rect.width)
    );
    const spaceBelow = viewportH - rect.bottom - margin;
    const spaceAbove = rect.top - margin;
    const placeAbove = spaceBelow < 200 && spaceAbove > spaceBelow;
    const maxHeight = Math.max(140, Math.min(340, (placeAbove ? spaceAbove : spaceBelow) - 8));

    let left = rect.left;
    if (left + desiredWidth > viewportW - margin) {
      left = Math.max(margin, viewportW - margin - desiredWidth);
    }

    setCoords({
      top: placeAbove ? rect.top - 6 : rect.bottom + 6,
      left,
      width: desiredWidth,
      maxHeight,
      placeAbove,
    });
  }, [minPanelWidth]);

  useLayoutEffect(() => {
    if (!open) {
      setCoords(null);
      return;
    }
    updatePosition();
  }, [open, updatePosition]);

  useEffect(() => {
    if (!open) return;

    const onMouseDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        triggerRef.current?.contains(target) ||
        panelRef.current?.contains(target)
      ) {
        return;
      }
      onOpenChange(false);
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onOpenChange(false);
        triggerRef.current?.focus();
      }
    };

    const onScrollOrResize = () => updatePosition();

    window.addEventListener('mousedown', onMouseDown);
    window.addEventListener('keydown', onKeyDown, true);
    window.addEventListener('resize', onScrollOrResize);
    window.addEventListener('scroll', onScrollOrResize, true);
    return () => {
      window.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('keydown', onKeyDown, true);
      window.removeEventListener('resize', onScrollOrResize);
      window.removeEventListener('scroll', onScrollOrResize, true);
    };
  }, [open, onOpenChange, updatePosition]);

  return (
    <>
      <button
        ref={triggerRef}
        id={id}
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => onOpenChange(!open)}
        className={`flex w-full items-center justify-between gap-2.5 rounded-xl border bg-surface-950/90 px-3 py-2 text-left text-sm text-slate-100 transition-colors cursor-pointer focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-50 ${
          hasError
            ? 'border-rose-500/70 focus:border-rose-400 focus:ring-rose-500/25'
            : open
              ? 'border-cyan-400 ring-2 ring-cyan-400/20'
              : 'border-slate-700/90 hover:border-cyan-500/50 focus:border-cyan-400 focus:ring-cyan-400/20'
        } ${triggerClassName}`}
      >
        <div className="min-w-0 flex-1">{trigger}</div>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-slate-400 transition-transform duration-150 ${
            open ? 'rotate-180 text-cyan-300' : ''
          }`}
        />
      </button>

      {open &&
        coords &&
        createPortal(
          <div
            ref={panelRef}
            style={{
              position: 'fixed',
              left: coords.left,
              top: coords.top,
              width: coords.width,
              maxHeight: coords.maxHeight,
              transform: coords.placeAbove ? 'translateY(-100%)' : undefined,
            }}
            className={`z-[70] flex flex-col overflow-hidden rounded-xl border border-slate-700/90 bg-surface-950/98 shadow-2xl shadow-black/70 backdrop-blur-sm ${panelClassName}`}
          >
            {children}
          </div>,
          document.body
        )}
    </>
  );
}
