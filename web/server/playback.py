"""Local playlist process controller & IPC bridge for LED Matrix Studio."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


RUNTIME_DIRNAME = "_runtime"
STATE_FILENAME = "state.json"
COMMAND_FILENAME = "command.json"
LOG_FILENAME = "playlist.log"
HEARTBEAT_STALE_SECONDS = 8.0


def _pid_alive(pid: int, updated_at: float) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # e.g. `sudo make playlist` running as root on Raspberry Pi
        return (time.time() - updated_at) < HEARTBEAT_STALE_SECONDS
    except OSError:
        return False


class PlaybackController:
    """Starts/stops the local playlist runner and sends real-time skip/jump/reload commands."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.runtime_dir = self.repo_root / RUNTIME_DIRNAME
        self.state_path = self.runtime_dir / STATE_FILENAME
        self.command_path = self.runtime_dir / COMMAND_FILENAME
        self.log_path = self.runtime_dir / LOG_FILENAME
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen[bytes]] = None
        self._log_handle: Optional[Any] = None

    def _atomic_write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def _read_state_file(self) -> Optional[Dict[str, Any]]:
        if not self.state_path.is_file():
            return None
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _send_command(self, action: str, **extra: Any) -> Dict[str, Any]:
        cmd = {
            "id": uuid.uuid4().hex,
            "action": action,
            "createdAt": time.time(),
            **extra,
        }
        self._atomic_write_json(self.command_path, cmd)
        return cmd

    def _resolve_python_executable(self) -> str:
        venv_python = self.repo_root / ".venv" / "bin" / "python"
        if venv_python.is_file() and os.access(venv_python, os.X_OK):
            return str(venv_python)
        return sys.executable

    def _cleanup_finished_proc(self) -> None:
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

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            self._cleanup_finished_proc()
            managed_running = self._proc is not None and self._proc.poll() is None
            managed_pid = self._proc.pid if managed_running and self._proc else None

        state = self._read_state_file()
        running = False
        pid = managed_pid
        managed = managed_running

        if state and state.get("status") in ("playing", "idle"):
            state_pid = int(state.get("pid") or 0)
            updated_at = float(state.get("updatedAt") or 0.0)
            if _pid_alive(state_pid, updated_at):
                running = True
                pid = state_pid
                managed = managed_running and (managed_pid == state_pid)
        elif managed_running:
            # Process just launched and hasn't written its first state.json yet
            running = True

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

        started_at = state.get("startedAt") if state else None
        elapsed = (
            max(0.0, round(time.time() - float(started_at), 1))
            if isinstance(started_at, (int, float))
            else 0.0
        )

        return {
            "running": True,
            "managed": managed,
            "pid": pid,
            "status": (state.get("status") if state else None) or "starting",
            "mode": (state.get("mode") if state else None) or "playlist",
            "currentIndex": state.get("currentIndex") if state else None,
            "currentEffect": state.get("currentEffect") if state else None,
            "currentConfig": state.get("currentConfig") if state else None,
            "playlistLength": state.get("playlistLength") if state else None,
            "playlistDelay": state.get("playlistDelay") if state else None,
            "startedAt": started_at,
            "elapsedSeconds": elapsed,
            "virtual": state.get("virtual") if state else None,
        }

    def start(
        self,
        *,
        index: Optional[int] = None,
        effect: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        status = self.get_status()
        if status["running"]:
            if effect:
                self._send_command("play_effect", effect=effect, config=config or {})
            elif index is not None:
                self._send_command("jump", index=index)
            return self.get_status()

        script_path = self.repo_root / "src" / "load_playlist.py"
        if not script_path.is_file():
            raise RuntimeError("src/load_playlist.py not found in repository.")

        # Pre-seed an initial jump/play command if requested before spawning
        if effect:
            self._send_command("play_effect", effect=effect, config=config or {})
        elif index is not None:
            self._send_command("jump", index=index)

        python_bin = self._resolve_python_executable()
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        with self._lock:
            self._cleanup_finished_proc()
            self._log_handle = self.log_path.open("wb")
            env = dict(os.environ)
            env.setdefault("PYTHONUNBUFFERED", "1")
            self._proc = subprocess.Popen(
                [python_bin, str(script_path)],
                cwd=str(self.repo_root),
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
                env=env,
            )

        # Give it a brief moment to detect immediate startup failures (e.g. missing venv deps)
        time.sleep(0.25)
        with self._lock:
            if self._proc is not None and self._proc.poll() is not None:
                code = self._proc.returncode
                self._cleanup_finished_proc()
                last_line = self._read_last_log_line()
                raise RuntimeError(
                    f"Playlist runner exited immediately (code {code})"
                    + (f": {last_line}" if last_line else ".")
                )

        return self.get_status()

    def stop(self) -> Dict[str, Any]:
        self._send_command("stop")

        with self._lock:
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
            with self._lock:
                self._cleanup_finished_proc()
        else:
            # Allow external `make playlist` process a brief moment to see the stop command
            time.sleep(0.2)

        return self.get_status()

    def skip_next(self) -> Dict[str, Any]:
        if not self.get_status()["running"]:
            return self.start()
        self._send_command("next")
        return self.get_status()

    def jump_to(self, index: int) -> Dict[str, Any]:
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("index must be a non-negative integer.")
        if not self.get_status()["running"]:
            return self.start(index=index)
        self._send_command("jump", index=index)
        return self.get_status()

    def play_effect(
        self, effect: str, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not isinstance(effect, str) or not effect.strip():
            raise ValueError("effect name is required.")
        cfg = config if isinstance(config, dict) else {}
        if not self.get_status()["running"]:
            return self.start(effect=effect.strip(), config=cfg)
        self._send_command("play_effect", effect=effect.strip(), config=cfg)
        return self.get_status()

    def notify_config_updated(self) -> None:
        """Let any live runner know config.json changed (it also polls mtime)."""
        if self.get_status()["running"]:
            self._send_command("reload")

    def shutdown(self) -> None:
        with self._lock:
            proc = self._proc
        if proc is not None and proc.poll() is None:
            self.stop()
