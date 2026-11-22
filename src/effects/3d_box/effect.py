#
# 3D Box
# Ported from https://github.com/rm-hull/luma.examples/blob/main/examples/3d_box.py
# 25 February 2025
#

import math
import numpy as np
from operator import itemgetter


def radians(degrees):
    return degrees * math.pi / 180


class point(object):

    def __init__(self, x, y, z):
        self.coords = (x, y, z)
        self.xy = (x, y)
        self.z = z

    def rotate_x(self, angle):
        x, y, z = self.coords
        rad = radians(angle)
        c = math.cos(rad)
        s = math.sin(rad)
        return point(x, y * c - z * s, y * s + z * c)

    def rotate_y(self, angle):
        x, y, z = self.coords
        rad = radians(angle)
        c = math.cos(rad)
        s = math.sin(rad)
        return point(z * s + x * c, y, z * c - x * s)

    def rotate_z(self, angle):
        x, y, z = self.coords
        rad = radians(angle)
        c = math.cos(rad)
        s = math.sin(rad)
        return point(x * c - y * s, x * s + y * c, z)

    def project(self, size, fov, viewer_distance):
        x, y, z = self.coords
        factor = fov / (viewer_distance + z)
        return point(x * factor + size[0] / 2, -y * factor + size[1] / 2, z)


def sine_wave(min, max, step=1):
    angle = 0
    diff = max - min
    diff2 = diff / 2
    offset = min + diff2
    while True:
        yield angle, offset + math.sin(radians(angle)) * diff2
        angle += step


def run(matrix, config):
    """3D Box"""
    max_y = config["pixel_height"]
    max_x = config["pixel_width"]

    vertices = [
        point(-1, 1, -1),
        point(1, 1, -1),
        point(1, -1, -1),
        point(-1, -1, -1),
        point(-1, 1, 1),
        point(1, 1, 1),
        point(1, -1, 1),
        point(-1, -1, 1),
    ]

    faces = [
        ((0, 1, 2, 3), matrix.color("red")),
        ((1, 5, 6, 2), matrix.color("green")),
        ((0, 4, 5, 1), matrix.color("blue")),
        ((5, 4, 7, 6), matrix.color("magenta")),
        ((4, 0, 3, 7), matrix.color("yellow")),
        ((3, 2, 6, 7), matrix.color("cyan")),
    ]

    a, b, c = 0, 0, 0

    background_color = matrix.color("black")

    while matrix.ready():

        for angle, dist in sine_wave(8, 40, 1.5):
            t = [
                v.rotate_x(a).rotate_y(b).rotate_z(c).project((max_y, max_x), 256, dist)
                for v in vertices
            ]

            depth = []
            for idx, face in enumerate(faces):
                v1, v2, v3, v4 = face[0]
                avg_z = (t[v1].z + t[v2].z + t[v3].z + t[v4].z) / 4.0
                depth.append((idx, avg_z))

            matrix.reset(background_color)
            for idx, depth in sorted(depth, key=itemgetter(1), reverse=True)[3:]:
                (v1, v2, v3, v4), color = faces[idx]

                if angle // 720 % 2 == 0:
                    fill, outline = color, color
                else:
                    fill, outline = matrix.color("black"), matrix.color("white")

                points = []
                points.append((int(t[v1].xy[0]), int(t[v1].xy[1])))
                points.append((int(t[v2].xy[0]), int(t[v2].xy[1])))
                points.append((int(t[v3].xy[0]), int(t[v3].xy[1])))
                points.append((int(t[v4].xy[0]), int(t[v4].xy[1])))

                lines = np.array(points, dtype=np.int32)
                matrix.polyfill([lines], fill)
                matrix.polylines([lines], outline, 1)

            a += 0.3
            b -= 1.1
            c += 0.85
            matrix.show()
