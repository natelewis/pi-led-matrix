import os
import time
import random
import inspect
import importlib
import multiprocessing
from src.main import Matrix, pixel_height, pixel_width, playlist_delay, playlist


def import_effect(name):
    effect_dir = os.path.realpath(
        os.path.abspath(
            os.path.join(
                os.path.split(inspect.getfile(inspect.currentframe()))[0],
                "effects/" + name,
            )
        )
    )
    return importlib.import_module("effects." + name + ".effect"), effect_dir


# preload all the effects
effects = []
for e_data in playlist:
    effect_module, e_dir = import_effect(e_data["effect"])
    effects.append(
        {
            "name": e_data["effect"],
            "argv": e_data["argv"],
            "module": effect_module,
            "dir": e_dir,
        }
    )


def run_effect(index):
    effect_obj = effects[index]
    print("Starting " + effect_obj["name"])
    # import effect # pylint: disable=import-outside-toplevel
    matrix = Matrix()
    effect_obj["module"].run(
        matrix,
        {
            "pixel_height": pixel_height,
            "pixel_width": pixel_width,
            "effect_dir": effect_obj["dir"],
            "argv": effect_obj["argv"],
        },
    )


if __name__ == "__main__":
    print("Starting playlist: CTRL-c to stop")
    multiprocessing.set_start_method("spawn")
    while True:
        effect_index = random.randrange(len(effects))
        p = multiprocessing.Process(
            target=run_effect, name="run_effect", args=(effect_index,)
        )
        p.start()
        p.join()
