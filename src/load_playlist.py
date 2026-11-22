import importlib
import inspect
import multiprocessing
import os
import random
import signal
import sys
import time

import main
from lib import runtime_ipc


def import_effect(name):
    effect_dir = os.path.realpath(
        os.path.abspath(
            os.path.join(
                os.path.split(inspect.getfile(inspect.currentframe()))[0],
                "effects/" + name,
            )
        )
    )
    return importlib.import_module("effects." + name + ".effect"), effect_dir


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
    effect_started_at = time.time()
    last_heartbeat = 0.0

    def publish_state(status="playing", mode="playlist"):
        nonlocal last_heartbeat
        last_heartbeat = time.time()
        runtime_ipc.write_state(
            {
                "pid": os.getpid(),
                "status": status,
                "mode": mode,
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

    def poll_control(shared_matrix=None):
        """Return True if the currently running effect should yield immediately."""
        nonlocal stop_requested, pending_cmd, last_cmd_id, last_config_mtime, effects

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
            if action in ("next", "jump", "play_effect", "reload"):
                pending_cmd = cmd
                return True

        # 2. Check live config.json edits for seamless hot-reload
        current_mtime = runtime_ipc.get_active_config_mtime()
        if current_mtime != last_config_mtime:
            last_config_mtime = current_mtime
            try:
                prev_playlist = list(main.playlist)
                info = main.reload_config()
                effects = build_effects(main.playlist)
                if shared_matrix is not None:
                    shared_matrix.apply_runtime_config(dims_changed=info["dims_changed"])
                publish_state("playing")
                # Interrupt immediately if geometry changed or current entry disappeared
                if info["dims_changed"]:
                    return True
                if current_index is not None and (
                    current_index >= len(effects)
                    or (
                        prev_playlist != main.playlist
                        and effects[current_index]["name"] != current_effect_name
                    )
                ):
                    return True
            except Exception as exc:
                print(f"Warning: failed to hot-reload config.json: {exc}", flush=True)

        return False

    def choose_next_effect():
        nonlocal pending_cmd, current_index, current_effect_name, current_effect_config
        nonlocal effects, last_config_mtime

        cmd = pending_cmd
        pending_cmd = None

        if cmd:
            action = cmd.get("action")
            if action == "reload":
                try:
                    info = main.reload_config()
                    last_config_mtime = runtime_ipc.get_active_config_mtime()
                    effects = build_effects(main.playlist)
                    if shared_matrix is not None:
                        shared_matrix.apply_runtime_config(dims_changed=info["dims_changed"])
                except Exception as exc:
                    print(f"Warning: reload failed: {exc}", flush=True)
            elif action == "play_effect":
                fx_name = cmd.get("effect")
                fx_cfg = cmd.get("config") or {}
                if isinstance(fx_name, str) and fx_name:
                    current_index = None
                    current_effect_name = fx_name
                    current_effect_config = fx_cfg if isinstance(fx_cfg, dict) else {}
                    return build_single_effect(fx_name, current_effect_config), "single"
            elif action == "jump":
                target_idx = cmd.get("index")
                if isinstance(target_idx, int) and 0 <= target_idx < len(effects):
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
                effect_obj, mode = choose_next_effect()
                if effect_obj is None:
                    publish_state("idle", "idle")
                    time.sleep(0.25)
                    poll_control(shared_matrix)
                    continue
                effect_started_at = time.time()
                publish_state("playing", mode)
                try:
                    _run_effect_obj(effect_obj, shared_matrix)
                except SystemExit:
                    stop_requested = True
                    break
                except Exception as exc:
                    print(f"Error running effect {effect_obj['name']}: {exc}", flush=True)
                    time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            publish_state("stopped", "stopped")
            shared_matrix.close()
    else:
        multiprocessing.set_start_method("spawn", force=True)
        try:
            while not stop_requested:
                effect_obj, mode = choose_next_effect()
                if effect_obj is None:
                    publish_state("idle", "idle")
                    time.sleep(0.25)
                    poll_control()
                    continue
                effect_started_at = time.time()
                publish_state("playing", mode)
                proc = multiprocessing.Process(
                    target=_run_live_effect_process,
                    name="run_effect",
                    args=(effect_obj["name"], effect_obj["effect"]),
                )
                proc.start()
                while proc.is_alive():
                    proc.join(timeout=0.1)
                    if poll_control():
                        proc.terminate()
                        proc.join(timeout=1.5)
                        if proc.is_alive():
                            proc.kill()
                        break
        except KeyboardInterrupt:
            pass
        finally:
            publish_state("stopped", "stopped")


if __name__ == "__main__":
    main_loop()
