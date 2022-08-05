import sys
import os
import inspect
import time
import random
import multiprocessing
from src.led_matrix import Matrix, pixel_height, pixel_width, playlist_delay, playlist

# mock target task function
def run_effect():
    effect_item = random.choice(playlist)
    effect_module  = 'effects/' + effect_item['effect']
    sys.path.append(effect_module)
    effect_dir = os.path.realpath(
        os.path.abspath(
            os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0], effect_module)
        )
    )
    sys.path.insert(0, effect_dir)
    print("starting " + effect_module)
    import effect # pylint: disable=import-outside-toplevel
    matrix = Matrix()
    effect.run(matrix, {
        'pixel_height': pixel_height,
        'pixel_width': pixel_width,
        'effect_dir': effect_dir,
        'argv': effect_item['argv'],
    })

if __name__ == '__main__':
    while True:
        p = multiprocessing.Process(target=run_effect, name="run_effect", args=())
        p.start()
        time.sleep(playlist_delay)
        p.terminate()
        p.join()
