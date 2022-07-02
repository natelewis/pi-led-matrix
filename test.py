# Simple test for NeoPixels on Raspberry Pi
# Red... Green... Blue... (Repeat)
from led_matrix import framebuffer, delay

framebuf = framebuffer()

while True:
    framebuf.fill(255, 0, 0)
    framebuf.display()
    delay(1000)

    framebuf.fill(0, 255, 0)
    framebuf.display()
    delay(1000)

    framebuf.fill(0, 0, 255)
    framebuf.display()
    delay(1000)
