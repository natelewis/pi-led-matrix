def run(matrix, confg):
    step_speed = 30
    def reverse_color(c):
        if c > 255:
            return 255-c
        return c

    while True:
        for red in range(0, 510, step_speed):
            for green in range(0, 510, step_speed):
                for blue in range(0, 510, step_speed):
                    matrix.fill(
                        reverse_color(red),
                        reverse_color(green),
                        reverse_color(blue)
                    )
                    matrix.show()
