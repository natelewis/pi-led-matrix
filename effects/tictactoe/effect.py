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

#
# ./run.sh tictactoe
#
def run(matrix, config):
    """ tic tac toe """

    grid_color = matrix.color('white')
    x_color = matrix.color('white')
    o_color = matrix.color('white')
    win_color = matrix.color('red')
    background_color = matrix.color('black')

    x_min = 0
    y_min = 0
    x_max = config['pixel_width']
    y_max = config['pixel_height']
    x_mid = round(x_max / 2)
    y_mid = round(y_max / 2)

    # Blocks in the grid
    upper_left = (x_mid - 10, y_mid - 10)
    upper_mid = (x_mid, y_mid - 10)
    upper_right = (x_mid + 10, y_mid - 10)
    mid_left = (x_mid - 10, y_mid)
    mid_mid = (x_mid, y_mid)
    mid_right = (x_mid + 10, y_mid)
    lower_left = (x_mid - 10, y_mid + 10)
    lower_mid = (x_mid, y_mid + 10)
    lower_right = (x_mid + 10, y_mid + 10)

    all_squares = [upper_left, upper_mid, upper_right, mid_left, mid_mid, mid_right, lower_left, lower_mid, lower_right]

    win_states = [
        [upper_left, upper_mid, upper_right],
        [mid_left, mid_mid, mid_right],
        [lower_left, lower_mid, lower_right],
        [upper_left, mid_left, lower_left],
        [upper_mid, mid_mid, lower_mid],
        [upper_right, mid_right, lower_right],
        [upper_left, mid_mid, lower_right],
        [lower_left, mid_mid, upper_right]
    ]

    player_grid = {}
    for block in all_squares:
        player_grid[block] = None

    left_line = x_mid - 5
    right_line = x_mid + 5
    top_line = y_mid - 5
    bottom_line = y_mid + 5

    active_player = 'X'

    def clear_grid():
        for block in all_squares:
            player_grid[block] = None

    def draw_board():
        matrix.line((left_line, y_min), (left_line, y_max), grid_color, 1)
        matrix.line((right_line, y_min), (right_line, y_max),grid_color, 1)
        matrix.line((x_mid - 15, top_line), (x_mid + 15, top_line), grid_color, 1)
        matrix.line((x_mid - 15, bottom_line), (x_mid + 15, bottom_line), grid_color, 1)

    def draw_oh(coord, color=o_color):
        x, y = coord
        matrix.circle((x, y), 3, color, 1)

    def draw_ex(coord, color=x_color):
        x, y = coord
        matrix.line((x - 2, y - 2), (x + 2, y + 2), color, 1)
        matrix.line((x - 2, y + 2), (x + 2, y - 2), color, 1)

    def is_full():
        if None not in player_grid.values():
            return True
        else:
            return False

    def draw_players():
        for block, player in player_grid.items():
            if player == 'X':
                draw_ex(block)
            elif player == 'O':
                draw_oh(block)

    def player_move():
        open_blocks = []
        for block, player in player_grid.items():
            if player == None:
                open_blocks.append(block)
        return random.choice(open_blocks)

    def celebrate_winner(player, blocks):
        for _ in range(5):
            for coord in blocks:
                if player == 'X':
                    draw_ex(coord, background_color)
                else:
                    draw_oh(coord, background_color)
            matrix.show()
            matrix.delay(500)
            for coord in blocks:
                if player == 'X':
                    draw_ex(coord, win_color)
                else:
                    draw_oh(coord, win_color)
            matrix.show()
            matrix.delay(500)

    def is_winner(player):
        for blocks in win_states:
            if player_grid[blocks[0]] == active_player and player_grid[blocks[1]] == active_player and player_grid[blocks[2]] == active_player:
                celebrate_winner(player, blocks)
                return True
        return False                    

    clear_grid()

    while matrix.good_to_go():
        matrix.reset()

        draw_board()

        # Player makes a move
        # TODO: Use the win_states to help decide the next move.
        player_grid[player_move()] = active_player

        draw_players()
        
        matrix.show()
        matrix.delay(1000)

        if is_winner(active_player):
            print(f"Player {active_player} wins!")
            matrix.delay(3000)
            clear_grid()
        
        if is_full():
            print('No winner!?!')
            matrix.delay(3000)
            clear_grid()

        # Next player
        if active_player == 'X':
            active_player = 'O'
        else:
            active_player = 'X'
