# only supports mac/linux and pi
echo Loading effect...

if [ $(uname -m) = "armv6l" ]; then
    # pi
    sudo python3 load_effect.py "$@"
else
    # mac/linux
    python3 load_effect.py "$@"
fi