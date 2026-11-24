
# Raspberry Pi LED Matrix Effects

List of current contributed effects that can be run as follows:

```bash
make run effect=effect_name
```

Some that support options can be passed a config:

```bash
make run effect=effect_name config='{"some_json": "config settings"}'
```

Playlist are loaded at random from a configurable list in `config.py` with:

```bash
make playlist
```

To make a new effect, just copy an existing effect directory that might have some common code and alter its contents.  You'll see there is a `run()` function that receives a `matrix` and `config` argument.  The `config` dictionary will have:

* pixel_width
* pixel_height
* effect_directory
* effect (This is a dictionary containing what was passed as the effect JSON config whe loading the effect)

### Declaring UI Controls (`CONFIG_SCHEMA`)

Any effect can expose native controls in **LED Matrix Studio** (dropdowns, sliders, toggles, text inputs, and a standard color picker) by defining a top-level `CONFIG_SCHEMA` list of plain dicts inside `src/effects/<name>/effect.py`. Studio parses it safely via AST without importing the effect.

Supported field types:

| `type` | Studio Control | Supported Properties |
| --- | --- | --- |
| `"select"` | Dropdown | `key`, `label`, `options` (`[{"value", "label"}]` or `["a", "b"]`), `default`, `description`, `required` |
| `"number"` | Slider (when `min` & `max` set) or numeric input | `key`, `label`, `default`, `min`, `max`, `step`, `integer`, `unit`, `description`, `required` |
| `"boolean"` | Toggle switch | `key`, `label`, `default`, `description` |
| `"color"` | Standard color picker (color wheel, hex `#rrggbb` input, RGB readout & vivid LED swatches) | `key`, `label`, `default` (`"#rrggbb"`), `description`, `required` |
| `"text"` | Text input | `key`, `label`, `default`, `placeholder`, `description`, `required` |

Use `"select"` when curated multi-color themes/palettes make sense (e.g., `hallway`, `snow_flakes`), and `"color"` whenever arbitrary user-picked colors make sense (e.g., `matrix`, `water_ripple`, text accents). Inside `run(matrix, config)`, convert hex color values cleanly with `matrix.parse_color(effect_cfg.get("color"), default_rgb)`:

```python
CONFIG_SCHEMA = [
    {
        "key": "color",
        "label": "Primary Color",
        "type": "color",
        "default": "#00e5ff",
        "description": "Any hex color picked in LED Matrix Studio.",
    },
    {
        "key": "speed",
        "label": "Speed",
        "type": "number",
        "default": 1.0,
        "min": 0.2,
        "max": 3.0,
        "step": 0.1,
        "unit": "×",
    },
]

def run(matrix, config):
    effect_cfg = config.get("effect") or {}
    rgb = matrix.parse_color(effect_cfg.get("color"), (0, 229, 255))
```

## hallway

Immersive 3D curving neon hallway with perspective portal arches, recessed overhead light panels, glossy floor reflections, traveling energy pulses, drifting light motes, and atmospheric portal fog.

Optional config keys: `theme` (`"auto"` [default], `"cyber"`, `"synthwave"`, `"crimson"`, `"gold"`, or `"emerald"`), `speed` (`0.2`–`3.0`), `curve` (`0.0`–`2.0`), `pulse` (`true`/`false`), and `motes` (`true`/`false`).

```bash
make run effect=hallway config='{"theme":"synthwave","speed":1.3,"curve":1.2}'
```

## image image.png

Resize the image in any graphic editor to the size of the matrix and save it as a PNG.  Place image in the `image` effect directory.  Fonts usually have some padding and such, so you sometimes have to adjust for that on the 'y' settings.

```bash
make run effect=image config='{"file":"_some_image_40x26.png"}'
```

## marquee

Passing json definitions can create any type of marquee.  Place custom fonts in the `./fonts` directory.

```bash
make run effect=marquee config='{ "messages": [{ "left": 10, "right": 5, "r": 255, "g": 255, "b": 255, "message": "my message", "font": "dosis.ttf"}]}'
# example of:
#     The
#        Beverly
make run effect=marquee config='{"messages": [{"left": 0, "right": 0, "r": 0, "g": 0, "b": 255, "message": "The", "font": "dosis.ttf"}, {"left": 25, "right": 9, "r": 0, "g": 0, "b": 255, "message": "Beverly", "font": "dosis.ttf"}]}'
# notice the -5 for the first `y`.  This offsets the font because of some top padding the dosis font has.
```

<https://user-images.githubusercontent.com/1588877/180103974-6579da59-469b-4a1d-952b-508631e22fd3.mov>

Or with a fancier font:

<https://user-images.githubusercontent.com/1588877/180108937-b5a49bbd-d0af-445e-bcce-64446570fc11.mov>

## off

Simple effect that sets all lights to black.

## pong

Simulates a pong game

<https://user-images.githubusercontent.com/1588877/180089226-94fc8646-5f0d-4173-a96a-8605a65c4c78.mov>

## snow

Simple snow effect.

## snow_flakes

Swirling 6-fold crystalline snowflakes drifting across three parallax depth layers over a moonlit winter sky with gentle wind gusts, specular ice glints, and an accumulating bottom snowdrift.

![Snow Flakes Effect Preview](snow_flakes/preview.png)

Optional config keys: `speed` (`0.2`–`3.0`), `wind` (`0.0`–`3.0`), `density` (`0.3`–`2.5`), `drift` (`true`/`false`), and `palette` (`"winter"`, `"aurora"`, or `"warm"`).

```bash
make run effect=snow_flakes config='{"palette":"aurora","wind":1.5,"drift":true}'
```

## rgb_test

Test that checks your RGB configuration.  Red... Blue... Green... (repeat)

## video filename.mp4

To play a video, first resize the video with `ffmpeg` to the size of your matrix.  In this example
the matrix is 60 wide by 30 tall.

```bash
ffmpeg -i _test.mp4 -vf scale=60:30 _test_60x30.mp4
```

Copy the video to the `video` effect directory.

```bash
make run effect=video config='{"file":"_test_60x30.mp4"}'
```

## water_ripple

Blue circle animation that resembles water ripples.

---

Created by [@natelewis](https://github.com/natelewis). Released under the MIT license.
