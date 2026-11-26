"""Dynamic discovery of LED matrix effects, declarative CONFIG_SCHEMA, presets, fonts, and media."""

from __future__ import annotations

import ast
import math
import sys
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
    "mightnight_fireworks": "animation",
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
    "image": "image",
    "video": "video",
}

VALID_FIELD_TYPES = {
    "select",
    "number",
    "boolean",
    "text",
    "textarea",
    "color",
    "font",
    "alignment",
    "list",
}

VALID_HORIZONTAL_ALIGNS = {"left", "center", "right"}
VALID_GRID_ALIGNS = {
    "left-top",
    "center-top",
    "right-top",
    "left-middle",
    "center-middle",
    "right-middle",
    "left-bottom",
    "center-bottom",
    "right-bottom",
}


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


def _normalize_show_when(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    dep_key = raw.get("key")
    if not isinstance(dep_key, str) or not dep_key.strip():
        return None
    cond: Dict[str, Any] = {"key": dep_key.strip()}
    if "equals" in raw:
        cond["equals"] = raw["equals"]
    if "notEquals" in raw:
        cond["notEquals"] = raw["notEquals"]
    if isinstance(raw.get("in"), (list, tuple)):
        cond["in"] = list(raw["in"])
    gt_val = _finite_number(raw.get("gt"))
    if gt_val is not None:
        cond["gt"] = gt_val
    if "truthy" in raw:
        cond["truthy"] = bool(raw["truthy"])
    return cond if len(cond) > 1 else None


def _normalize_tokens(raw: Any) -> List[Dict[str, str]]:
    if not isinstance(raw, (list, tuple)):
        return []
    tokens: List[Dict[str, str]] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            tokens.append({"token": item.strip(), "label": item.strip()})
        elif isinstance(item, dict) and isinstance(item.get("token"), str) and item["token"].strip():
            tok = item["token"].strip()
            lbl = item.get("label")
            tokens.append(
                {
                    "token": tok,
                    "label": lbl.strip() if isinstance(lbl, str) and lbl.strip() else tok,
                }
            )
    return tokens


def _normalize_config_field(raw: Any, *, depth: int = 0) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None

    key = raw.get("key")
    field_type = raw.get("type")
    if not isinstance(key, str) or not key.strip():
        return None
    if not isinstance(field_type, str) or field_type not in VALID_FIELD_TYPES:
        return None
    if field_type == "list" and depth > 0:
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

    section = raw.get("section")
    if isinstance(section, str) and section.strip():
        field["section"] = section.strip()

    show_when = _normalize_show_when(raw.get("showWhen"))
    if show_when is not None:
        field["showWhen"] = show_when

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
        allow_auto = raw.get("allowAuto") is True
        if allow_auto:
            field["allowAuto"] = True
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

        raw_default = raw.get("default")
        default_val = _finite_number(raw_default)
        if allow_auto and isinstance(raw_default, str) and raw_default.strip().lower() == "auto":
            field["default"] = "auto"
        elif default_val is not None:
            field["default"] = default_val
        elif allow_auto:
            field["default"] = "auto"
        elif min_val is not None:
            field["default"] = min_val
        else:
            field["default"] = 0

    elif field_type == "boolean":
        field["default"] = bool(raw.get("default", False))

    elif field_type in ("text", "textarea"):
        default = raw.get("default")
        field["default"] = default if isinstance(default, str) else ""
        placeholder = raw.get("placeholder")
        if isinstance(placeholder, str) and placeholder.strip():
            field["placeholder"] = placeholder.strip()
        tokens = _normalize_tokens(raw.get("tokens"))
        if tokens:
            field["tokens"] = tokens

    elif field_type == "color":
        field["default"] = _normalize_hex_color(raw.get("default"), "#ffffff")

    elif field_type == "font":
        default = raw.get("default")
        field["default"] = (
            default.strip()
            if isinstance(default, str) and default.strip()
            else "dosis.ttf"
        )
        preview_key = raw.get("previewTextKey")
        if isinstance(preview_key, str) and preview_key.strip():
            field["previewTextKey"] = preview_key.strip()

    elif field_type == "alignment":
        mode = str(raw.get("mode") or "horizontal").strip().lower()
        if mode not in ("horizontal", "grid"):
            mode = "horizontal"
        field["mode"] = mode
        raw_def = str(raw.get("default") or "").strip().lower()
        if mode == "grid":
            field["default"] = raw_def if raw_def in VALID_GRID_ALIGNS else "center-middle"
        else:
            field["default"] = raw_def if raw_def in VALID_HORIZONTAL_ALIGNS else "center"

    elif field_type == "list":
        item_fields = _dedupe_fields(raw.get("itemFields"), depth=depth + 1)
        if not item_fields:
            return None
        field["itemFields"] = item_fields
        item_label = raw.get("itemLabel")
        if isinstance(item_label, str) and item_label.strip():
            field["itemLabel"] = item_label.strip()
        add_label = raw.get("addLabel")
        if isinstance(add_label, str) and add_label.strip():
            field["addLabel"] = add_label.strip()
        min_items = _finite_number(raw.get("minItems"))
        max_items = _finite_number(raw.get("maxItems"))
        if min_items is not None:
            field["minItems"] = max(0, int(min_items))
        if max_items is not None:
            field["maxItems"] = max(1, int(max_items))
        if raw.get("reorderable") is True:
            field["reorderable"] = True
        raw_default = raw.get("default")
        if isinstance(raw_default, list):
            field["default"] = [item for item in raw_default if isinstance(item, dict)]
        else:
            field["default"] = []

    return field


def _dedupe_fields(raw_schema: Any, *, depth: int = 0) -> List[Dict[str, Any]]:
    if not isinstance(raw_schema, (list, tuple)):
        return []
    seen: set[str] = set()
    fields: List[Dict[str, Any]] = []
    for item in raw_schema:
        normalized = _normalize_config_field(item, depth=depth)
        if normalized is None or normalized["key"] in seen:
            continue
        seen.add(normalized["key"])
        fields.append(normalized)
    return fields


def _normalize_presets(raw_presets: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_presets, (list, tuple)):
        return []
    seen: set[str] = set()
    presets: List[Dict[str, Any]] = []
    for item in raw_presets:
        if not isinstance(item, dict):
            continue
        pid = item.get("id")
        cfg = item.get("config")
        if not isinstance(pid, str) or not pid.strip() or not isinstance(cfg, dict):
            continue
        pid = pid.strip()
        if pid in seen:
            continue
        seen.add(pid)
        label = item.get("label")
        entry: Dict[str, Any] = {
            "id": pid,
            "label": (
                label.strip()
                if isinstance(label, str) and label.strip()
                else _humanize_name(pid)
            ),
            "config": cfg,
        }
        desc = item.get("description")
        if isinstance(desc, str) and desc.strip():
            entry["description"] = desc.strip()
        presets.append(entry)
    return presets


def _extract_effect_metadata(
    effect_file: Path,
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], bool]:
    """Safely inspect effect.py via AST for docstring, CONFIG_SCHEMA, CONFIG_PRESETS & preview()."""
    docstring = ""
    fields: List[Dict[str, Any]] = []
    presets: List[Dict[str, Any]] = []
    has_preview = False
    try:
        tree = ast.parse(effect_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return docstring, fields, presets, has_preview

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name == "run":
                doc = ast.get_docstring(node) or ""
                docstring = doc.strip()
            elif node.name == "preview":
                has_preview = True
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "CONFIG_SCHEMA":
                    try:
                        raw_schema = ast.literal_eval(node.value)
                    except (ValueError, SyntaxError, TypeError):
                        raw_schema = None
                    fields = _dedupe_fields(raw_schema)
                elif target.id == "CONFIG_PRESETS":
                    try:
                        raw_presets = ast.literal_eval(node.value)
                    except (ValueError, SyntaxError, TypeError):
                        raw_presets = None
                    presets = _normalize_presets(raw_presets)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            if node.target.id == "CONFIG_SCHEMA":
                try:
                    raw_schema = ast.literal_eval(node.value)
                except (ValueError, SyntaxError, TypeError):
                    raw_schema = None
                fields = _dedupe_fields(raw_schema)
            elif node.target.id == "CONFIG_PRESETS":
                try:
                    raw_presets = ast.literal_eval(node.value)
                except (ValueError, SyntaxError, TypeError):
                    raw_presets = None
                presets = _normalize_presets(raw_presets)

    return docstring, fields, presets, has_preview


def discover_font_catalog(repo_root: Path) -> List[Dict[str, Any]]:
    for candidate in (repo_root / "src", Path(__file__).resolve().parents[2] / "src"):
        resolved = str(candidate.resolve())
        if candidate.is_dir() and resolved not in sys.path:
            sys.path.insert(0, resolved)
    from lib import led_fonts  # pylint: disable=import-outside-toplevel

    return led_fonts.discover_font_catalog(repo_root)


def discover_fonts(repo_root: Path) -> List[str]:
    return [item["id"] for item in discover_font_catalog(repo_root)]


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
        docstring, config_fields, config_presets, has_preview = _extract_effect_metadata(
            effect_file
        )
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
            "hasPreview": has_preview,
        }

        if config_fields:
            meta["configFields"] = config_fields
        if config_presets:
            meta["configPresets"] = config_presets

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
