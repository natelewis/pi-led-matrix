# Simple test to confirm color
# Red... Green... Blue... (Repeat)
def run(matrix, _):
    """red, green, blue, repeat"""
    while matrix.ready():
        matrix.reset()
        matrix.text("R E D", (0, 0), 10, (255, 0, 0))
        matrix.show()
        matrix.delay(1000)

        matrix.reset()
        matrix.text("G R E E N", (0, 0), 10, (0, 255, 0))
        matrix.show()
        matrix.delay(1000)

        matrix.reset()
        matrix.text("B L U E", (0, 0), 10, (0, 0, 255))
        matrix.show()
        matrix.delay(1000)
