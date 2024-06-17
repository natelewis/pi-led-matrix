def tunnel_circle(matrix, x):
    """create individual circle"""
    if x > 0:
        matrix.circle((30, 15), x + 1, (0, 0, 90), 1)
        matrix.circle((30, 15), x, (0, 0, 255), 1)
        if x - 1 > 0:
            matrix.circle((30, 15), x - 1, (0, 0, 90), 1)


def run(matrix, _):
    """water rippling outwards"""
    rings = [0, 10, 20, 30]
    while matrix.ready():
        matrix.reset()
        for idx, x in enumerate(rings):
            x = x + 1
            if x > 40:
                x = 0
            rings[idx] = x
            tunnel_circle(matrix, x)

        matrix.show()
