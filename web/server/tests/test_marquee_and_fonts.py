"""Unit tests for shared font catalog, text layout, marquee player, and generic preview API."""

from __future__ import annotations

import base64
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = str(REPO_ROOT / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from effects.marquee import effect as marquee_effect  # noqa: E402
from lib import led_fonts, text_layout  # noqa: E402
from web.server.config_store import ConfigStore, ConfigValidationError  # noqa: E402
from web.server.effects import discover_effects  # noqa: E402
from web.server.fonts import FontStore  # noqa: E402
from web.server.preview import render_effect_preview  # noqa: E402


class MarqueeAndFontsTestCase(unittest.TestCase):
    def test_font_catalog_includes_builtin_pixel_and_bundled_fonts(self):
        catalog = led_fonts.discover_font_catalog(REPO_ROOT)
        ids = {item["id"] for item in catalog}
        self.assertIn("pixel_5x7", ids)
        self.assertIn("dosis.ttf", ids)
        self.assertIn("silkscreen.ttf", ids)
        self.assertIn("bungee.ttf", ids)
        self.assertIn("share_tech_mono.ttf", ids)
        self.assertGreaterEqual(len(catalog), 10)

        # Path traversal protection
        self.assertFalse(led_fonts.is_safe_font_ref("../etc/passwd"))
        self.assertFalse(led_fonts.is_safe_font_ref("/etc/passwd"))
        self.assertFalse(led_fonts.is_safe_font_ref("_uploads/../../secret.ttf"))
        self.assertTrue(led_fonts.is_safe_font_ref("pixel_5x7"))
        self.assertTrue(led_fonts.is_safe_font_ref("dosis.ttf"))
        self.assertTrue(led_fonts.is_safe_font_ref("_uploads/custom.ttf"))

    def test_font_store_upload_validation_and_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fonts_dir = root / "fonts"
            fonts_dir.mkdir(parents=True)
            shutil.copy(REPO_ROOT / "fonts" / "dosis.ttf", fonts_dir / "dosis.ttf")

            store = FontStore(root)
            raw_ttf = (REPO_ROOT / "fonts" / "dosis.ttf").read_bytes()
            b64_ttf = base64.b64encode(raw_ttf).decode("ascii")

            saved = store.save_uploaded_font("My Custom Font.ttf", b64_ttf)
            self.assertTrue(saved["id"].startswith("_uploads/"))
            self.assertTrue(saved["uploaded"])

            # Invalid / corrupt font rejected
            bad_b64 = base64.b64encode(b"not a real ttf file").decode("ascii")
            with self.assertRaises(ValueError):
                store.save_uploaded_font("bad.ttf", bad_b64)

            # Wrong extension rejected
            with self.assertRaises(ValueError):
                store.save_uploaded_font("evil.py", b64_ttf)

            # Cannot delete bundled font
            with self.assertRaises(ValueError):
                store.delete_uploaded_font("dosis.ttf")

            # Can delete uploaded font
            self.assertTrue(store.delete_uploaded_font(saved["id"]))
            self.assertFalse(store.delete_uploaded_font(saved["id"]))

    def test_dynamic_token_expansion_and_optical_layout(self):
        fixed_now = datetime(2026, 11, 23, 21, 5, 30)
        expanded = text_layout.expand_dynamic_tokens(
            "{time} | {time24} | {date} | {day} | {countdown:2026-11-24 21:05:30}",
            now=fixed_now,
        )
        self.assertEqual(expanded, "9:05 PM | 21:05 | Nov 23 | Monday | 1d 00h 00m")

        # Pixel 5x7 font renders crisp non-empty ink
        mask, metrics = text_layout.render_text_mask("HI", "pixel_5x7", 7, crisp=True)
        self.assertGreater(metrics["ink_w"], 0)
        self.assertEqual(mask.height, 7)
        arr = np.array(mask)
        self.assertTrue(set(np.unique(arr)).issubset({0, 255}))

    def test_marquee_preview_across_screen_sizes_and_legacy_config(self):
        for w, h in ((32, 16), (64, 32), (128, 72)):
            for preset in marquee_effect.CONFIG_PRESETS:
                payload = render_effect_preview(
                    REPO_ROOT, "marquee", preset["config"], w, h
                )
                self.assertEqual(payload["width"], w)
                self.assertEqual(payload["height"], h)
                self.assertGreaterEqual(payload["frameCount"], 1)
                raw = base64.b64decode(payload["framesBase64"])
                self.assertEqual(len(raw), payload["frameCount"] * w * h * 3)
                self.assertTrue(len(payload["diagnostics"]) >= 1)

        # Legacy messages[] config still renders seamlessly
        legacy_cfg = {
            "messages": [
                {
                    "left": 0,
                    "right": 5,
                    "r": 255,
                    "g": 120,
                    "b": 0,
                    "message": "Legacy Marquee",
                    "font": "dosis.ttf",
                }
            ]
        }
        legacy_payload = render_effect_preview(REPO_ROOT, "marquee", legacy_cfg, 64, 32)
        self.assertGreaterEqual(legacy_payload["frameCount"], 1)

    def test_multiline_even_vertical_spacing(self):
        for text, w, h in (
            ("WELCOME\nTO THE LAB", 128, 72),
            ("LINE 1\nLINE 2\nLINE 3", 128, 72),
            ("HELLO\nWORLD", 64, 32),
        ):
            norm = marquee_effect.normalize_marquee_config({"text": text})
            slides, _, _ = marquee_effect._build_slides_and_diagnostics(norm, w, h)
            sl = slides[0]
            self.assertFalse(sl.vertical_scroll)
            _, sy0, _, sy1 = sl.safe_rect
            ys = sl.line_ys
            hs = [ln.ink_h for ln in sl.lines]
            gaps = [ys[0] - sy0] + [
                ys[i + 1] - (ys[i] + hs[i]) for i in range(len(ys) - 1)
            ] + [sy1 - (ys[-1] + hs[-1])]
            self.assertLessEqual(max(gaps) - min(gaps), 1, f"Uneven gaps for {text!r}: {gaps}")

    def test_credits_roll_exits_screen_before_restarting(self):
        preset = next(p for p in marquee_effect.CONFIG_PRESETS if p["id"] == "credits_roll")
        cfg = {**preset["config"], "bg_type": "solid", "bg_color": "#000000"}
        res = marquee_effect.preview(cfg, 128, 72)
        self.assertGreaterEqual(len(res["frames"]), 16)
        self.assertEqual(int(res["frames"][0].max()), 0)
        self.assertGreater(int(res["frames"][len(res["frames"]) // 2].max()), 0)
        self.assertEqual(int(res["frames"][-1].max()), 0)

    def test_unequal_length_multiline_sync_and_seamless_loop(self):
        preset = next(p for p in marquee_effect.CONFIG_PRESETS if p["id"] == "retro_pixel")
        for cfg, w, h in (
            (preset["config"], 32, 16),
            ({**preset["config"], "mode": "scroll_left"}, 128, 72),
            ({**preset["config"], "mode": "bounce"}, 128, 72),
        ):
            norm = marquee_effect.normalize_marquee_config(cfg)
            slides, _, _ = marquee_effect._build_slides_and_diagnostics(norm, w, h)
            motions = {ln.motion for ln in slides[0].lines}
            self.assertEqual(len(motions), 1)
            dur = marquee_effect._compute_preview_cycle_sec(slides, norm)
            f0 = marquee_effect._render_marquee_frame(slides, norm, w, h, 0.0)
            f_end = marquee_effect._render_marquee_frame(slides, norm, w, h, dur)
            self.assertTrue(np.array_equal(f0, f_end))

    def test_reusable_schema_types_and_presets_for_third_party_effects(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fx_dir = root / "src" / "effects" / "custom_ticker"
            fx_dir.mkdir(parents=True)
            (fx_dir / "effect.py").write_text(
                '''CONFIG_SCHEMA = [
    {"key": "headline", "type": "textarea", "section": "Content", "tokens": ["{time}"]},
    {"key": "font", "type": "font", "section": "Style", "default": "pixel_5x7", "previewTextKey": "headline"},
    {"key": "size", "type": "number", "allowAuto": True, "default": "auto", "min": 6, "max": 64},
    {"key": "align", "type": "alignment", "mode": "grid", "default": "center-middle"},
    {
        "key": "items",
        "type": "list",
        "reorderable": True,
        "itemFields": [
            {"key": "title", "type": "text", "required": True},
            {"key": "accent", "type": "color", "default": "#00e5ff"},
        ],
    },
]
CONFIG_PRESETS = [{"id": "default", "label": "Default", "config": {"headline": "Hello"}}]

def preview(config, width, height):
    return {"width": width, "height": height, "fps": 1, "frames": []}

def run(matrix, config):
    """Third-party ticker reusing declarative controls."""
''',
                encoding="utf-8",
            )
            discovered = discover_effects(root)
            self.assertEqual(len(discovered), 1)
            meta = discovered[0]
            self.assertEqual(meta["configSchema"], "fields")
            self.assertTrue(meta["hasPreview"])
            self.assertEqual(len(meta["configPresets"]), 1)
            fields = {f["key"]: f for f in meta["configFields"]}
            self.assertEqual(fields["headline"]["type"], "textarea")
            self.assertEqual(fields["font"]["type"], "font")
            self.assertEqual(fields["size"]["default"], "auto")
            self.assertTrue(fields["size"]["allowAuto"])
            self.assertEqual(fields["align"]["mode"], "grid")
            self.assertEqual(fields["items"]["type"], "list")
            self.assertEqual(len(fields["items"]["itemFields"]), 2)

    def test_config_store_blocks_font_path_traversal(self):
        store = ConfigStore(REPO_ROOT)
        cfg = store.load_default_config()
        cfg["playlist"] = [{"effect": "marquee", "config": {"font": "../../etc/passwd"}}]
        with self.assertRaises(ConfigValidationError):
            store.validate(cfg)

        cfg["playlist"] = [
            {
                "effect": "marquee",
                "config": {
                    "text": "HELLO\nWORLD",
                    "font": "bungee.ttf",
                    "font_size": "auto",
                },
            }
        ]
        validated = store.validate(cfg)
        self.assertEqual(validated["playlist"][0]["config"]["font"], "bungee.ttf")


if __name__ == "__main__":
    unittest.main()
