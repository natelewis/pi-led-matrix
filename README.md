# Raspberry Pi LED Matrix Playground

This is a collection of widgets and helpers to drive a LED matrix of any size created with WS2812B LED strips.  To work with this locally without a LED matrix, the library will detect you are not in the live environment and use `cv2` to render the matrix locally.

## Virtual Env setup
You can emulate the LED array locally.  It detects you do not have any of the adafruit modules installed and fails over to virtual mode.  Currently limited to animations only, your event loop must be < 100ms.  If you are not animating you can import the `delay()` function to keep the virtual matrix up.

```bash
pip3 install opencv-python
pip3 install -U numpy
```

## Hardware

Here is the high level construction details of the LED matrix panel.

Shopping List:

* WS2812B LED strips
* 5V power supply
* Raspberry Pi 4
* Extra 3 pin wire @ 22AWG
* Extra JST SM 3 Pin Connectors for extension to where your panel is from the Pi/PSU
* Curtain rod
* Hobby wood/bamboo @ 3/8" wide to stick on the back of the LED strips to keep them straight
* A bit of patience -- Takes about 4-5 hours to put it all together

In this example I built a 60x30 array with 5V 300W 60A power supply:

1. Collect a 60 count of 30 LED per meter 1M strips
2. Build the matrix in a chain pattern:

```text
_   _   _   _ ...
 | | | | | |
 | | | | | |
 | | | | | |
 | | | | | |
 | | | | | |
 |_| |_| |_|
```

1. Attach power to every other strip in parallel

2. Connect GPIO 18 of the RPi4 to the green LED wire
3. Connect GND pin of the RPi4 to COM of the power supply
4. Hang the LED strips to the curtain rod with your adhesive of choice
5. Stick the wood to the back of the strips to keep them from bending around


## Raspberry Pi setup
1. Install RPi OS 32 bit
2. Get your Pi on your network, running headless and pull down this repo
3. Execute the following to globally install libraries and dependencies:

```bash
sudo apt update
sudo apt install -y ffmpeg
sudo pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
sudo python3 raspi-blinka.py
sudo pip3 install rpi_ws281x adafruit-circuitpython-neopixel
sudo python3 -m pip install --force-reinstall adafruit-blinka
sudo pip3 install opencv-python
sudo pip3 install -U numpy
sudo apt-get install libatlas-base-dev
```

1. Update the `config.py` to adjust sizes, delays, and pin configuration.

## Test hardware

Running the test script will cycle between R..., G..., B... (repeat)

```bash
sudo python3 test.py
```

## Playing videos

To play a video first resize the video before playing with `ffmpeg` to the size of your matrix:

```bash
ffmpeg -i filename.mp4 -vf scale=60:30 filename-60x30.mp4
```

To play the video on the matrix:

```bash
sudo python3 video.py filename.mp4
```

## Displaying an image

Resize the image in any graphic editor to the size of the matrix and save it as a PNG.

```bash
sudo python3 image.py image.png
```

## Scrolling Marquee

This only works in live -- not currently compatible with virtual env

```bash
sudo python3 marquee.py 'Message Here'
```

## API

The API consist of [cv2 drawing functions](https://docs.opencv.org/4.x/dc/da5/tutorial_py_drawing_functions.html) and a few extras that mimic some helpful function in the adafruit libraries.

### led_matrix.fill(r, g, b):
Fill all the pixels with the r/g/b values given.

```python
fill(0, 0, 0) # turn off all LEDs
fill(255, 0 , 0) # all LEDs red
```

img = np.zeros((512,512,3), np.uint8)

## Contributing

Checkout [CONTRIBUTING.md](CONTRIBUTING.md)

---

Created by [@natelewis](https://github.com/natelewis). Released under the MIT license.
