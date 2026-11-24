"""Dynamic discovery of LED matrix effects, fonts, and media assets."""

from __future__ import annotations

import ast
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EFFECT_CATEGORIES: Dict[str, str] = {
    "3d_box": "animation",
    "asteroids": "game",
    "aurora": "animation",
    "broadway": "animation",
    "eye": "animation",
    "futbol": "game",
    "game_of_life": "animation",
    "hallway": "animation",
    "image": "media",
    "jewels": "animation",
    "marquee": "text",
    "matrix": "animation",
    "multiball": "animation",
    "off": "utility",
    "pacman": "game",
    "pollock": "animation",
    "pong": "game",
    "rgb_test": "utility",
    "rgb_text": "utility",
    "snow": "animation",
    "snow_flakes": "animation",
    "space_invaders": "game",
    "sparkler": "animation",
    "tictactoe": "game",
    "video": "media",
    "warp": "animation",
    "water_ripple": "animation",
}

CONFIG_SCHEMAS: Dict[str, str] = {
    "marquee": "marquee",
    "image": "image",
    "video": "video",
}

VALID_FIELD_TYPES = {"select", "number", "boolean", "text", "color"}


def _humanize_name(name: str) -> str:
    special = {
        "rgb_test": "RGB Test",
        "rgb_text": "RGB Text",
        "tictactoe": "Tic-Tac-Toe",
        "pacman": "Pac-Man",
        "3d_box": "3D Box",
    }
    if name in special:
        return special[name]
    return " ".join(part.capitalize() for part in name.split("_"))


def _normalize_hex_color(raw: Any, fallback: str = "#ffffff") -> str:
    if not isinstance(raw, str):
        return fallback
    text = raw.strip().lower()
    hex_part = text[1:] if text.startswith("#") else text
    if len(hex_part) == 3:
        hex_part = "".join(ch * 2 for ch in hex_part)
    if len(hex_part) == 6 and all(ch in "0123456789abcdef" for ch in hex_part):
        return f"#{hex_part}"
    return fallback


def _finite_number(val: Any) -> Optional[float]:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return None
    fval = float(val)
    if not math.isfinite(fval):
        return None
    return int(fval) if isinstance(val, int) else fval


def _normalize_config_field(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None

    key = raw.get("key")
    field_type = raw.get("type")
    if not isinstance(key, str) or not key.strip():
        return None
    if not isinstance(field_type, str) or field_type not in VALID_FIELD_TYPES:
        return None

    key = key.strip()
    label = raw.get("label")
    field: Dict[str, Any] = {
        "key": key,
        "label": (
            label.strip()
            if isinstance(label, str) and label.strip()
            else _humanize_name(key)
        ),
        "type": field_type,
    }

    description = raw.get("description")
    if isinstance(description, str) and description.strip():
        field["description"] = description.strip()

    if raw.get("required") is True:
        field["required"] = True

    if field_type == "select":
        raw_options = raw.get("options")
        if not isinstance(raw_options, list) or not raw_options:
            return None
        options: List[Dict[str, str]] = []
        for opt in raw_options:
            if isinstance(opt, str):
                options.append({"value": opt, "label": _humanize_name(opt)})
            elif isinstance(opt, dict) and isinstance(opt.get("value"), str):
                opt_val = opt["value"]
                opt_lbl = opt.get("label")
                options.append(
                    {
                        "value": opt_val,
                        "label": (
                            opt_lbl.strip()
                            if isinstance(opt_lbl, str) and opt_lbl.strip()
                            else _humanize_name(opt_val)
                        ),
                    }
                )
        if not options:
            return None
        field["options"] = options
        default = raw.get("default")
        valid_values = {o["value"] for o in options}
        field["default"] = (
            default
            if isinstance(default, str) and default in valid_values
            else options[0]["value"]
        )

    elif field_type == "number":
        min_val = _finite_number(raw.get("min"))
        max_val = _finite_number(raw.get("max"))
        if min_val is not None and max_val is not None and min_val > max_val:
            min_val, max_val = max_val, min_val
        step_val = _finite_number(raw.get("step"))
        default_val = _finite_number(raw.get("default"))
        if min_val is not None:
            field["min"] = min_val
        if max_val is not None:
            field["max"] = max_val
        if step_val is not None and step_val > 0:
            field["step"] = step_val
        if raw.get("integer") is True:
            field["integer"] = True
        unit = raw.get("unit")
        if isinstance(unit, str) and unit.strip():
            field["unit"] = unit.strip()
        if default_val is not None:
            field["default"] = default_val
        elif min_val is not None:
            field["default"] = min_val
        else:
            field["default"] = 0

    elif field_type == "boolean":
        field["default"] = bool(raw.get("default", False))

    elif field_type == "text":
        default = raw.get("default")
        field["default"] = default if isinstance(default, str) else ""
        placeholder = raw.get("placeholder")
        if isinstance(placeholder, str) and placeholder.strip():
            field["placeholder"] = placeholder.strip()

    elif field_type == "color":
        field["default"] = _normalize_hex_color(raw.get("default"), "#ffffff")

    return field


def _dedupe_fields(raw_schema: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_schema, (list, tuple)):
        return []
    seen: set[str] = set()
    fields: List[Dict[str, Any]] = []
    for item in raw_schema:
        normalized = _normalize_config_field(item)
        if normalized is None or normalized["key"] in seen:
            continue
        seen.add(normalized["key"])
        fields.append(normalized)
    return fields


def _extract_effect_metadata(effect_file: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Safely inspect effect.py via AST for run() docstring and CONFIG_SCHEMA."""
    docstring = ""
    fields: List[Dict[str, Any]] = []
    try:
        tree = ast.parse(effect_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return docstring, fields

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            doc = ast.get_docstring(node) or ""
            docstring = doc.strip()
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CONFIG_SCHEMA":
                    try:
                        raw_schema = ast.literal_eval(node.value)
                    except (ValueError, SyntaxError, TypeError):
                        raw_schema = None
                    fields = _dedupe_fields(raw_schema)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "CONFIG_SCHEMA"
            and node.value is not None
        ):
            try:
                raw_schema = ast.literal_eval(node.value)
            except (ValueError, SyntaxError, TypeError):
                raw_schema = None
            fields = _dedupe_fields(raw_schema)

    return docstring, fields


def discover_fonts(repo_root: Path) -> List[str]:
    fonts_dir = repo_root / "fonts"
    if not fonts_dir.is_dir():
        return []
    return sorted(
        p.name
        for p in fonts_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".ttf", ".otf"}
    )


def discover_effect_media(
    effect_dir: Path, extensions: set[str], *, include_uploads: bool = False
) -> List[str]:
    if not effect_dir.is_dir():
        return []
    found: List[str] = []
    if include_uploads:
        uploads_dir = effect_dir / "_uploads"
        if uploads_dir.is_dir():
            upload_entries: List[tuple[float, str]] = []
            for p in uploads_dir.iterdir():
                if p.name.startswith(".") or p.suffix.lower() not in extensions:
                    continue
                try:
                    if not p.is_file():
                        continue
                    mtime = p.stat().st_mtime
                except OSError:
                    continue
                upload_entries.append((mtime, f"_uploads/{p.name}"))
            upload_entries.sort(key=lambda item: item[0], reverse=True)
            found.extend(name for _, name in upload_entries)

    root_entries: List[str] = []
    for p in effect_dir.iterdir():
        if p.name.startswith(".") or p.suffix.lower() not in extensions:
            continue
        try:
            if p.is_file():
                root_entries.append(p.name)
        except OSError:
            continue
    found.extend(sorted(root_entries))
    return found


def discover_effects(repo_root: Path) -> List[Dict[str, Any]]:
    effects_dir = repo_root / "src" / "effects"
    if not effects_dir.is_dir():
        return []

    results: List[Dict[str, Any]] = []
    for entry in sorted(effects_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        effect_file = entry / "effect.py"
        if not effect_file.is_file():
            continue

        name = entry.name
        docstring, config_fields = _extract_effect_metadata(effect_file)
        builtin_schema = CONFIG_SCHEMAS.get(name)
        if builtin_schema:
            schema = builtin_schema
        elif config_fields:
            schema = "fields"
        else:
            schema = "none"

        requires_config = bool(builtin_schema) or any(
            bool(field.get("required")) for field in config_fields
        )

        meta: Dict[str, Any] = {
            "id": name,
            "label": _humanize_name(name),
            "description": docstring or f"Run the {name} effect",
            "category": EFFECT_CATEGORIES.get(name, "animation"),
            "configSchema": schema,
            "requiresConfig": requires_config,
            "isUtility": EFFECT_CATEGORIES.get(name) == "utility",
        }

        if config_fields:
            meta["configFields"] = config_fields

        if name == "image":
            meta["availableFiles"] = discover_effect_media(
                entry,
                {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"},
                include_uploads=True,
            )
        elif name == "video":
            meta["availableFiles"] = discover_effect_media(
                entry,
                {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"},
                include_uploads=True,
            )

        results.append(meta)

    return results
