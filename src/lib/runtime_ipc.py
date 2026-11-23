"""Lightweight file-based IPC between LED Matrix Studio and the local playlist runner.

Files live inside `<repo_root>/_runtime/`, which is automatically gitignored via `_*`.
On Linux (Raspberry Pi), live mirror frame snapshots use `/dev/shm` when available to
avoid microSD wear and only write when an active Studio viewer has polled recently.
"""

import hashlib
import json
import os
import struct
import tempfile
import time
import uuid
from pathlib import Path


RUNTIME_DIRNAME = "_runtime"
STATE_FILENAME = "state.json"
COMMAND_FILENAME = "command.json"
FRAME_FILENAME = "frame.bin"
MIRROR_LEASE_FILENAME = "mirror.lease"
MIRROR_LEASE_TTL_SECONDS = 5.0


def get_runtime_dir(repo_root=None):
    base = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
    return base / RUNTIME_DIRNAME


def get_mirror_dir(repo_root=None):
    """Prefer RAM-backed /dev/shm on Linux to avoid microSD wear during live mirroring."""
    shm = Path("/dev/shm")
    if shm.is_dir() and os.access(shm, os.W_OK | os.X_OK):
        # Deterministic cross-process hash of repo path so runner & web server agree
        base = str(Path(repo_root).resolve() if repo_root else Path.cwd().resolve())
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]
        return shm / f"pi-led-matrix-{digest}"
    return get_runtime_dir(repo_root)


def get_frame_path(repo_root=None):
    return get_mirror_dir(repo_root) / FRAME_FILENAME


def get_mirror_lease_path(repo_root=None):
    return get_mirror_dir(repo_root) / MIRROR_LEASE_FILENAME


def _atomic_write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, allow_nan=False)
            handle.write("\n")
        try:
            os.chmod(tmp_path, 0o664)
        except OSError:
            pass
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _read_json(path):
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def write_state(state, repo_root=None):
    payload = dict(state)
    payload["updatedAt"] = time.time()
    _atomic_write_json(get_runtime_dir(repo_root) / STATE_FILENAME, payload)


def read_state(repo_root=None):
    return _read_json(get_runtime_dir(repo_root) / STATE_FILENAME)


def write_command(action, repo_root=None, **extra):
    cmd = {
        "id": uuid.uuid4().hex,
        "action": action,
        "createdAt": time.time(),
        **extra,
    }
    _atomic_write_json(get_runtime_dir(repo_root) / COMMAND_FILENAME, cmd)
    return cmd


def read_command(repo_root=None):
    return _read_json(get_runtime_dir(repo_root) / COMMAND_FILENAME)


def get_active_config_mtime(repo_root=None):
    base = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
    cfg = base / "config.json"
    if cfg.is_file():
        return cfg.stat().st_mtime
    default_cfg = base / "default_config.json"
    if default_cfg.is_file():
        return default_cfg.stat().st_mtime
    return 0.0


def is_mirror_active(repo_root=None):
    """Return True only when a Studio viewer has polled the live mirror recently."""
    lease_path = get_mirror_lease_path(repo_root)
    try:
        return (time.time() - lease_path.stat().st_mtime) <= MIRROR_LEASE_TTL_SECONDS
    except OSError:
        return False


def write_frame_snapshot(frame_rgb, repo_root=None):
    """Atomically write an RGB numpy array (H, W, 3) when a live mirror viewer is active."""
    try:
        if not is_mirror_active(repo_root):
            return
        height, width, channels = frame_rgb.shape
        if channels != 3 or width <= 0 or height <= 0:
            return
        payload = struct.pack(">HH", int(width), int(height)) + frame_rgb.astype(
            "uint8", copy=False
        ).tobytes()
        path = get_frame_path(repo_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Use a deterministic per-PID temp file so SIGTERM never accumulates random orphans
        tmp_path = path.with_name(f".frame.{os.getpid()}.tmp")
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(str(tmp_path), flags, 0o664)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
            os.replace(tmp_path, path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
    except Exception:
        # Never let live-mirror snapshotting interrupt LED rendering
        pass


def clear_frame_snapshot(repo_root=None):
    try:
        mirror_dir = get_mirror_dir(repo_root)
        (mirror_dir / FRAME_FILENAME).unlink(missing_ok=True)
        if mirror_dir.is_dir():
            for leftover in mirror_dir.glob(".frame.*.tmp"):
                leftover.unlink(missing_ok=True)
    except OSError:
        pass
