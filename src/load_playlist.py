import importlib
import inspect
import multiprocessing
import os
import random
import re
import signal
import time
from pathlib import Path

import main
from lib import runtime_ipc


EFFECT_NAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


def import_effect(name):
    if not isinstance(name, str) or not EFFECT_NAME_RE.match(name):
        raise ValueError(f"Invalid effect name: {name!r}")

    src_dir = Path(inspect.getfile(inspect.currentframe())).resolve().parent
    effects_root = (src_dir / "effects").resolve()
    effect_path = (effects_root / name).resolve()
    try:
        effect_path.relative_to(effects_root)
    except ValueError as exc:
        raise ValueError(f"Invalid effect path: {name!r}") from exc

    if not (effect_path / "effect.py").is_file():
        raise FileNotFoundError(f"Unknown effect: {name}")

    return importlib.import_module("effects." + name + ".effect"), str(effect_path)


def build_effects(playlist_entries):
    loaded = []
    for e_data in playlist_entries:
        name = e_data["effect"]
        effect_module, e_dir = import_effect(name)
        loaded.append(
            {
                "name": name,
                "module": effect_module,
                "dir": e_dir,
                "color_order": main.color_order,
                "effect": e_data.get("config", {}) or {},
            }
        )
    return loaded


def build_single_effect(name, effect_config=None):
    effect_module, e_dir = import_effect(name)
    return {
        "name": name,
        "module": effect_module,
        "dir": e_dir,
        "color_order": main.color_order,
        "effect": effect_config if isinstance(effect_config, dict) else {},
    }


def _run_effect_obj(effect_obj, matrix=None):
    print("Starting " + effect_obj["name"], flush=True)
    if matrix is None:
        matrix = main.Matrix()
    else:
        matrix.reset_timer()
        matrix.reset()
    effect_obj["module"].run(
        matrix,
        {
            "pixel_height": main.pixel_height,
            "pixel_width": main.pixel_width,
            "effect_dir": effect_obj["dir"],
            "color_order": main.color_order,
            "effect": effect_obj["effect"],
        },
    )


def _run_live_effect_process(name, effect_config):
    """Spawned child entry point for LiveMatrix mode (reads fresh config.json on spawn)."""
    effect_obj = build_single_effect(name, effect_config)
    _run_effect_obj(effect_obj, matrix=None)


def _pick_next_index(length, current_index):
    if length <= 0:
        return None
    if length == 1:
        return 0
    candidates = [i for i in range(length) if i != current_index]
    return random.choice(candidates)


def main_loop():
    print("Starting playlist: CTRL-c to stop", flush=True)

    stop_requested = False

    def _handle_sigterm(_signum, _frame):
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, _handle_sigterm)

    effects = build_effects(main.playlist)
    last_config_mtime = runtime_ipc.get_active_config_mtime()

    # Track last handled IPC command ID; accept a very recent command (e.g. start-at-index)
    initial_cmd = runtime_ipc.read_command()
    last_cmd_id = None
    pending_cmd = None
    if initial_cmd and (time.time() - float(initial_cmd.get("createdAt", 0))) < 5.0:
        if initial_cmd.get("action") in ("jump", "play_effect"):
            pending_cmd = initial_cmd
        last_cmd_id = initial_cmd.get("id")
    elif initial_cmd:
        last_cmd_id = initial_cmd.get("id")

    current_index = None
    current_effect_name = None
    current_effect_config = {}
    current_mode = "playlist"
    effect_started_at = time.time()
    last_heartbeat = 0.0

    def publish_state(status="playing", mode=None):
        nonlocal last_heartbeat, current_mode
        if mode is not None:
            current_mode = mode
        last_heartbeat = time.time()
        runtime_ipc.write_state(
            {
                "pid": os.getpid(),
                "status": status,
                "mode": current_mode,
                "currentIndex": current_index,
                "currentEffect": current_effect_name,
                "currentConfig": current_effect_config,
                "playlistLength": len(effects),
                "playlistDelay": main.playlist_delay,
                "startedAt": effect_started_at,
                "configMtime": last_config_mtime,
                "virtual": main.VIRTUAL_ENV,
            }
        )

    def _apply_hot_reload(shared_matrix=None):
        """Reload config.json live; return True only if the current effect must restart."""
        nonlocal effects, last_config_mtime, pending_cmd
        last_config_mtime = runtime_ipc.get_active_config_mtime()
        try:
            info = main.reload_config()
            effects = build_effects(main.playlist)
            if shared_matrix is not None:
                shared_matrix.apply_runtime_config(dims_changed=info["dims_changed"])
            publish_state("playing")

            if info["dims_changed"]:
                # Restart current entry at new geometry if possible
                if current_index is not None and 0 <= current_index < len(effects):
                    pending_cmd = {"action": "jump", "index": current_index}
                return True

            if current_mode == "playlist" and current_index is not None:
                if current_index >= len(effects):
                    return True
                updated_entry = effects[current_index]
                if (
                    updated_entry["name"] != current_effect_name
                    or updated_entry["effect"] != current_effect_config
                ):
                    pending_cmd = {"action": "jump", "index": current_index}
                    return True
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"Warning: failed to hot-reload config.json: {exc}", flush=True)
        return False

    def poll_control(shared_matrix=None):
        """Return True if the currently running effect should yield immediately."""
        nonlocal stop_requested, pending_cmd, last_cmd_id

        if stop_requested:
            return True

        # Keep heartbeat fresh while a long effect is playing
        if time.time() - last_heartbeat >= 2.0 and current_effect_name is not None:
            publish_state("playing")

        # 1. Check incoming Studio IPC commands
        cmd = runtime_ipc.read_command()
        if cmd and cmd.get("id") and cmd.get("id") != last_cmd_id:
            last_cmd_id = cmd["id"]
            action = cmd.get("action")
            if action == "stop":
                stop_requested = True
                return True
            if action == "reload":
                return _apply_hot_reload(shared_matrix)
            if action in ("next", "jump", "play_effect"):
                pending_cmd = cmd
                return True

        # 2. Check live config.json edits for seamless hot-reload
        current_mtime = runtime_ipc.get_active_config_mtime()
        if current_mtime != last_config_mtime:
            return _apply_hot_reload(shared_matrix)

        return False

    def choose_next_effect():
        nonlocal pending_cmd, current_index, current_effect_name, current_effect_config

        cmd = pending_cmd
        pending_cmd = None

        if cmd:
            action = cmd.get("action")
            if action == "play_effect":
                fx_name = cmd.get("effect")
                fx_cfg = cmd.get("config") or {}
                if isinstance(fx_name, str) and fx_name:
                    current_index = None
                    current_effect_name = fx_name
                    current_effect_config = fx_cfg if isinstance(fx_cfg, dict) else {}
                    return build_single_effect(fx_name, current_effect_config), "single"
            elif action == "jump":
                target_idx = cmd.get("index")
                if (
                    not isinstance(target_idx, bool)
                    and isinstance(target_idx, int)
                    and 0 <= target_idx < len(effects)
                ):
                    current_index = target_idx
                    chosen = effects[target_idx]
                    current_effect_name = chosen["name"]
                    current_effect_config = chosen["effect"]
                    return chosen, "playlist"

        if not effects:
            current_index = None
            current_effect_name = None
            current_effect_config = {}
            return None, "idle"

        next_idx = _pick_next_index(len(effects), current_index)
        current_index = next_idx
        chosen = effects[next_idx]
        current_effect_name = chosen["name"]
        current_effect_config = chosen["effect"]
        return chosen, "playlist"

    shared_matrix = None
    if main.VIRTUAL_ENV:
        shared_matrix = main.Matrix()
        shared_matrix.set_interrupt_check(lambda: poll_control(shared_matrix))
        try:
            while not stop_requested:
                try:
                    effect_obj, mode = choose_next_effect()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    print(f"Error selecting next effect: {exc}", flush=True)
                    time.sleep(0.5)
                    continue

                if effect_obj is None:
                    publish_state("idle", "idle")
                    time.sleep(0.25)
                    poll_control(shared_matrix)
                    continue
                effect_started_at = time.time()
                publish_state("playing", mode)
                try:
                    _run_effect_obj(effect_obj, shared_matrix)
                except SystemExit as exc:
                    if exc.code in (None, 0):
                        stop_requested = True
                        break
                    print(
                        f"Effect {effect_obj['name']} exited with error code {exc.code}",
                        flush=True,
                    )
                    time.sleep(0.5)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    print(
                        f"Error running effect {effect_obj['name']}: {exc}",
                        flush=True,
                    )
                    time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            runtime_ipc.clear_frame_snapshot()
            publish_state("stopped", "stopped")
            shared_matrix.close()
    else:
        multiprocessing.set_start_method("spawn", force=True)
        active_proc = None
        try:
            while not stop_requested:
                try:
                    effect_obj, mode = choose_next_effect()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    print(f"Error selecting next effect: {exc}", flush=True)
                    time.sleep(0.5)
                    continue

                if effect_obj is None:
                    publish_state("idle", "idle")
                    time.sleep(0.25)
                    poll_control()
                    continue
                effect_started_at = time.time()
                publish_state("playing", mode)
                active_proc = multiprocessing.Process(
                    target=_run_live_effect_process,
                    name="run_effect",
                    args=(effect_obj["name"], effect_obj["effect"]),
                )
                active_proc.start()
                while active_proc.is_alive():
                    active_proc.join(timeout=0.1)
                    if poll_control():
                        active_proc.terminate()
                        active_proc.join(timeout=1.5)
                        if active_proc.is_alive():
                            active_proc.kill()
                            active_proc.join(timeout=1.0)
                        break
                active_proc = None
        except KeyboardInterrupt:
            pass
        finally:
            if active_proc is not None and active_proc.is_alive():
                active_proc.terminate()
                active_proc.join(timeout=1.5)
                if active_proc.is_alive():
                    active_proc.kill()
                    active_proc.join(timeout=1.0)
            runtime_ipc.clear_frame_snapshot()
            publish_state("stopped", "stopped")


if __name__ == "__main__":
    main_loop()
