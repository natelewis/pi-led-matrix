# size of matrix
pixel_width = 60
pixel_height = 30

# brightness 0 - 1
brightness = 0.2

#contrast (1 is no change)
contrast = 2

#color (1 is no change)
color = 1.5

# framerate between renderings in milliseconds in virtual mode
# this mimics the delay of hardware latency
virtual_framerate = 75 # this is pretty close to a raspi 4 processing speed with a 60x30 matrix

playlist = [
#    {'effect': 'video', 'argv': ['cartoon-60x30.mp4']},
#    {'effect': 'image', 'argv': ['josie-60x30.png']},
    {'effect': 'hallway', 'argv': []},
    {'effect': 'snow', 'argv': []},
    {'effect': 'water_ripple', 'argv':[]}
]
playlist_delay = 30 # in seconds
