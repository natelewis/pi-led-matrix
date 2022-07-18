# size of matrix
PIXEL_WIDTH = 60
PIXEL_HEIGHT = 30

# brightness 0 - 1
BRIGHTNESS = 0.2

#contrast (1 is no change)
CONTRAST = 2

#color (1 is no change)
COLOR = 1.5

# framerate between renderings in milliseconds in virtual mode
# this mimics the delay of hardware latency
VIRTUAL_FRAMERATE = 75 # this is pretty close to a pi 4 processing speed with a 60x30 matrix

PLAYLIST = [
#    {'effect': 'video', 'argv': ['cartoon-60x30.mp4']},
#    {'effect': 'image', 'argv': ['josie-60x30.png']},
    {'effect': 'hallway', 'argv': []},
    {'effect': 'snow', 'argv': []},
    {'effect': 'water_ripple', 'argv':[]},
]
PLAYLIST_DELAY = 30 # in seconds
