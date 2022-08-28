

Raspberry Pi LED Matrix
=========================
WIP -- Place holder for PIP readme -- WIP

A LED Matrix animation and graphics library for use on the Raspberry Pi.   It supports a virtual environment, and can drive a physical LED matrix.
For general details check out the `project repo's readme <https://github.com/natelewis/pi-led-matrix>`_.  You can view examples and public effects made by contributors `here <https://github.com/natelewis/pi-led-matrix/blob/main/effects/README.md>`_.

Installing
============
.. code-block:: bash

    pip3 install pi-led-matrix

Installing on Pi With Physical LED Matrix
===========================================

.. code-block:: bash

    sudo apt update
    sudo apt install -y ffmpeg libatlas-base-dev
    sudo pip3 install --upgrade api-led-matrix adafruit-python-shell rpi_ws281x adafruit-circuitpython-neopixel adafruit_pixel_framebuf
    wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
    sudo python3 raspi-blinka.py

Usage
=====

.. code-block:: bash

    from led_matrix import Matrix
    matrix = Matrix()

    # draw some random things to show how this works
    matrix.reset() # black background (0, 0, 0)
    matrix.line((0, 0), (60, 30), (255, 0, 0),  1) # diagonal red line
    matrix.rectangle((5, 5), (55, 25), (0, 255, 0),  1) # green rectangle
    matrix.circle((30, 15), 10, (0, 0, 255),  2) # blue circle
    matrix.show()
    matrix.delay(10000) # delay 10 seconds before shutting virtual window down

.. image:: https://user-images.githubusercontent.com/1588877/177688122-57a522d4-5d3d-4401-ae9d-464fef425688.png
   :width: 600

Simple Animation
==================
Paint the LED matrix a random color every second:

.. code-block:: bash

    from led_matrix import Matrix
    matrix = Matrix()

    while True:
        matrix.reset(matrix.random_color())
        matrix.show()
        matrix.delay(1000)

For more examples of animations and fun effects `here <https://github.com/natelewis/pi-led-matrix/blob/main/effects/README.md>`_.


