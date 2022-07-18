import os
import sys
import inspect
from led_matrix import Matrix, pixel_height, pixel_width

effect_module  = 'effects/' + sys.argv[1]
sys.path.append(effect_module)
effect_dir = os.path.realpath(
    os.path.abspath(
        os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0], effect_module)
    )
)
sys.path.insert(0, effect_dir)
print("starting " + effect_module)
import effect # pylint: disable=wrong-import-position, wrong-import-order
matrix = Matrix()

effect.run(matrix, {
    'pixel_height': pixel_height,
    'pixel_width': pixel_width,
    'effect_dir': effect_dir,
    'argv': sys.argv[2:],
})
