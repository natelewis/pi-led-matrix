import os
import random
import inspect
import importlib
import multiprocessing
from main import (
    Matrix,
    VIRTUAL_ENV,
    pixel_height,
    pixel_width,
    playlist,
    color_order,
)


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
            "module": effect_module,
            "dir": e_dir,
            "color_order": color_order,
            "effect": e_data.get("effect", ""),
        }
    )


def run_effect(index, matrix=None):
    effect_obj = effects[index]
    print("Starting " + effect_obj["name"])
    if matrix is None:
        matrix = Matrix()
    else:
        matrix.reset_timer()
        matrix.reset()
    effect_obj["module"].run(
        matrix,
        {
            "pixel_height": pixel_height,
            "pixel_width": pixel_width,
            "effect_dir": effect_obj["dir"],
            "color_order": color_order,
            "effect": effect_obj["effect"],
        },
    )


if __name__ == "__main__":
    print("Starting playlist: CTRL-c to stop")
    if VIRTUAL_ENV:
        shared_matrix = Matrix()
        try:
            while True:
                run_effect(random.randrange(len(effects)), shared_matrix)
        except KeyboardInterrupt:
            pass
        finally:
            shared_matrix.close()
    else:
        multiprocessing.set_start_method("spawn")
        while True:
            effect_index = random.randrange(len(effects))
            p = multiprocessing.Process(
                target=run_effect, name="run_effect", args=(effect_index,)
            )
            p.start()
            p.join()
