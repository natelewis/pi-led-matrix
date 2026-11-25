"""Unit and integration tests for the pi-led-matrix web server."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from web.server.app import create_server
from web.server.media import inspect_png_header, probe_video_metadata


REPO_ROOT = Path(__file__).resolve().parents[3]


class WebServerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_quiet = os.environ.get("LED_MATRIX_WEB_QUIET")
        os.environ["LED_MATRIX_WEB_QUIET"] = "1"
        self.tmpdir = Path(tempfile.mkdtemp(prefix="led_matrix_web_test_"))
        shutil.copy2(REPO_ROOT / "default_config.json", self.tmpdir / "default_config.json")
        # Mirror src/effects and fonts for discovery
        shutil.copytree(REPO_ROOT / "src" / "effects", self.tmpdir / "src" / "effects")
        shutil.copytree(REPO_ROOT / "fonts", self.tmpdir / "fonts")

        static_dir = self.tmpdir / "web" / "client" / "dist"
        static_dir.mkdir(parents=True)
        (static_dir / "index.html").write_text("<!doctype html><html><body>OK</body></html>", encoding="utf-8")

        self.server = create_server(
            "127.0.0.1",
            0,
            repo_root=self.tmpdir,
            static_dir=static_dir,
            auth_file=self.tmpdir / "web" / ".auth.json",
            targets_file=self.tmpdir / "web" / ".targets.json",
            env_password="",
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self._prev_quiet is None:
            os.environ.pop("LED_MATRIX_WEB_QUIET", None)
        else:
            os.environ["LED_MATRIX_WEB_QUIET"] = self._prev_quiet

    def _request(
        self,
        method: str,
        path: str,
        body: object = None,
        cookie: str = "",
    ):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if cookie:
            headers["Cookie"] = cookie
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                raw_bytes = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return resp.status, dict(resp.headers), json.loads(raw_bytes.decode("utf-8"))
                if content_type.startswith("text/"):
                    return resp.status, dict(resp.headers), raw_bytes.decode("utf-8")
                return resp.status, dict(resp.headers), raw_bytes
        except urllib.error.HTTPError as err:
            raw_bytes = err.read()
            raw_text = raw_bytes.decode("utf-8", errors="replace")
            return err.code, dict(err.headers), json.loads(raw_text) if raw_text.startswith("{") else raw_text

    def _extract_cookie(self, headers: dict) -> str:
        set_cookie = headers.get("Set-Cookie", "")
        return set_cookie.split(";", 1)[0]

    def test_auth_setup_login_config_and_validation(self) -> None:
        # Uninitialized status
        status, _, body = self._request("GET", "/api/auth/status")
        self.assertEqual(status, 200)
        self.assertFalse(body["initialized"])
        self.assertFalse(body["authenticated"])

        # Protected route rejects unauthenticated requests
        status, _, _ = self._request("GET", "/api/config")
        self.assertEqual(status, 401)

        # First-run password setup returns HttpOnly cookie
        status, headers, body = self._request(
            "POST", "/api/auth/setup", {"password": "secret-password"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["authenticated"])
        self.assertIn("HttpOnly", headers.get("Set-Cookie", ""))
        cookie = self._extract_cookie(headers)

        # Config loads from default_config.json initially
        status, _, cfg_resp = self._request("GET", "/api/config", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(cfg_resp["source"], "default")
        self.assertEqual(cfg_resp["config"]["pixel_width"], 128)
        self.assertEqual(cfg_resp["config"]["pixel_height"], 72)

        # Discover effects & fonts
        status, _, fx_resp = self._request("GET", "/api/effects", cookie=cookie)
        self.assertEqual(status, 200)
        effect_ids = {e["id"] for e in fx_resp["effects"]}
        self.assertIn("hallway", effect_ids)
        self.assertIn("marquee", effect_ids)
        self.assertIn("dosis.ttf", fx_resp["fonts"])

        # Validation catches invalid fields
        bad_cfg = dict(cfg_resp["config"])
        bad_cfg["brightness"] = 5.0
        bad_cfg["pixel_pins"] = ["D99"]
        status, _, err_resp = self._request("PUT", "/api/config", {"config": bad_cfg}, cookie=cookie)
        self.assertEqual(status, 422)
        self.assertIn("brightness", err_resp["fields"])
        self.assertIn("pixel_pins", err_resp["fields"])

        # Valid update writes config.json atomically
        updated_cfg = dict(cfg_resp["config"])
        updated_cfg["brightness"] = 0.45
        updated_cfg["playlist_delay"] = 30
        updated_cfg["playlist"] = [
            {"effect": "snow"},
            {"effect": "marquee", "config": {"messages": [{"left": 0, "right": 5, "r": 255, "g": 0, "b": 0, "message": "Hi", "font": "dosis.ttf"}]}},
        ]
        status, _, saved = self._request("PUT", "/api/config", {"config": updated_cfg}, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(saved["source"], "custom")
        self.assertAlmostEqual(saved["config"]["brightness"], 0.45)
        self.assertEqual(len(saved["config"]["playlist"]), 2)
        self.assertTrue((self.tmpdir / "config.json").exists())

        # Password change rotates session cookie
        status, headers, _ = self._request(
            "POST",
            "/api/auth/change-password",
            {"currentPassword": "secret-password", "newPassword": "new-password"},
            cookie=cookie,
        )
        self.assertEqual(status, 200)
        new_cookie = self._extract_cookie(headers)
        # Old cookie invalidated
        status, _, _ = self._request("GET", "/api/config", cookie=cookie)
        self.assertEqual(status, 401)
        # New cookie works
        status, _, _ = self._request("GET", "/api/config", cookie=new_cookie)
        self.assertEqual(status, 200)

        # Logout clears cookie and SPA serves index.html
        status, headers, _ = self._request("POST", "/api/auth/logout", {}, cookie=new_cookie)
        self.assertEqual(status, 200)
        self.assertIn("Max-Age=0", headers.get("Set-Cookie", ""))

        status, _, html = self._request("GET", "/playlist")
        self.assertEqual(status, 200)
        self.assertIn("<body>OK</body>", html)

    def test_image_upload_rgba_png_and_uploads_management(self) -> None:
        _, headers, _ = self._request(
            "POST", "/api/auth/setup", {"password": "secret-password"}
        )
        cookie = self._extract_cookie(headers)

        # Create a 128x72 RGBA buffer (cyan pixels with alpha=255)
        width, height = 128, 72
        rgba = bytes([0, 220, 255, 255]) * (width * height)
        rgba_b64 = base64.b64encode(rgba).decode("ascii")

        status, _, resp = self._request(
            "POST",
            "/api/effects/image/upload",
            {
                "filename": "My Cool Photo!.jpg",
                "width": width,
                "height": height,
                "rgbaBase64": rgba_b64,
            },
            cookie=cookie,
        )
        self.assertEqual(status, 201)
        rel_file = resp["image"]["file"]
        self.assertEqual(rel_file, "_uploads/my_cool_photo_128x72.png")

        saved_path = self.tmpdir / "src" / "effects" / "image" / rel_file
        self.assertTrue(saved_path.is_file())
        header = inspect_png_header(saved_path.read_bytes())
        # Verify exact dimensions and color_type=6 (RGBA) for image/effect.py compatibility
        self.assertEqual(header, (128, 72, 6))

        # Effect discovery lists the uploaded file under _uploads/
        status, _, fx_resp = self._request("GET", "/api/effects", cookie=cookie)
        self.assertEqual(status, 200)
        image_fx = next(e for e in fx_resp["effects"] if e["id"] == "image")
        self.assertIn(rel_file, image_fx["availableFiles"])

        # Preview endpoint serves PNG bytes
        qs = urllib.parse.urlencode({"file": rel_file})
        status, resp_headers, png_bytes = self._request(
            "GET", f"/api/effects/image/file?{qs}", cookie=cookie
        )
        self.assertEqual(status, 200)
        self.assertEqual(resp_headers.get("Content-Type"), "image/png")
        self.assertEqual(inspect_png_header(png_bytes), (128, 72, 6))

        # Path traversal is rejected
        bad_qs = urllib.parse.urlencode({"file": "../../default_config.json"})
        status, _, _ = self._request("GET", f"/api/effects/image/file?{bad_qs}", cookie=cookie)
        self.assertEqual(status, 400)

        # Deleting a non-media file (e.g. effect.py) is rejected
        bad_del_qs = urllib.parse.urlencode({"file": "effect.py"})
        status, _, _ = self._request(
            "DELETE", f"/api/effects/image/file?{bad_del_qs}", cookie=cookie
        )
        self.assertEqual(status, 400)

        # Hidden macOS AppleDouble dotfiles are excluded from media listing
        (self.tmpdir / "src" / "effects" / "image" / "._hidden.png").write_bytes(png_bytes)
        status, _, listed_after_hidden = self._request(
            "GET", "/api/effects/image/files", cookie=cookie
        )
        self.assertEqual(status, 200)
        self.assertFalse(
            any(item["name"].startswith(".") for item in listed_after_hidden["files"])
        )

        # Deleting a root-level media image in src/effects/image/ succeeds
        root_img = self.tmpdir / "src" / "effects" / "image" / "root.png"
        root_img.write_bytes(png_bytes)
        root_qs = urllib.parse.urlencode({"file": "root.png"})
        status, _, root_del = self._request(
            "DELETE", f"/api/effects/image/file?{root_qs}", cookie=cookie
        )
        self.assertEqual(status, 200)
        self.assertEqual(root_del["deleted"], "root.png")
        self.assertFalse(root_img.is_file())

        # Deleting the uploaded file succeeds
        status, _, del_resp = self._request(
            "DELETE", f"/api/effects/image/file?{qs}", cookie=cookie
        )
        self.assertEqual(status, 200)
        self.assertEqual(del_resp["deleted"], rel_file)
        self.assertFalse(saved_path.is_file())

    def test_video_upload_transcode_range_and_delete(self) -> None:
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not installed")

        _, headers, _ = self._request(
            "POST", "/api/auth/setup", {"password": "secret-password"}
        )
        cookie = self._extract_cookie(headers)

        # Generate a tiny 1-second 320x240 MP4 clip in temp dir
        sample_mp4 = self.tmpdir / "sample_source.mp4"
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=1:size=320x240:rate=15",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(sample_mp4),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        video_bytes = sample_mp4.read_bytes()

        # Upload with smart-crop coordinates to resize 320x240 -> 128x72
        params = urllib.parse.urlencode(
            {
                "filename": "Demo Clip!.mp4",
                "width": 128,
                "height": 72,
                "fitMode": "crop",
                "cropX": 0,
                "cropY": 30,
                "cropW": 320,
                "cropH": 180,
            }
        )
        upload_url = f"http://127.0.0.1:{self.port}/api/effects/video/upload?{params}"
        req = urllib.request.Request(
            upload_url,
            data=video_bytes,
            headers={
                "Content-Type": "video/mp4",
                "Cookie": cookie,
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)
            body = json.loads(resp.read().decode("utf-8"))

        rel_file = body["video"]["file"]
        self.assertEqual(rel_file, "_uploads/demo_clip_128x72.mp4")
        saved_path = self.tmpdir / "src" / "effects" / "video" / rel_file
        self.assertTrue(saved_path.is_file())

        meta = probe_video_metadata(saved_path)
        self.assertEqual(meta["width"], 128)
        self.assertEqual(meta["height"], 72)

        # Effect discovery lists the uploaded video under _uploads/
        status, _, fx_resp = self._request("GET", "/api/effects", cookie=cookie)
        self.assertEqual(status, 200)
        video_fx = next(e for e in fx_resp["effects"] if e["id"] == "video")
        self.assertIn(rel_file, video_fx["availableFiles"])

        # Range request returns 206 Partial Content
        qs = urllib.parse.urlencode({"file": rel_file})
        range_req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/effects/video/file?{qs}",
            headers={"Cookie": cookie, "Range": "bytes=0-127"},
            method="GET",
        )
        with urllib.request.urlopen(range_req) as resp:
            self.assertEqual(resp.status, 206)
            self.assertEqual(len(resp.read()), 128)

        # Delete removes the uploaded video
        status, _, del_resp = self._request(
            "DELETE", f"/api/effects/video/file?{qs}", cookie=cookie
        )
        self.assertEqual(status, 200)
        self.assertEqual(del_resp["deleted"], rel_file)
        self.assertFalse(saved_path.is_file())

    def test_playback_ipc_status_and_commands(self) -> None:
        _, headers, _ = self._request(
            "POST", "/api/auth/setup", {"password": "secret-password"}
        )
        cookie = self._extract_cookie(headers)

        # Initially stopped
        status, _, pb = self._request("GET", "/api/playback/status", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertFalse(pb["running"])

        # Simulate a live external `make playlist` process via _runtime/state.json
        runtime_dir = self.tmpdir / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        import time as _time

        (runtime_dir / "state.json").write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "status": "playing",
                    "mode": "playlist",
                    "currentIndex": 2,
                    "currentEffect": "hallway",
                    "currentConfig": {},
                    "playlistLength": 18,
                    "playlistDelay": 60,
                    "startedAt": _time.time() - 5,
                    "updatedAt": _time.time(),
                    "virtual": True,
                }
            ),
            encoding="utf-8",
        )

        status, _, pb = self._request("GET", "/api/playback/status", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertTrue(pb["running"])
        self.assertEqual(pb["currentEffect"], "hallway")
        self.assertEqual(pb["currentIndex"], 2)

        # Skip next writes IPC command
        status, _, _ = self._request("POST", "/api/playback/next", {}, cookie=cookie)
        self.assertEqual(status, 200)
        cmd = json.loads((runtime_dir / "command.json").read_text(encoding="utf-8"))
        self.assertEqual(cmd["action"], "next")

        # Jump writes jump command with index
        status, _, _ = self._request(
            "POST", "/api/playback/jump", {"index": 5}, cookie=cookie
        )
        self.assertEqual(status, 200)
        cmd = json.loads((runtime_dir / "command.json").read_text(encoding="utf-8"))
        self.assertEqual(cmd["action"], "jump")
        self.assertEqual(cmd["index"], 5)

        # Play ad-hoc effect writes play_effect command
        status, _, _ = self._request(
            "POST",
            "/api/playback/play",
            {"effect": "video", "config": {"file": "_uploads/demo_128x72.mp4"}},
            cookie=cookie,
        )
        self.assertEqual(status, 200)
        cmd = json.loads((runtime_dir / "command.json").read_text(encoding="utf-8"))
        self.assertEqual(cmd["action"], "play_effect")
        self.assertEqual(cmd["effect"], "video")
        self.assertEqual(cmd["config"]["file"], "_uploads/demo_128x72.mp4")

        # Stop writes stop command
        status, _, _ = self._request("POST", "/api/playback/stop", {}, cookie=cookie)
        self.assertEqual(status, 200)
        cmd = json.loads((runtime_dir / "command.json").read_text(encoding="utf-8"))
        self.assertEqual(cmd["action"], "stop")

    def test_security_csrf_nan_validation_and_rate_limit(self) -> None:
        _, headers, _ = self._request(
            "POST", "/api/auth/setup", {"password": "secret-password"}
        )
        self.assertIn("SameSite=Strict", headers.get("Set-Cookie", ""))
        cookie = self._extract_cookie(headers)

        # Cross-origin POST is rejected with 403
        csrf_req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/playback/next",
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "Cookie": cookie,
                "Origin": "http://evil.example",
            },
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(csrf_req)
        self.assertEqual(ctx.exception.code, 403)

        # Raw NaN JSON body is rejected (never written to config.json)
        nan_req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/config",
            data=b'{"brightness": NaN}',
            headers={"Content-Type": "application/json", "Cookie": cookie},
            method="PUT",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(nan_req)
        self.assertEqual(ctx.exception.code, 400)

        # Unknown effect name & path traversal in playback/play are rejected
        status, _, _ = self._request(
            "POST",
            "/api/playback/play",
            {"effect": "../../etc/passwd"},
            cookie=cookie,
        )
        self.assertEqual(status, 400)

        status, _, _ = self._request(
            "POST",
            "/api/playback/play",
            {"effect": "image", "config": {"file": "../../../etc/passwd"}},
            cookie=cookie,
        )
        self.assertEqual(status, 400)

        # Media file traversal in config playlist is rejected with 422
        _, _, cfg_resp = self._request("GET", "/api/config", cookie=cookie)
        bad_cfg = dict(cfg_resp["config"])
        bad_cfg["playlist"] = [{"effect": "video", "config": {"file": "../../secret.mp4"}}]
        status, _, err = self._request("PUT", "/api/config", {"config": bad_cfg}, cookie=cookie)
        self.assertEqual(status, 422)
        self.assertIn("playlist.0", err["fields"])

        # Login rate limiter returns 429 after exceeding max attempts
        last_status = 0
        for _ in range(13):
            last_status, _, _ = self._request(
                "POST", "/api/auth/login", {"password": "wrong-password"}
            )
        self.assertEqual(last_status, 429)

    def test_remote_target_proxy_and_frame_mirror(self) -> None:
        import struct

        # Spin up a second isolated server acting as a remote Raspberry Pi
        remote_dir = Path(tempfile.mkdtemp(prefix="led_matrix_remote_pi_"))
        try:
            shutil.copy2(REPO_ROOT / "default_config.json", remote_dir / "default_config.json")
            shutil.copytree(REPO_ROOT / "src" / "effects", remote_dir / "src" / "effects")
            shutil.copytree(REPO_ROOT / "fonts", remote_dir / "fonts")
            remote_static = remote_dir / "web" / "client" / "dist"
            remote_static.mkdir(parents=True)
            (remote_static / "index.html").write_text("<html>remote</html>", encoding="utf-8")

            remote_server = create_server(
                "127.0.0.1",
                0,
                repo_root=remote_dir,
                static_dir=remote_static,
                auth_file=remote_dir / "web" / ".auth.json",
                targets_file=remote_dir / "web" / ".targets.json",
                env_password="pi-password",
            )
            remote_port = remote_server.server_address[1]
            remote_thread = threading.Thread(target=remote_server.serve_forever, daemon=True)
            remote_thread.start()

            try:
                # 1. Authenticate to local Mac Studio
                _, headers, _ = self._request(
                    "POST", "/api/auth/setup", {"password": "mac-password"}
                )
                local_cookie = self._extract_cookie(headers)

                remote_url = f"http://127.0.0.1:{remote_port}"

                # 2. Test reachability of the remote Pi
                status, _, probe = self._request(
                    "POST", "/api/targets/test", {"url": remote_url}, cookie=local_cookie
                )
                self.assertEqual(status, 200)
                self.assertTrue(probe["reachable"])
                self.assertTrue(probe["initialized"])
                self.assertFalse(probe["authenticated"])

                # 3. Add remote Pi target
                status, _, added = self._request(
                    "POST",
                    "/api/targets",
                    {"name": "Living Room Pi", "url": remote_url},
                    cookie=local_cookie,
                )
                self.assertEqual(status, 201)
                target_id = added["target"]["id"]

                # 4. Switch active target to remote Pi BEFORE remote login -> 401 with remoteAuthRequired
                status, _, _ = self._request(
                    "POST", "/api/targets/active", {"targetId": target_id}, cookie=local_cookie
                )
                self.assertEqual(status, 200)

                status, resp_headers, err_body = self._request(
                    "GET", "/api/config", cookie=local_cookie
                )
                self.assertEqual(status, 401)
                self.assertTrue(err_body.get("remoteAuthRequired"))
                self.assertEqual(resp_headers.get("X-Remote-Auth-Required"), "1")

                # Local Mac auth is still intact!
                status, _, local_auth = self._request(
                    "GET", "/api/auth/status", cookie=local_cookie
                )
                self.assertEqual(status, 200)
                self.assertTrue(local_auth["authenticated"])

                # 5. Sign in to remote Pi target
                status, _, login_res = self._request(
                    "POST",
                    f"/api/targets/{target_id}/login",
                    {"password": "pi-password"},
                    cookie=local_cookie,
                )
                self.assertEqual(status, 200)
                self.assertTrue(login_res["authenticated"])

                # 6. Proxied GET/PUT /api/config edits the REMOTE Pi's config.json (not local!)
                status, _, remote_cfg = self._request(
                    "GET", "/api/config", cookie=local_cookie
                )
                self.assertEqual(status, 200)
                updated = dict(remote_cfg["config"])
                updated["brightness"] = 0.77
                status, _, saved_remote = self._request(
                    "PUT", "/api/config", {"config": updated}, cookie=local_cookie
                )
                self.assertEqual(status, 200)
                self.assertAlmostEqual(saved_remote["config"]["brightness"], 0.77)
                self.assertTrue((remote_dir / "config.json").is_file())
                self.assertFalse((self.tmpdir / "config.json").is_file())

                # 7. Live Frame Mirror proxies binary RGB frames from remote Pi & touches lease
                remote_mirror_dir = remote_server.app_ctx.playback.mirror_dir
                remote_mirror_dir.mkdir(parents=True, exist_ok=True)
                rgb_pixels = bytes([255, 0, 128]) * (4 * 2)
                (remote_mirror_dir / "frame.bin").write_bytes(
                    struct.pack(">HH", 4, 2) + rgb_pixels
                )
                status, frame_headers, frame_bytes = self._request(
                    "GET", "/api/playback/frame", cookie=local_cookie
                )
                self.assertEqual(status, 200)
                self.assertEqual(frame_headers.get("X-Matrix-Width"), "4")
                self.assertEqual(frame_headers.get("X-Matrix-Height"), "2")
                self.assertEqual(frame_headers.get("Cache-Control"), "private, no-store")
                self.assertEqual(frame_bytes, rgb_pixels)
                self.assertTrue((remote_mirror_dir / "mirror.lease").is_file())

                # 7b. X-Matrix-Target: local overrides global activeTargetId per request
                req_local = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/api/config",
                    headers={"Cookie": local_cookie, "X-Matrix-Target": "local"},
                    method="GET",
                )
                with urllib.request.urlopen(req_local) as resp:
                    local_cfg_body = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(local_cfg_body["source"], "default")
                self.assertAlmostEqual(local_cfg_body["config"]["brightness"], 0.2)

                # 7c. Cloud metadata IP is rejected by URL validator
                status, _, _ = self._request(
                    "POST",
                    "/api/targets/test",
                    {"url": "http://169.254.169.254"},
                    cookie=local_cookie,
                )
                self.assertEqual(status, 400)

                # 8. Deleting active remote target falls back cleanly to local
                status, _, del_res = self._request(
                    "DELETE", f"/api/targets/{target_id}", cookie=local_cookie
                )
                self.assertEqual(status, 200)
                self.assertEqual(del_res["activeTargetId"], "local")
            finally:
                remote_server.shutdown()
                remote_server.server_close()
        finally:
            shutil.rmtree(remote_dir, ignore_errors=True)

    def test_remote_git_pull_and_restart(self) -> None:
        if not shutil.which("git"):
            self.skipTest("git is not installed")

        sandbox = Path(tempfile.mkdtemp(prefix="led_matrix_git_test_"))
        try:
            bare_dir = sandbox / "origin.git"
            dev_dir = sandbox / "dev"
            pi_dir = sandbox / "pi"

            git_env = {
                **os.environ,
                "GIT_AUTHOR_NAME": "Test User",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test User",
                "GIT_COMMITTER_EMAIL": "test@example.com",
                "GIT_TERMINAL_PROMPT": "0",
            }

            def run_git(cwd: Path, *args: str) -> None:
                res = subprocess.run(
                    ["git", *args],
                    cwd=str(cwd),
                    env=git_env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    res.returncode,
                    0,
                    f"git {' '.join(args)} failed: {res.stderr or res.stdout}",
                )

            bare_dir.mkdir()
            run_git(bare_dir, "init", "--bare", "-b", "main")
            run_git(sandbox, "clone", str(bare_dir), str(dev_dir))
            shutil.copy2(REPO_ROOT / "default_config.json", dev_dir / "default_config.json")
            (dev_dir / "src").mkdir(exist_ok=True)
            (dev_dir / "src" / "effect.py").write_text("VALUE = 1\n", encoding="utf-8")
            (dev_dir / "web" / "server").mkdir(parents=True, exist_ok=True)
            (dev_dir / "web" / "server" / "dummy.py").write_text("V = 1\n", encoding="utf-8")
            run_git(dev_dir, "add", ".")
            run_git(dev_dir, "commit", "-m", "initial commit")
            run_git(dev_dir, "push", "-u", "origin", "main")

            # Clone onto simulated Pi
            run_git(sandbox, "clone", str(bare_dir), str(pi_dir))
            (pi_dir / "web" / "client" / "dist").mkdir(parents=True, exist_ok=True)

            # Push a new commit from dev repo so Pi is 1 commit behind
            (dev_dir / "src" / "effect.py").write_text("VALUE = 2\n", encoding="utf-8")
            (dev_dir / "web" / "server" / "dummy.py").write_text("V = 2\n", encoding="utf-8")
            run_git(dev_dir, "add", ".")
            run_git(dev_dir, "commit", "-m", "add new matrix effect")
            run_git(dev_dir, "push", "origin", "main")

            restarted = threading.Event()
            pi_server = create_server(
                "127.0.0.1",
                0,
                repo_root=pi_dir,
                static_dir=pi_dir / "web" / "client" / "dist",
                auth_file=pi_dir / "web" / ".auth.json",
                targets_file=pi_dir / "web" / ".targets.json",
                env_password="pi-password",
                restart_callback=restarted.set,
            )
            pi_port = pi_server.server_address[1]
            pi_thread = threading.Thread(target=pi_server.serve_forever, daemon=True)
            pi_thread.start()
            try:
                _, headers, _ = self._request(
                    "POST", "/api/auth/setup", {"password": "local-password"}
                )
                local_cookie = self._extract_cookie(headers)
                # Non-git local tmpdir reports isGitRepo=False cleanly
                status, _, local_git = self._request(
                    "GET", "/api/system/git-status", cookie=local_cookie
                )
                self.assertEqual(status, 200)
                self.assertFalse(local_git["isGitRepo"])
                self.assertFalse(local_git["canRestart"])

                # Add, switch, and log into remote Pi
                status, _, added = self._request(
                    "POST",
                    "/api/targets",
                    {"name": "Pi Git Test", "url": f"http://127.0.0.1:{pi_port}"},
                    cookie=local_cookie,
                )
                self.assertEqual(status, 201)
                target_id = added["target"]["id"]
                status, _, _ = self._request(
                    "POST",
                    f"/api/targets/{target_id}/login",
                    {"password": "pi-password"},
                    cookie=local_cookie,
                )
                self.assertEqual(status, 200)
                status, _, _ = self._request(
                    "POST",
                    "/api/targets/active",
                    {"targetId": target_id},
                    cookie=local_cookie,
                )
                self.assertEqual(status, 200)

                # Proxied git-status?fetch=1 detects the Pi is 1 commit behind
                status, _, pi_git = self._request(
                    "GET", "/api/system/git-status?fetch=1", cookie=local_cookie
                )
                self.assertEqual(status, 200)
                self.assertTrue(pi_git["isGitRepo"])
                self.assertEqual(pi_git["branch"], "main")
                self.assertEqual(pi_git["behind"], 1)
                self.assertTrue(pi_git["canRestart"])

                # Dirty tracked file blocks git pull cleanly with 409
                (pi_dir / "src" / "effect.py").write_text("VALUE = 99\n", encoding="utf-8")
                status, _, dirty_err = self._request(
                    "POST", "/api/system/git-pull", {}, cookie=local_cookie
                )
                self.assertEqual(status, 409)
                self.assertIn("src/effect.py", dirty_err["error"])

                # Revert local tracked edit -> proxied git pull fast-forwards cleanly!
                run_git(pi_dir, "checkout", "--", "src/effect.py")
                status, _, pull_res = self._request(
                    "POST", "/api/system/git-pull", {}, cookie=local_cookie
                )
                self.assertEqual(status, 200)
                self.assertTrue(pull_res["updated"])
                self.assertTrue(pull_res["serverFilesChanged"])
                self.assertTrue(pull_res["playbackFilesChanged"])
                self.assertIn("src/effect.py", pull_res["changedFiles"])
                self.assertEqual(pull_res["status"]["behind"], 0)
                self.assertEqual(
                    (pi_dir / "src" / "effect.py").read_text(encoding="utf-8"),
                    "VALUE = 2\n",
                )

                # Proxied restart triggers the remote Pi's restart callback
                status, _, restart_res = self._request(
                    "POST", "/api/system/restart", {}, cookie=local_cookie
                )
                self.assertEqual(status, 200)
                self.assertTrue(restart_res["restarting"])
                self.assertTrue(restarted.is_set())

                # Env-managed Pi persisted its session_secret so cookies survive restarts
                auth_data = json.loads(
                    (pi_dir / "web" / ".auth.json").read_text(encoding="utf-8")
                )
                self.assertTrue(auth_data.get("session_secret"))
                self.assertEqual(auth_data.get("password_hash"), "")

                # Conditional rebuild runs pip + npm when requirements.txt & web/client/ change
                (dev_dir / "requirements.txt").write_text("# reqs\n", encoding="utf-8")
                (dev_dir / "web" / "client").mkdir(parents=True, exist_ok=True)
                (dev_dir / "web" / "client" / "package.json").write_text(
                    '{"name":"client"}\n', encoding="utf-8"
                )
                run_git(dev_dir, "add", ".")
                run_git(dev_dir, "commit", "-m", "update python and frontend deps")
                run_git(dev_dir, "push", "origin", "main")

                # Simulate an existing frontend install on the target
                (pi_dir / "web" / "client" / "node_modules").mkdir(
                    parents=True, exist_ok=True
                )
                ran_cmds: list[list[str]] = []

                def fake_run_tool(cmd, *, cwd, timeout=240.0, extra_env=None):
                    ran_cmds.append(list(cmd))
                    return True, "ok"

                orig_run_tool = pi_server.app_ctx.git_updater._run_tool
                pi_server.app_ctx.git_updater._run_tool = fake_run_tool
                try:
                    status, _, rebuild_pull = self._request(
                        "POST", "/api/system/git-pull", {}, cookie=local_cookie
                    )
                finally:
                    pi_server.app_ctx.git_updater._run_tool = orig_run_tool

                self.assertEqual(status, 200)
                self.assertTrue(rebuild_pull["updated"])
                self.assertTrue(rebuild_pull["pythonDepsChanged"])
                self.assertTrue(rebuild_pull["nodeDepsChanged"])
                self.assertTrue(rebuild_pull["rebuilt"])
                self.assertFalse(rebuild_pull["rebuildFailed"])
                step_names = [s["name"] for s in rebuild_pull["rebuildSteps"]]
                self.assertIn("python-deps", step_names)
                if shutil.which("npm"):
                    self.assertIn("node-deps", step_names)
                    self.assertIn("frontend-build", step_names)
                self.assertTrue(any("pip" in cmd for cmd in ran_cmds))
            finally:
                pi_server.shutdown()
                pi_server.server_close()
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)

    def test_fonts_api_and_generic_effect_preview(self):
        _, headers, _ = self._request(
            "POST", "/api/auth/setup", {"password": "secret-password"}
        )
        cookie = self._extract_cookie(headers)

        # 1. GET /api/effects includes fontCatalog and marquee hasPreview + configPresets
        status, _, fx_data = self._request("GET", "/api/effects", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(fx_data.get("fontCatalog", [])), 10)
        marquee = next(e for e in fx_data["effects"] if e["id"] == "marquee")
        self.assertEqual(marquee["configSchema"], "fields")
        self.assertTrue(marquee["hasPreview"])
        self.assertGreaterEqual(len(marquee.get("configPresets", [])), 5)

        # 2. GET /api/fonts and GET /api/fonts/file serve real font bytes
        status, _, fonts_list = self._request("GET", "/api/fonts", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertTrue(any(f["id"] == "dosis.ttf" for f in fonts_list["fonts"]))

        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/fonts/file?file=dosis.ttf",
            headers={"Cookie": cookie},
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Content-Type"), "font/ttf")
            ttf_bytes = resp.read()
            self.assertGreater(len(ttf_bytes), 4000)

        # 3. Upload & delete custom font
        b64_ttf = base64.b64encode(ttf_bytes).decode("ascii")
        status, _, uploaded = self._request(
            "POST",
            "/api/fonts/upload",
            {"filename": "custom_test.ttf", "dataBase64": b64_ttf},
            cookie=cookie,
        )
        self.assertEqual(status, 201)
        uploaded_id = uploaded["font"]["id"]
        self.assertTrue(uploaded_id.startswith("_uploads/"))

        status, _, deleted = self._request(
            "DELETE",
            f"/api/fonts/file?file={urllib.parse.quote(uploaded_id)}",
            cookie=cookie,
        )
        self.assertEqual(status, 200)
        self.assertEqual(deleted["deleted"], uploaded_id)

        # 4. Generic POST /api/effects/:name/preview renders marquee frames + diagnostics
        status, _, preview_res = self._request(
            "POST",
            "/api/effects/marquee/preview",
            {
                "config": {"text": "HELLO\nWORLD", "font": "pixel_5x7", "mode": "auto"},
                "width": 64,
                "height": 32,
            },
            cookie=cookie,
        )
        self.assertEqual(status, 200)
        self.assertEqual(preview_res["width"], 64)
        self.assertEqual(preview_res["height"], 32)
        self.assertGreaterEqual(preview_res["frameCount"], 1)
        self.assertTrue(len(preview_res["diagnostics"]) >= 1)

        # 5. Effects without a preview() hook return 501 cleanly
        status, _, _ = self._request(
            "POST",
            "/api/effects/warp/preview",
            {"config": {}, "width": 64, "height": 32},
            cookie=cookie,
        )
        self.assertEqual(status, 501)


if __name__ == "__main__":
    unittest.main()
