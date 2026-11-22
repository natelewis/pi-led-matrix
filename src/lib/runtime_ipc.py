"""Lightweight file-based IPC between LED Matrix Studio and the local playlist runner.

Files live inside `<repo_root>/_runtime/`, which is automatically gitignored via `_*`.
"""

import json
import os
import time
import uuid
from pathlib import Path


RUNTIME_DIRNAME = "_runtime"
STATE_FILENAME = "state.json"
COMMAND_FILENAME = "command.json"


def get_runtime_dir(repo_root=None):
    base = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
    return base / RUNTIME_DIRNAME


def _atomic_write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


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
