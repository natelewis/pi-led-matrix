"""Local playlist process controller & IPC bridge for LED Matrix Studio."""

from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .config_store import is_safe_relative_media_path
from .effects import discover_effects


RUNTIME_DIRNAME = "_runtime"
STATE_FILENAME = "state.json"
COMMAND_FILENAME = "command.json"
FRAME_FILENAME = "frame.bin"
MIRROR_LEASE_FILENAME = "mirror.lease"
LOG_FILENAME = "playlist.log"
HEARTBEAT_STALE_SECONDS = 12.0
FRAME_STALE_SECONDS = 6.0
MAX_MIRROR_DIMENSION = 1024
MAX_MIRROR_BYTES = 4 + MAX_MIRROR_DIMENSION * MAX_MIRROR_DIMENSION * 3


def _resolve_mirror_dir(repo_root: Path) -> Path:
    shm = Path("/dev/shm")
    if shm.is_dir() and os.access(shm, os.W_OK | os.X_OK):
        digest = hashlib.sha256(str(repo_root.resolve()).encode("utf-8")).hexdigest()[:12]
        return shm / f"pi-led-matrix-{digest}"
    return repo_root / RUNTIME_DIRNAME


def _pid_alive(pid: int, updated_at: float) -> bool:
    if pid <= 0:
        return False
    # Reject stale state even if the OS recycled the PID or left a zombie
    if updated_at > 0 and (time.time() - updated_at) > HEARTBEAT_STALE_SECONDS:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # e.g. `sudo make playlist` running as root on Raspberry Pi
        return updated_at > 0 and (time.time() - updated_at) < HEARTBEAT_STALE_SECONDS
    except OSError:
        return False


class PlaybackController:
    """Thread-safe controller for the local playlist runner and _runtime IPC."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.runtime_dir = self.repo_root / RUNTIME_DIRNAME
        self.state_path = self.runtime_dir / STATE_FILENAME
        self.command_path = self.runtime_dir / COMMAND_FILENAME
        self.mirror_dir = _resolve_mirror_dir(self.repo_root)
        self.frame_path = self.mirror_dir / FRAME_FILENAME
        self.mirror_lease_path = self.mirror_dir / MIRROR_LEASE_FILENAME
        self.log_path = self.runtime_dir / LOG_FILENAME
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen[bytes]] = None
        self._log_handle: Optional[Any] = None

    def _atomic_write_json_locked(self, path: Path, payload: Dict[str, Any]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
            )
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
        except PermissionError as exc:
            raise RuntimeError(
                "Permission denied writing to _runtime/. If `make playlist` was started "
                "with sudo, ensure _runtime/ is writable by the web server user."
            ) from exc

    def _read_state_file(self) -> Optional[Dict[str, Any]]:
        if not self.state_path.is_file():
            return None
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _send_command_locked(self, action: str, **extra: Any) -> Dict[str, Any]:
        cmd = {
            "id": uuid.uuid4().hex,
            "action": action,
            "createdAt": time.time(),
            **extra,
        }
        self._atomic_write_json_locked(self.command_path, cmd)
        return cmd

    def _send_command(self, action: str, **extra: Any) -> Dict[str, Any]:
        with self._lock:
            return self._send_command_locked(action, **extra)

    def _validate_effect_request(
        self, effect: Any, config: Any
    ) -> tuple[str, Dict[str, Any]]:
        if not isinstance(effect, str) or not effect.strip():
            raise ValueError("effect name is required.")
        effect_name = effect.strip()
        known = {e["id"] for e in discover_effects(self.repo_root)}
        if effect_name not in known:
            raise ValueError(f"Unknown effect '{effect_name}'.")
        if config is None:
            cfg: Dict[str, Any] = {}
        elif isinstance(config, dict):
            cfg = dict(config)
        else:
            raise ValueError("config must be a JSON object.")
        if effect_name in ("image", "video") and "file" in cfg:
            if not is_safe_relative_media_path(cfg["file"]):
                raise ValueError("Media file path must be a relative path without '..'.")
        return effect_name, cfg

    def _validate_index(self, index: Any) -> int:
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("index must be a non-negative integer.")
        return index

    def _resolve_python_executable(self) -> str:
        venv_python = self.repo_root / ".venv" / "bin" / "python"
        if venv_python.is_file() and os.access(venv_python, os.X_OK):
            return str(venv_python)
        return sys.executable

    def _cleanup_finished_proc_locked(self) -> None:
        if self._proc is not None and self._proc.poll() is not None:
            self._proc = None
            if self._log_handle is not None:
                try:
                    self._log_handle.close()
                except OSError:
                    pass
                self._log_handle = None

    def _read_last_log_line(self) -> Optional[str]:
        if not self.log_path.is_file():
            return None
        try:
            lines = [
                ln.strip()
                for ln in self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                if ln.strip()
            ]
            return lines[-1] if lines else None
        except OSError:
            return None

    def _get_status_locked(self) -> Dict[str, Any]:
        self._cleanup_finished_proc_locked()
        managed_running = self._proc is not None and self._proc.poll() is None
        managed_pid = self._proc.pid if managed_running and self._proc else None

        state = self._read_state_file()
        state_active = False
        pid = managed_pid
        managed = managed_running

        if state and state.get("status") in ("playing", "idle"):
            state_pid = int(state.get("pid") or 0)
            updated_at = float(state.get("updatedAt") or 0.0)
            if _pid_alive(state_pid, updated_at):
                state_active = True
                pid = state_pid
                managed = managed_running and (managed_pid == state_pid)

        running = state_active or managed_running

        if not running:
            return {
                "running": False,
                "managed": False,
                "pid": None,
                "status": "stopped",
                "mode": "stopped",
                "currentIndex": None,
                "currentEffect": None,
                "currentConfig": None,
                "playlistLength": state.get("playlistLength") if state else None,
                "playlistDelay": state.get("playlistDelay") if state else None,
                "startedAt": None,
                "elapsedSeconds": 0,
                "virtual": state.get("virtual") if state else None,
            }

        # Managed process just spawned and hasn't published its first live state yet
        if not state_active or state is None:
            return {
                "running": True,
                "managed": True,
                "pid": managed_pid,
                "status": "starting",
                "mode": "playlist",
                "currentIndex": None,
                "currentEffect": None,
                "currentConfig": None,
                "playlistLength": None,
                "playlistDelay": None,
                "startedAt": None,
                "elapsedSeconds": 0,
                "virtual": None,
            }

        started_at = state.get("startedAt")
        elapsed = (
            max(0.0, round(time.time() - float(started_at), 1))
            if isinstance(started_at, (int, float))
            else 0.0
        )

        return {
            "running": True,
            "managed": managed,
            "pid": pid,
            "status": state.get("status") or "playing",
            "mode": state.get("mode") or "playlist",
            "currentIndex": state.get("currentIndex"),
            "currentEffect": state.get("currentEffect"),
            "currentConfig": state.get("currentConfig"),
            "playlistLength": state.get("playlistLength"),
            "playlistDelay": state.get("playlistDelay"),
            "startedAt": started_at,
            "elapsedSeconds": elapsed,
            "virtual": state.get("virtual"),
        }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return self._get_status_locked()

    def start(
        self,
        *,
        index: Optional[int] = None,
        effect: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        validated_effect: Optional[str] = None
        validated_config: Dict[str, Any] = {}
        validated_index: Optional[int] = None

        if effect is not None:
            validated_effect, validated_config = self._validate_effect_request(effect, config)
        elif index is not None:
            validated_index = self._validate_index(index)

        with self._lock:
            status = self._get_status_locked()
            if status["running"]:
                if validated_effect is not None:
                    self._send_command_locked(
                        "play_effect", effect=validated_effect, config=validated_config
                    )
                elif validated_index is not None:
                    self._send_command_locked("jump", index=validated_index)
                return self._get_status_locked()

            script_path = self.repo_root / "src" / "load_playlist.py"
            if not script_path.is_file():
                raise RuntimeError("src/load_playlist.py not found in repository.")

            if validated_effect is not None:
                self._send_command_locked(
                    "play_effect", effect=validated_effect, config=validated_config
                )
            elif validated_index is not None:
                self._send_command_locked("jump", index=validated_index)

            python_bin = self._resolve_python_executable()
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
            self._cleanup_finished_proc_locked()
            self._log_handle = self.log_path.open("wb")
            env = dict(os.environ)
            env.setdefault("PYTHONUNBUFFERED", "1")
            proc = subprocess.Popen(
                [python_bin, str(script_path)],
                cwd=str(self.repo_root),
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
                env=env,
            )
            self._proc = proc

        # Briefly verify it didn't immediately crash on import/startup
        time.sleep(0.25)
        with self._lock:
            if self._proc is proc and proc.poll() is not None:
                code = proc.returncode
                self._cleanup_finished_proc_locked()
                last_line = self._read_last_log_line()
                raise RuntimeError(
                    f"Playlist runner exited immediately (code {code})"
                    + (f": {last_line}" if last_line else ".")
                )
            return self._get_status_locked()

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            self._send_command_locked("stop")
            proc = self._proc

        if proc is not None and proc.poll() is None:
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    try:
                        proc.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        pass
            with self._lock:
                self._cleanup_finished_proc_locked()
        else:
            time.sleep(0.2)

        return self.get_status()

    def skip_next(self) -> Dict[str, Any]:
        with self._lock:
            if self._get_status_locked()["running"]:
                self._send_command_locked("next")
                return self._get_status_locked()
        return self.start()

    def jump_to(self, index: int) -> Dict[str, Any]:
        validated_index = self._validate_index(index)
        with self._lock:
            if self._get_status_locked()["running"]:
                self._send_command_locked("jump", index=validated_index)
                return self._get_status_locked()
        return self.start(index=validated_index)

    def play_effect(
        self, effect: str, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        validated_effect, validated_config = self._validate_effect_request(effect, config)
        with self._lock:
            if self._get_status_locked()["running"]:
                self._send_command_locked(
                    "play_effect", effect=validated_effect, config=validated_config
                )
                return self._get_status_locked()
        return self.start(effect=validated_effect, config=validated_config)

    def notify_config_updated(self) -> None:
        """Notify any live runner of config.json changes (non-destructive reload)."""
        with self._lock:
            if self._get_status_locked()["running"]:
                try:
                    self._send_command_locked("reload")
                except RuntimeError:
                    pass

    def _touch_mirror_lease(self) -> None:
        try:
            self.mirror_dir.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(str(self.mirror_lease_path), flags, 0o664)
            os.close(fd)
            os.utime(self.mirror_lease_path, None)
        except OSError:
            pass

    def read_frame_snapshot(self) -> Optional[Tuple[int, int, bytes, float]]:
        """Touch the live-mirror lease and return (width, height, rgb_bytes, mtime) if fresh."""
        self._touch_mirror_lease()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(str(self.frame_path), flags)
        except OSError:
            return None
        try:
            stat = os.fstat(fd)
            if (time.time() - stat.st_mtime) > FRAME_STALE_SECONDS:
                return None
            if stat.st_size < 4 or stat.st_size > MAX_MIRROR_BYTES:
                return None
            with os.fdopen(fd, "rb") as handle:
                fd = -1
                raw = handle.read(MAX_MIRROR_BYTES + 1)
        except OSError:
            return None
        finally:
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass

        if len(raw) < 4 or len(raw) > MAX_MIRROR_BYTES:
            return None
        width, height = struct.unpack(">HH", raw[:4])
        if not (1 <= width <= MAX_MIRROR_DIMENSION and 1 <= height <= MAX_MIRROR_DIMENSION):
            return None
        rgb = raw[4:]
        if len(rgb) != width * height * 3:
            return None
        return width, height, rgb, stat.st_mtime

    def close_log_handle(self) -> None:
        """Close the open playlist log file handle without terminating a running playlist."""
        with self._lock:
            if self._log_handle is not None:
                try:
                    self._log_handle.close()
                except OSError:
                    pass
                self._log_handle = None

    def shutdown(self) -> None:
        with self._lock:
            proc = self._proc
        if proc is not None and proc.poll() is None:
            self.stop()
        self.close_log_handle()
