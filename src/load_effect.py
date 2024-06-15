import os
import sys
import json
import inspect
from main import Matrix, pixel_height, pixel_width

EFFECT = sys.argv[1]
EFFECT_MODULE = "effects/" + EFFECT
sys.path.append(EFFECT_MODULE)
effect_dir = os.path.realpath(
    os.path.abspath(
        os.path.join(
            os.path.split(inspect.getfile(inspect.currentframe()))[0], EFFECT_MODULE
        )
    )
)

sys.path.insert(0, effect_dir)
print(f"Starting: {EFFECT_MODULE}")

effect_config = "{}"  # pylint: disable=invalid-name
try:
    if sys.argv[2] != "":
        effect_config = json.loads(sys.argv[2])
except json.JSONDecodeError:
    print("Error: Invalid effect config JSON")
    sys.exit()

print(f'Playlist JSON: {{"effect": "{EFFECT}", "config": {sys.argv[2]}}}')
import effect  # pylint: disable=wrong-import-position, wrong-import-order

matrix = Matrix()


effect.run(
    matrix,
    {
        "pixel_height": pixel_height,
        "pixel_width": pixel_width,
        "effect_dir": effect_dir,
        "effect": effect_config,
    },
)
