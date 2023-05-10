# Simple test to confirm color
# Red... Green... Blue... (Repeat)
def run(matrix, config):
    """red, green, blue, repeat"""
    while matrix.ready():
        matrix.reset(matrix.color('red'))
        matrix.show()
        matrix.delay(1000)

        matrix.reset(matrix.color('green'))
        matrix.show()
        matrix.delay(1000)

        matrix.reset(matrix.color('blue'))
        matrix.show()
        matrix.delay(1000)
