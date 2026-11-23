# Headless Raspberry Pi Deployment (`systemd`)

Use these unit files to run the LED matrix playlist runner and the Studio web API automatically on boot so you can control your Pi from your Mac or phone on the local network.

## Setup on the Raspberry Pi

1. Adjust `/home/pi/pi-led-matrix` and `User=`/`Group=` in both `.service` files if your username or repo path differs from `pi`.
2. Ensure `_runtime/` exists with group-write permissions so `root` (GPIO NeoPixels) and `pi` (web server) share IPC files cleanly:

```bash
mkdir -p /home/pi/pi-led-matrix/_runtime
sudo chown pi:pi /home/pi/pi-led-matrix/_runtime
chmod 2775 /home/pi/pi-led-matrix/_runtime
```

3. *(Optional)* If you want a fixed Studio password managed via env file rather than first-run web setup, create a `0600` env file and uncomment `EnvironmentFile=` in `pi-led-matrix-web.service`:

```bash
echo 'LED_MATRIX_PASSWORD=your-strong-password' | sudo tee /etc/pi-led-matrix-web.env >/dev/null
sudo chown pi:pi /etc/pi-led-matrix-web.env
sudo chmod 600 /etc/pi-led-matrix-web.env
```

4. Install and enable the services:

```bash
sudo cp deploy/systemd/pi-led-matrix.service /etc/systemd/system/
sudo cp deploy/systemd/pi-led-matrix-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pi-led-matrix-web.service
sudo systemctl enable --now pi-led-matrix.service
```

> **Note on Stop / Start with GPIO hardware:** Because NeoPixel GPIO requires `root`, `pi-led-matrix.service` runs as `root` while `pi-led-matrix-web.service` runs as `pi`. Live **Skip**, **Play Now**, **Live Mirror**, and **Save Config** hot-reload work out of the box across both services. If you click **Stop** in Studio, `pi-led-matrix.service` exits cleanly (`0`); to restart it from the Pi run `sudo systemctl start pi-led-matrix.service` (or switch the service to `Restart=always` / add a narrow `sudoers` rule if you want automatic restart).

5. Check status and logs:

```bash
systemctl status pi-led-matrix-web pi-led-matrix
journalctl -u pi-led-matrix-web -f
```

6. Connect from LED Matrix Studio on your Mac:
   - Open **Devices & Remote** in your local Mac Studio.
   - Add your Pi (e.g. `http://raspberrypi.local:8080` or `http://192.168.1.x:8080`), sign in, and switch to it.

## Raspberry Pi Desktop / HDMI Virtual Display (`virtual: true`)

If your Raspberry Pi displays the matrix fullscreen on an attached HDMI screen via Pygame (rather than root-only GPIO NeoPixels), run `pi-led-matrix-web.service` as your desktop user (e.g. `nlewis`) and pass the desktop session display variables so Pygame can take over the screen:

```ini
[Unit]
Description=Raspberry Pi LED Matrix Studio Web Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=nlewis
Group=nlewis
UMask=0002
WorkingDirectory=/home/nlewis/pi-led-matrix
ExecStart=/home/nlewis/pi-led-matrix/.venv/bin/python -m web.server.app --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=3
Environment=PYTHONUNBUFFERED=1
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=WAYLAND_DISPLAY=wayland-1
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/nlewis/.Xauthority
EnvironmentFile=/etc/pi-led-matrix-web.env

[Install]
WantedBy=multi-user.target
```

> **Tip:** Check `ls /run/user/$(id -u)/wayland*` on your Pi to confirm whether Wayfire/labwc is using `wayland-0` or `wayland-1`, and ensure `/etc/pi-led-matrix-web.env` and `_runtime/` are owned by your desktop user.
