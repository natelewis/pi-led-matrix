# Simple test to confirm color
# Red... Green... Blue... (Repeat)
def run(matrix, config):
    """red, green, blue, repeat"""
    while True:
        matrix.fill(255, 0, 0)
        matrix.show()
        matrix.delay(1000)

        matrix.fill(0, 255, 0)
        matrix.show()
        matrix.delay(1000)

        matrix.fill(0, 0, 255)
        matrix.show()
        matrix.delay(1000)
