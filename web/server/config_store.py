"""Config storage, schema validation, and atomic writes for pi-led-matrix."""

from __future__ import annotations

import json
import math
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .effects import discover_effects


VALID_PINS = ("D10", "D12", "D18", "D21")
VALID_COLOR_ORDERS = ("rgb", "rbg", "grb", "gbr", "brg", "bgr")


def is_safe_relative_media_path(raw_file: Any) -> bool:
    if not isinstance(raw_file, str):
        return False
    cleaned = raw_file.strip()
    if not cleaned or cleaned.startswith("/") or "\\" in cleaned:
        return False
    return ".." not in Path(cleaned).parts


class ConfigValidationError(ValueError):
    """Raised when a submitted matrix configuration fails validation."""

    def __init__(self, errors: Dict[str, str]) -> None:
        super().__init__("Configuration validation failed")
        self.errors = errors


class ConfigStore:
    """Thread-safe reader/writer for config.json with fallback to default_config.json."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.config_path = repo_root / "config.json"
        self.default_config_path = repo_root / "default_config.json"
        self._lock = threading.Lock()

    def _read_json(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"{path.name} must contain a JSON object.")
        return data

    def load_default_config(self) -> Dict[str, Any]:
        return self._read_json(self.default_config_path)

    def load(self) -> Dict[str, Any]:
        """Return the active config along with metadata about its source."""
        with self._lock:
            if self.config_path.exists():
                config = self._read_json(self.config_path)
                source = "custom"
                stat = self.config_path.stat()
                updated_at = datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat()
            else:
                config = self.load_default_config()
                source = "default"
                updated_at = None

            defaults = self.load_default_config()
            merged = {**defaults, **config}

        return {
            "config": merged,
            "source": source,
            "configPath": str(self.config_path),
            "defaultConfigPath": str(self.default_config_path),
            "updatedAt": updated_at,
        }

    def validate(self, payload: Any) -> Dict[str, Any]:
        """Validate a config object and return a normalized copy."""
        if not isinstance(payload, dict):
            raise ConfigValidationError({"_root": "Configuration must be a JSON object."})

        errors: Dict[str, str] = {}
        normalized: Dict[str, Any] = dict(payload)

        def require_int(key: str, minimum: int, maximum: int) -> Optional[int]:
            val = payload.get(key)
            if isinstance(val, bool) or not isinstance(val, int):
                errors[key] = f"{key} must be an integer."
                return None
            if val < minimum or val > maximum:
                errors[key] = f"{key} must be between {minimum} and {maximum}."
                return None
            normalized[key] = val
            return val

        def require_number(key: str, minimum: float, maximum: float) -> Optional[float]:
            val = payload.get(key)
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                errors[key] = f"{key} must be a number."
                return None
            fval = float(val)
            if not math.isfinite(fval):
                errors[key] = f"{key} must be a finite number."
                return None
            if fval < minimum or fval > maximum:
                errors[key] = f"{key} must be between {minimum} and {maximum}."
                return None
            normalized[key] = round(fval, 4)
            return fval

        def require_bool(key: str) -> Optional[bool]:
            val = payload.get(key)
            if not isinstance(val, bool):
                errors[key] = f"{key} must be a boolean."
                return None
            normalized[key] = val
            return val

        width = require_int("pixel_width", 1, 1024)
        require_int("pixel_height", 1, 1024)
        require_number("brightness", 0.0, 1.0)
        require_number("contrast", 0.0, 10.0)
        require_number("color", 0.0, 10.0)
        require_bool("virtual")
        require_bool("virtual_fullscreen")
        require_bool("virtual_led_dots")
        require_int("virtual_framerate", 1, 5000)
        require_int("playlist_delay", 1, 86400)
        require_bool("alternating")

        color_order = payload.get("color_order")
        if not isinstance(color_order, str) or color_order.lower() not in VALID_COLOR_ORDERS:
            errors["color_order"] = (
                f"color_order must be one of: {', '.join(VALID_COLOR_ORDERS)}."
            )
        else:
            normalized["color_order"] = color_order.lower()

        pins = payload.get("pixel_pins")
        if not isinstance(pins, list) or len(pins) == 0:
            errors["pixel_pins"] = "Select at least one GPIO pixel pin."
        else:
            invalid_pins = [p for p in pins if not isinstance(p, str) or p not in VALID_PINS]
            if invalid_pins:
                errors["pixel_pins"] = (
                    f"Invalid GPIO pin(s): {', '.join(map(str, invalid_pins))}. "
                    f"Valid pins: {', '.join(VALID_PINS)}."
                )
            elif len(set(pins)) != len(pins):
                errors["pixel_pins"] = "Duplicate GPIO pins are not allowed."
            elif width is not None and width % len(pins) != 0:
                errors["pixel_pins"] = (
                    f"pixel_width ({width}) must be evenly divisible by the number of "
                    f"pixel_pins ({len(pins)})."
                )
            else:
                normalized["pixel_pins"] = list(pins)

        # Validate playlist entries
        known_effects = {e["id"] for e in discover_effects(self.repo_root)}
        playlist = payload.get("playlist")
        if not isinstance(playlist, list):
            errors["playlist"] = "playlist must be a list of effect entries."
        else:
            cleaned_playlist: List[Dict[str, Any]] = []
            for idx, item in enumerate(playlist):
                if not isinstance(item, dict):
                    errors[f"playlist.{idx}"] = "Each playlist entry must be an object."
                    continue
                effect_name = item.get("effect")
                if not isinstance(effect_name, str) or not effect_name.strip():
                    errors[f"playlist.{idx}"] = "Playlist entry is missing an effect name."
                    continue
                if known_effects and effect_name not in known_effects:
                    errors[f"playlist.{idx}"] = f"Unknown effect '{effect_name}'."
                    continue
                cleaned_item = dict(item)
                cleaned_item["effect"] = effect_name
                if "config" in cleaned_item:
                    if cleaned_item["config"] is None or cleaned_item["config"] == {}:
                        cleaned_item.pop("config", None)
                    elif not isinstance(cleaned_item["config"], dict):
                        errors[f"playlist.{idx}"] = "Effect config must be a JSON object."
                        continue
                    elif effect_name in ("image", "video") and "file" in cleaned_item["config"]:
                        if not is_safe_relative_media_path(cleaned_item["config"]["file"]):
                            errors[f"playlist.{idx}"] = (
                                "Media file path must be a relative path without '..'."
                            )
                            continue
                cleaned_playlist.append(cleaned_item)
            normalized["playlist"] = cleaned_playlist

        if errors:
            raise ConfigValidationError(errors)

        # Ensure entire object serializes as strict RFC 8259 JSON (no NaN/Infinity in nested keys)
        try:
            json.dumps(normalized, allow_nan=False)
        except ValueError as exc:
            raise ConfigValidationError(
                {"_root": f"Configuration contains invalid non-finite numbers: {exc}"}
            ) from exc

        return normalized

    def save(self, payload: Any) -> Dict[str, Any]:
        """Validate and atomically write config.json."""
        normalized = self.validate(payload)
        serialized = json.dumps(normalized, indent=4, allow_nan=False) + "\n"
        with self._lock:
            fd, tmp_name = tempfile.mkstemp(
                dir=str(self.config_path.parent),
                prefix=".config.json.",
                suffix=".tmp",
            )
            tmp_path = Path(tmp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(serialized)
                os.replace(tmp_path, self.config_path)
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise
        return self.load()

    def reset_to_defaults(self) -> Dict[str, Any]:
        """Reset config.json to default_config.json values."""
        defaults = self.load_default_config()
        return self.save(defaults)

    def get_schema_metadata(self) -> Dict[str, Any]:
        return {
            "validPins": list(VALID_PINS),
            "validColorOrders": list(VALID_COLOR_ORDERS),
        }
