"""Unit tests for dynamic effect discovery and CONFIG_SCHEMA extraction."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from web.server.effects import discover_effects

REPO_ROOT = Path(__file__).resolve().parents[3]


class EffectDiscoveryTestCase(unittest.TestCase):
    def test_discovers_builtin_and_schema_fields_effects(self):
        effects = {fx["id"]: fx for fx in discover_effects(REPO_ROOT)}

        # Effects with declarative CONFIG_SCHEMA -> configSchema="fields", optional by default
        for fx_id, expected_keys in (
            ("hallway", ["theme", "speed", "curve", "pulse", "motes"]),
            ("snow_flakes", ["palette", "speed", "wind", "density", "drift"]),
            ("aurora", ["speed", "stars"]),
            ("multiball", ["balls"]),
            ("matrix", ["color", "background"]),
            ("water_ripple", ["color"]),
        ):
            self.assertIn(fx_id, effects)
            meta = effects[fx_id]
            self.assertEqual(meta["configSchema"], "fields")
            self.assertFalse(meta["requiresConfig"])
            field_keys = [f["key"] for f in meta.get("configFields", [])]
            self.assertEqual(field_keys, expected_keys)

        # Hallway theme select options
        hallway_theme = effects["hallway"]["configFields"][0]
        self.assertEqual(hallway_theme["type"], "select")
        self.assertEqual(hallway_theme["default"], "auto")
        self.assertEqual(
            [opt["value"] for opt in hallway_theme["options"]],
            ["auto", "cyber", "synthwave", "crimson", "gold", "emerald"],
        )

        # Video keeps its specialized media editor AND exposes its extra playback speed field
        video = effects["video"]
        self.assertEqual(video["configSchema"], "video")
        self.assertTrue(video["requiresConfig"])
        self.assertEqual([f["key"] for f in video.get("configFields", [])], ["speed"])

        # Marquee & image require config, plain animations do not
        self.assertTrue(effects["marquee"]["requiresConfig"])
        self.assertTrue(effects["image"]["requiresConfig"])
        self.assertEqual(effects["warp"]["configSchema"], "none")
        self.assertFalse(effects["warp"]["requiresConfig"])
        self.assertNotIn("configFields", effects["warp"])

    def test_handles_shorthand_options_required_fields_and_invalid_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fx_dir = root / "src" / "effects" / "custom_fx"
            fx_dir.mkdir(parents=True)
            (fx_dir / "effect.py").write_text(
                '''CONFIG_SCHEMA = [
    {"key": "mode", "type": "select", "options": ["fast", "slow"]},
    {"key": "accent", "type": "color", "default": "#0F8"},
    {"key": "api_key", "type": "text", "required": True, "placeholder": "Enter key"},
    {"key": "bad_select", "type": "select", "options": []},
    {"key": "unknown_type", "type": "bogus"},
    "not_a_dict",
]

def run(matrix, config):
    """Custom test effect."""
''',
                encoding="utf-8",
            )

            discovered = discover_effects(root)
            self.assertEqual(len(discovered), 1)
            meta = discovered[0]
            self.assertEqual(meta["id"], "custom_fx")
            self.assertEqual(meta["description"], "Custom test effect.")
            self.assertEqual(meta["configSchema"], "fields")
            self.assertTrue(meta["requiresConfig"])
            fields = meta["configFields"]
            self.assertEqual(len(fields), 3)
            self.assertEqual(
                fields[0]["options"],
                [
                    {"value": "fast", "label": "Fast"},
                    {"value": "slow", "label": "Slow"},
                ],
            )
            self.assertEqual(fields[0]["default"], "fast")
            self.assertEqual(fields[1]["type"], "color")
            self.assertEqual(fields[1]["default"], "#00ff88")
            self.assertEqual(fields[2]["key"], "api_key")
            self.assertTrue(fields[2]["required"])


if __name__ == "__main__":
    unittest.main()
