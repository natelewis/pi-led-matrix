#
# Let's play a game of tic tac toe!
# 15 September 2022
#
#     0   1    2
# 0  ul | um | ur
#   -------------
# 1  ml | mm | mr
#   -------------
# 2  ll | lm | lr
#

import random

WIN_LINES = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (6, 4, 2),
]


def build_layout(width, height):
    """compute centered board geometry scaled to the matrix"""
    x_mid = width // 2
    y_mid = height // 2
    cell = max(4, (min(width, height) - 2) // 3)
    half_board = (cell * 3) // 2
    squares = [
        (x_mid + col * cell, y_mid + row * cell)
        for row in (-1, 0, 1)
        for col in (-1, 0, 1)
    ]
    return {
        "x_mid": x_mid,
        "y_mid": y_mid,
        "cell": cell,
        "half_board": half_board,
        "squares": squares,
        "o_radius": max(2, int(cell * 0.32)),
        "x_half": max(2, int(cell * 0.28)),
        "thickness": max(1, cell // 10),
    }


def draw_board(matrix, layout, color):
    """draw centered 3x3 tic tac toe grid"""
    x_mid = layout["x_mid"]
    y_mid = layout["y_mid"]
    half_cell = layout["cell"] // 2
    half_board = layout["half_board"]
    thickness = layout["thickness"]

    matrix.line(
        (x_mid - half_cell, y_mid - half_board),
        (x_mid - half_cell, y_mid + half_board),
        color,
        thickness,
    )
    matrix.line(
        (x_mid + half_cell, y_mid - half_board),
        (x_mid + half_cell, y_mid + half_board),
        color,
        thickness,
    )
    matrix.line(
        (x_mid - half_board, y_mid - half_cell),
        (x_mid + half_board, y_mid - half_cell),
        color,
        thickness,
    )
    matrix.line(
        (x_mid - half_board, y_mid + half_cell),
        (x_mid + half_board, y_mid + half_cell),
        color,
        thickness,
    )


def draw_mark(matrix, layout, coord, player, color):
    """draw X or O at a square center"""
    x, y = coord
    thickness = layout["thickness"]
    if player == "X":
        half = layout["x_half"]
        matrix.line((x - half, y - half), (x + half, y + half), color, thickness)
        matrix.line((x - half, y + half), (x + half, y - half), color, thickness)
    elif player == "O":
        matrix.circle((x, y), layout["o_radius"], color, thickness)


def run(matrix, config):
    """tic tac toe"""
    colors = {
        "grid": matrix.color("white"),
        "mark": matrix.color("white"),
        "win": matrix.color("red"),
        "bg": matrix.color("black"),
    }
    layout = build_layout(config["pixel_width"], config["pixel_height"])
    board = [None] * 9
    active_player = "X"

    def celebrate_winner(player, indices):
        for _ in range(5):
            for idx in indices:
                draw_mark(matrix, layout, layout["squares"][idx], player, colors["bg"])
            matrix.show()
            matrix.delay(500)
            for idx in indices:
                draw_mark(matrix, layout, layout["squares"][idx], player, colors["win"])
            matrix.show()
            matrix.delay(500)

    def find_winner(player):
        for line in WIN_LINES:
            if all(board[idx] == player for idx in line):
                celebrate_winner(player, line)
                return True
        return False

    while matrix.ready():
        matrix.reset()
        draw_board(matrix, layout, colors["grid"])

        open_indices = [idx for idx, val in enumerate(board) if val is None]
        board[random.choice(open_indices)] = active_player

        for idx, player in enumerate(board):
            if player is not None:
                draw_mark(
                    matrix, layout, layout["squares"][idx], player, colors["mark"]
                )

        matrix.show()
        matrix.delay(1000)

        if find_winner(active_player):
            print(f"Player {active_player} wins!")
            matrix.delay(3000)
            board = [None] * 9
        elif None not in board:
            print("No winner!?!")
            matrix.delay(3000)
            board = [None] * 9

        active_player = "O" if active_player == "X" else "X"
