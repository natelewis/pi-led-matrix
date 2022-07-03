# Raspberry Pi LED Matrix Playground

This is a collection of examples and a API wrapper to simplify driving a LED matrix of any size created with WS2812B LED strips.  To work with this locally without a LED matrix, the library will detect you are not in the live environment and render the matrix locally.

## Virtual Env setup

When emulating the LED array locally, it detects you do not have any of the adafruit modules installed and fails over to virtual mode.  When building your event loop for animations they must be no less than 100ms.  If you are not animating and wish to keep your virtual LED image up use the `delay(ms)`.

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

# API

```python
from led_matrix import matrix
matrix.fill(0,0,0) # black background

matrix.show()
matrix.delay(1000)
```

`framebuffer.delay(ms)`

---

Sleep x amount of milliseconds

```python
matrix.delay(1000) # 1 second
matrix.delay(1000 * 60) # 1 minute
```

<br/>

`matrix.enhance()`

---

Apply the color, contrast, and brightness setting from the config to the current frame.

```python
matrix.enhance()
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

`framebuffer.line((x,y), (x,y), (r, g, b), width)`

---

Draw a line from the start to then end coordinates.

```python
matrix.line((0, 0), (60, 30), (255, 0, 0),  1) # diagonal red line
```

<br/>

`matrix.show()`

---

Paint the current image to the LEDs

```python
matrix.fill(0, 0, 0)
matrix.show() # turn off all LEDs
```

<br/>

## Contributing

Checkout [CONTRIBUTING.md](CONTRIBUTING.md)

---

Created by [@natelewis](https://github.com/natelewis). Released under the MIT license.
