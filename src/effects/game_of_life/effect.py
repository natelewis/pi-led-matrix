#
# Game of Life
# Ported from https://github.com/rm-hull/luma.examples/blob/main/examples/game_of_life.py
# 25 February 2025
#

import time
from random import randint


def neighbors(cell):
    x, y = cell
    yield x - 1, y - 1
    yield x, y - 1
    yield x + 1, y - 1
    yield x - 1, y
    yield x + 1, y
    yield x - 1, y + 1
    yield x, y + 1
    yield x + 1, y + 1


def iterate(board):
    new_board = set([])
    candidates = board.union(set(n for cell in board for n in neighbors(cell)))
    for cell in candidates:
        count = sum((n in board) for n in neighbors(cell))
        if count == 3 or (count == 2 and cell in board):
            new_board.add(cell)
    return new_board


def run(matrix, config):
    """Game of Life"""
    text = "Game of Life"
    scale = 1
    cols = config["pixel_width"] // scale
    rows = config["pixel_height"] // scale
    initial_population = int(cols * rows * 0.33)
    background_color = matrix.color("black")

    while matrix.ready():
        board = set(
            (randint(0, cols), randint(0, rows)) for _ in range(initial_population)
        )

        for i in range(500):
            matrix.reset(background_color)
            for x, y in board:
                left = x * scale
                top = y * scale
                if scale == 1:
                    matrix.pixel((left, top), matrix.color("white"))
                else:
                    right = left + scale
                    bottom = top + scale
                    matrix.rectangle(
                        (left, top), (right, bottom), matrix.color("white"), 1
                    )

            matrix.show()
            board = iterate(board)
