# Raspberry Pi LED Matrix Playground

This is a collection of examples and an API wrapper to simplify driving a LED matrix of any size created with WS2812B LED strips.  To tinker locally without a LED matrix, the library will detect you are not in the live environment and render the matrix in a window on your local machine.

## Virtual environment quick start

```bash
git clone git@github.com:natelewis/pi-led-matrix-playground.git
cd pi-led-matrix-playground
pip3 install opencv-python
pip3 install -U numpy
python3 test.py
```

## Hardware

Here is the high level construction details of the LED matrix panel.

Shopping List:

* WS2812B LED strips
* 5V power supply
* Raspberry Pi 4
* Extra 3 pin wire @ 22AWG
* A few Male/Female JST SM 3 Pin Connectors to create an extension cable from where your panel is to your Pi/PSU
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

## Testing your LED matrix

Running the test script will cycle between R..., G..., B... (repeat)

```bash
sudo python3 test.py
```

## Displaying an image on your LED matrix

Resize the image in any graphic editor to the size of the matrix and save it as a PNG.

```bash
sudo python3 image.py image.png
```

## Playing videos on your LED matrix

To play a video first resize the video before playing with `ffmpeg` to the size of your matrix:

```bash
ffmpeg -i filename.mp4 -vf scale=60:30 filename-60x30.mp4
```

To play the video on the matrix:

```bash
sudo python3 video.py filename.mp4
```

## Scrolling Marquee

This only works in live -- not currently compatible with virtual env

```bash
sudo python3 marquee.py 'Message Here'
```

# API

When emulating the LED array locally, it detects you do not have any of the adafruit modules installed and fails over to virtual mode.  To pause your event loop when animating use the `matrix.delay()` function.  This will ensure your rendering window stays open.

```python
from led_matrix import matrix
matrix.fill(0,0,0) # black background

matrix.show()
matrix.delay(1000)
```

`matrix.delay(ms)`

---

Sleep x amount of milliseconds.

```python
matrix.delay(1000) # 1 second
matrix.delay(1000 * 60) # 1 minute
```

<br/>

`matrix.fill(r, g, b)`

---

Fill all the pixels with the RGB values given.

```python
matrix.fill(0, 0, 0) # turn off all LEDs
matrix.fill(255, 0 , 0) # all LEDs red
```

<br/>

`matrix.image(Image)`

---

Display an image using the Python Imaging Library (PIL).

```python
from PIL import Image
image = Image.open(image_file)
matrix.image(image)
matrix.show()
```

<br/>

`matrix.line((x,y), (x,y), (r, g, b), width)`

---

Draw a line from the start to then end coordinates.

```python
matrix.line((0, 0), (60, 30), (255, 0, 0),  1) # diagonal red line
```

<br/>

`matrix.rectangle((x,y), (x,y), (r, g, b), width)`

---

Draw a rectangle from the start to then end coordinates.

```python
matrix.line((5, 5), (55, 25), (255, 0, 0),  1) # diagonal red line
```
<br/>

`matrix.show()`

---

Paint the current image to the LEDs

```python
matrix.fill(0, 0, 255)
matrix.show() # turn all LEDs blue
matrix.delay(1000)
matrix.fill(0, 0, 0)
matrix.show() # turn off all LEDs

```

<br/>

## Contributing

Checkout [CONTRIBUTING.md](CONTRIBUTING.md)

---

Created by [@natelewis](https://github.com/natelewis). Released under the MIT license.
