# Simple test to confirm color
# Red... Green... Blue... (Repeat)
from led_matrix import Matrix

matrix = Matrix()

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
