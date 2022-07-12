
# Raspberry Pi LED Matrix Effects

This is the list of current contributed effects that can be run.  They can be loaded be ran individually with the `run.sh` script:

```bash
./run.sh effect_name
```

To make a new effect, just copy an existing effect directory  that might have some common code and alter its contents.  You'll see there is a `run()` function that receives a `matrix` and `config` argument.  The `config` dictionary will have:
* pixel_width
* pixel_height
* effect_directory

## hallway

Effect of moving down a hallway

```bash
./run.sh hallway
```

## image

Resize the image in any graphic editor to the size of the matrix and save it as a PNG.  Place image in the image effect directory.

```bash
./run.sh image image.png
```

## marquee

This currently is set for matrix's at 60x30, and in red.  Change the settings in the effect script to alter.

```bash
./run.sh marquee 'Message Here'
```

## off

Simple effect that sets all lights to black

```bash
./run.sh off
```

## snow

Simple snow effect.

```bash
./run.sh snow
```

## rgb_test

Test that checks your RGB configuration.  Red... Blue... Green... (repeat)

```bash
./run.sh rgb_test
```

## video

To play a video first resize the video before playing with `ffmpeg` to the size of your matrix:

```bash
ffmpeg -i filename.mp4 -vf scale=60:30 filename-60x30.mp4
```

To play the video on the matrix with the `mp4` file copied to the video effect directory

```bash
./run.sh video filename.mp4
```

## water_ripple

Blue circle animation that resembles water ripples.

```bash
./run.sh water_ripple
```


---

Created by [@natelewis](https://github.com/natelewis). Released under the MIT license.
