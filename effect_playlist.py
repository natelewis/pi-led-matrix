import sys
import os
import inspect
import time
import random
import multiprocessing
from led_matrix import Matrix, PIXEL_HEIGHT, PIXEL_WIDTH, PLAYLIST_DELAY, PLAYLIST

# mock target task function
def run_effect():
    effect_item = random.choice(PLAYLIST)
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
        'pixel_height': PIXEL_HEIGHT,
        'pixel_width': PIXEL_WIDTH,
        'effect_dir': effect_dir,
        'argv': effect_item['argv'],
    })

if __name__ == '__main__':
    while True:
        p = multiprocessing.Process(target=run_effect, name="run_effect", args=())
        p.start()
        time.sleep(PLAYLIST_DELAY)
        p.terminate()
        p.join()
