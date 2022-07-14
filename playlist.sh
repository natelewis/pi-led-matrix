# only supports mac/linux and pi
ENV_TYPE=$(uname -m)
if [ $ENV_TYPE = "armv7l" ]; then
    echo Running on Raspberry Pi
    sudo python3 effect_playlist.py "$@"
else
    echo Running on $ENV_TYPE
    python3 effect_playlist.py "$@"
fi
