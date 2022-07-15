
# Raspberry Pi LED Matrix Effects

List of current contributed effects that can be run.  They can be loaded and ran individually with the `run.sh` script:

```bash
./run.sh effect_name
```

or loaded at random from a configurable list in `config.py` with:

```bash
./playlist.sh
```

To make a new effect, just copy an existing effect directory that might have some common code and alter its contents.  You'll see there is a `run()` function that receives a `matrix` and `config` argument.  The `config` dictionary will have:

* pixel_width
* pixel_height
* effect_directory
* argv (applicable only to `run.sh` -- being the arguments passed to the effect from the command line)

## hallway

Effect of moving down a hallway.

## image image.png

Resize the image in any graphic editor to the size of the matrix and save it as a PNG.  Place image in the `image` effect directory.

## marquee

This currently is set for matrix's at 60x30, and in red.  Change the settings in the effect script to alter.

## off

Simple effect that sets all lights to black.

## snow

Simple snow effect.

## snow_flakes

Complex snow flakes using animated sprites and shimmering brightness.

## rgb_test

Test that checks your RGB configuration.  Red... Blue... Green... (repeat)

## video filename.mp4

To play a video, first resize the video with `ffmpeg` to the size of your matrix:

```bash
ffmpeg -i filename.mp4 -vf scale=60:30 filename-60x30.mp4
```

Copy the video to the `video` effect directory to play.

## water_ripple

Blue circle animation that resembles water ripples.

---

Created by [@natelewis](https://github.com/natelewis). Released under the MIT license.
