"""Dynamic discovery of LED matrix effects, fonts, and media assets."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List


EFFECT_CATEGORIES: Dict[str, str] = {
    "broadway": "animation",
    "eye": "animation",
    "futbol": "game",
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


def _extract_run_docstring(effect_file: Path) -> str:
    try:
        tree = ast.parse(effect_file.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "run":
                doc = ast.get_docstring(node) or ""
                return doc.strip()
    except (OSError, SyntaxError):
        pass
    return ""


def _humanize_name(name: str) -> str:
    special = {
        "rgb_test": "RGB Test",
        "rgb_text": "RGB Text",
        "tictactoe": "Tic-Tac-Toe",
        "pacman": "Pac-Man",
    }
    if name in special:
        return special[name]
    return " ".join(part.capitalize() for part in name.split("_"))


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
            found.extend(
                f"_uploads/{p.name}"
                for p in sorted(uploads_dir.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True)
                if p.is_file() and p.suffix.lower() in extensions
            )
    found.extend(
        sorted(
            p.name
            for p in effect_dir.iterdir()
            if p.is_file() and p.suffix.lower() in extensions
        )
    )
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
        schema = CONFIG_SCHEMAS.get(name, "none")
        meta: Dict[str, Any] = {
            "id": name,
            "label": _humanize_name(name),
            "description": _extract_run_docstring(effect_file) or f"Run the {name} effect",
            "category": EFFECT_CATEGORIES.get(name, "animation"),
            "configSchema": schema,
            "isUtility": EFFECT_CATEGORIES.get(name) == "utility",
        }

        if name == "image":
            meta["availableFiles"] = discover_effect_media(
                entry, {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}, include_uploads=True
            )
        elif name == "video":
            meta["availableFiles"] = discover_effect_media(
                entry, {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}, include_uploads=True
            )

        results.append(meta)

    return results
