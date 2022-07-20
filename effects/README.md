
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

Resize the image in any graphic editor to the size of the matrix and save it as a PNG.  Place image in the `image` effect directory.  Fonts usually have some padding and such, so you sometimes have to adjust for that on the 'y' settings.

## marquee

Passing sets of definition can create any type of marquee.
```
# ./run.sh marquee left_padding right_padding r g b "my message" ..repeat'
# example of:
#     The
#        Beverly
# ./run.sh marquee 0 -5 0 0 255 'The' 25 9 0 0 255 'Beverly'
# notice the -5 for the first `y`.  This subtracts some padding the default font has.
```

## off

Simple effect that sets all lights to black.

## pong

Simulates a pong game

https://user-images.githubusercontent.com/1588877/180089226-94fc8646-5f0d-4173-a96a-8605a65c4c78.mov

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
