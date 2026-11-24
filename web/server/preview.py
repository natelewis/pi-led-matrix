"""Generic live effect preview dispatcher for Studio's EffectConfigModal.

Any built-in effect under ``src/effects/`` that exports
``preview(config, pixel_width, pixel_height)`` can render pixel-exact LED frames
and screen-aware diagnostics directly into the UI.
"""

from __future__ import annotations

import base64
import importlib
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

EFFECT_NAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")

_PREVIEW_LOCK = threading.Lock()
_LOADED_MTIMES: Dict[str, int] = {}


def _ensure_src_on_path(repo_root: Path) -> None:
    for candidate in (repo_root / "src", Path(__file__).resolve().parents[2] / "src"):
        resolved = str(candidate.resolve())
        if candidate.is_dir() and resolved not in sys.path:
            sys.path.insert(0, resolved)


def _load_builtin_effect_module(repo_root: Path, effect_id: str) -> Any:
    """Safely load a built-in effect module from ``src/effects/`` (reloading if edited)."""
    if not isinstance(effect_id, str) or not EFFECT_NAME_RE.match(effect_id):
        raise ValueError(f"Invalid effect name: {effect_id!r}")

    _ensure_src_on_path(repo_root)
    src_dir = (repo_root / "src").resolve()

    builtin_root = (src_dir / "effects").resolve()
    builtin_dir = (builtin_root / effect_id).resolve()
    try:
        builtin_dir.relative_to(builtin_root)
    except ValueError as exc:
        raise ValueError("Invalid effect path.") from exc

    effect_file = builtin_dir / "effect.py"
    if not effect_file.is_file():
        # Never execute non-built-in effects in-process inside the web server
        custom_file = (src_dir / "custom_effects" / effect_id / "effect.py").resolve()
        if custom_file.is_file():
            raise NotImplementedError(
                f"In-process live preview is disabled for custom effect '{effect_id}'."
            )
        raise FileNotFoundError(f"Unknown effect '{effect_id}'.")

    mod_name = f"effects.{effect_id}.effect"
    mtime = int(effect_file.stat().st_mtime_ns)
    mod = sys.modules.get(mod_name)
    if mod is None:
        mod = importlib.import_module(mod_name)
        _LOADED_MTIMES[mod_name] = mtime
    elif _LOADED_MTIMES.get(mod_name) != mtime:
        mod = importlib.reload(mod)
        _LOADED_MTIMES[mod_name] = mtime
    return mod


def render_effect_preview(
    repo_root: Path,
    effect_id: str,
    effect_config: Optional[Dict[str, Any]],
    width: int,
    height: int,
) -> Dict[str, Any]:
    """Invoke a built-in effect's ``preview(config, width, height)`` hook and serialize frames."""
    try:
        import numpy as np  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise RuntimeError(
            "Live preview requires numpy and Pillow (run the server inside .venv)."
        ) from exc

    safe_w = max(8, min(256, int(width)))
    safe_h = max(8, min(256, int(height)))

    with _PREVIEW_LOCK:
        module = _load_builtin_effect_module(repo_root, effect_id)
        preview_fn = getattr(module, "preview", None)
        if not callable(preview_fn):
            raise NotImplementedError(
                f"Effect '{effect_id}' does not provide a live preview() hook."
            )

        cfg = effect_config if isinstance(effect_config, dict) else {}
        result = preview_fn(cfg, safe_w, safe_h)

    if not isinstance(result, dict):
        raise RuntimeError("Effect preview() must return a dictionary.")

    raw_frames = result.get("frames")
    if not isinstance(raw_frames, list) or len(raw_frames) == 0:
        raise RuntimeError("Effect preview() returned no frames.")

    res_w = max(1, int(result.get("width", safe_w)))
    res_h = max(1, int(result.get("height", safe_h)))
    fps = float(result.get("fps", 16.0))
    if not np.isfinite(fps) or fps <= 0:
        fps = 16.0

    chunks: List[bytes] = []
    for frame in raw_frames[:160]:
        arr = np.asarray(frame, dtype=np.uint8)
        if arr.shape != (res_h, res_w, 3):
            raise RuntimeError(
                f"Preview frame shape mismatch: expected {(res_h, res_w, 3)}, got {arr.shape}"
            )
        chunks.append(np.ascontiguousarray(arr).tobytes())

    packed = b"".join(chunks)
    diagnostics = result.get("diagnostics")
    if not isinstance(diagnostics, list):
        diagnostics = []

    return {
        "effect": effect_id,
        "width": res_w,
        "height": res_h,
        "fps": round(fps, 2),
        "frameCount": len(chunks),
        "framesBase64": base64.b64encode(packed).decode("ascii"),
        "diagnostics": diagnostics,
        "summary": result.get("summary") if isinstance(result.get("summary"), dict) else {},
    }
