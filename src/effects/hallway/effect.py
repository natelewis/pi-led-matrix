import math


def tunnel_rectangle(matrix, center_x, height, ceiling_height, offset):
    """create individual rectangle"""
    matrix.rectangle(
        (center_x - offset, height - offset - ceiling_height),
        (center_x + offset, height + offset),
        (90, 0, 0),
        1,
    )


def run(matrix, config):
    """hallway coming towards you"""
    center_x = config["pixel_width"] // 2
    height = config["pixel_height"]
    ceiling_height = max(2, height // 3)
    spacing = 10
    reach = max(center_x, height - ceiling_height) + 2
    max_offset = math.ceil(reach / spacing) * spacing
    wall_offsets = list(range(0, max_offset, spacing))

    while matrix.ready():
        matrix.reset()
        for idx, offset in enumerate(wall_offsets):
            offset = offset + 1
            if offset >= max_offset:
                offset = 0
            wall_offsets[idx] = offset
            tunnel_rectangle(matrix, center_x, height, ceiling_height, offset)

        matrix.show()
