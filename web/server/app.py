"""HTTP server entry point for the pi-led-matrix web configurator.

Runs with Python 3 standard library only so it works effortlessly on Raspberry Pi
and macOS without compiling native dependencies.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import posixpath
import subprocess
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .auth import AuthManager
from .config_store import ConfigStore, ConfigValidationError
from .effects import discover_effects, discover_fonts
from .media import ImageMediaStore, VideoMediaStore
from .playback import PlaybackController
from .router import Router


MAX_BODY_BYTES = 10_485_760  # 10 MiB


class AppContext:
    """Shared application state injected into every HTTP request handler."""

    def __init__(
        self,
        repo_root: Path,
        *,
        static_dir: Optional[Path] = None,
        auth_file: Optional[Path] = None,
        env_password: Optional[str] = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.web_root = self.repo_root / "web"
        self.static_dir = (
            static_dir.resolve()
            if static_dir is not None
            else (self.web_root / "client" / "dist").resolve()
        )
        self.auth = AuthManager(
            auth_file if auth_file is not None else self.web_root / ".auth.json",
            env_password=env_password,
        )
        self.config_store = ConfigStore(self.repo_root)
        self.media_store = ImageMediaStore(self.repo_root)
        self.video_store = VideoMediaStore(self.repo_root)
        self.playback = PlaybackController(self.repo_root)
        self.router = self._build_router()

    def _build_router(self) -> Router:
        router = Router()

        @router.get("/api/health", require_auth=False)
        def health(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            req.send_json({"status": "ok"})

        @router.get("/api/auth/status", require_auth=False)
        def auth_status(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            session = self.auth.extract_session_from_cookie_header(
                req.headers.get("Cookie")
            )
            req.send_json(
                {
                    "initialized": self.auth.is_initialized,
                    "authenticated": session is not None,
                    "envManaged": self.auth.is_env_managed,
                    "expiresAt": session.get("exp") if session else None,
                }
            )

        @router.post("/api/auth/setup", require_auth=False)
        def auth_setup(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            body = req.read_json_body()
            if body is None:
                return
            password = str(body.get("password", ""))
            ok, err = self.auth.setup_password(password)
            if not ok:
                req.send_json({"error": err}, status=HTTPStatus.BAD_REQUEST)
                return
            token = self.auth.create_session_token()
            cookie = self.auth.build_set_cookie_header(
                token, secure=req.is_https_request()
            )
            req.send_json(
                {
                    "initialized": True,
                    "authenticated": True,
                    "envManaged": self.auth.is_env_managed,
                },
                extra_headers={"Set-Cookie": cookie},
            )

        @router.post("/api/auth/login", require_auth=False)
        def auth_login(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            body = req.read_json_body()
            if body is None:
                return
            password = str(body.get("password", ""))
            client_ip = req.client_address[0] if req.client_address else "unknown"
            ok, err = self.auth.authenticate(password, client_ip)
            if not ok:
                status = (
                    HTTPStatus.TOO_MANY_REQUESTS
                    if self.auth.is_rate_limited(client_ip)
                    else HTTPStatus.UNAUTHORIZED
                )
                req.send_json({"error": err}, status=status)
                return
            token = self.auth.create_session_token()
            cookie = self.auth.build_set_cookie_header(
                token, secure=req.is_https_request()
            )
            req.send_json(
                {
                    "initialized": True,
                    "authenticated": True,
                    "envManaged": self.auth.is_env_managed,
                },
                extra_headers={"Set-Cookie": cookie},
            )

        @router.post("/api/auth/logout", require_auth=False)
        def auth_logout(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            req.send_json(
                {"authenticated": False},
                extra_headers={"Set-Cookie": self.auth.build_clear_cookie_header()},
            )

        @router.post("/api/auth/change-password", require_auth=True)
        def auth_change_password(
            req: MatrixRequestHandler, _params: Dict[str, str]
        ) -> None:
            body = req.read_json_body()
            if body is None:
                return
            current_password = str(body.get("currentPassword", ""))
            new_password = str(body.get("newPassword", ""))
            ok, err = self.auth.change_password(current_password, new_password)
            if not ok:
                req.send_json({"error": err}, status=HTTPStatus.BAD_REQUEST)
                return
            token = self.auth.create_session_token()
            cookie = self.auth.build_set_cookie_header(
                token, secure=req.is_https_request()
            )
            req.send_json(
                {"ok": True},
                extra_headers={"Set-Cookie": cookie},
            )

        @router.get("/api/config", require_auth=True)
        def get_config(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            data = self.config_store.load()
            data["schema"] = self.config_store.get_schema_metadata()
            req.send_json(data)

        @router.put("/api/config", require_auth=True)
        def put_config(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            body = req.read_json_body()
            if body is None:
                return
            # Accept either { "config": {...} } or a raw config dict directly
            candidate = body.get("config", body) if isinstance(body, dict) else body
            try:
                saved = self.config_store.save(candidate)
            except ConfigValidationError as exc:
                req.send_json(
                    {"error": "Validation failed", "fields": exc.errors},
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                )
                return
            saved["schema"] = self.config_store.get_schema_metadata()
            self.playback.notify_config_updated()
            req.send_json(saved)

        @router.post("/api/config/reset", require_auth=True)
        def reset_config(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            reset_data = self.config_store.reset_to_defaults()
            reset_data["schema"] = self.config_store.get_schema_metadata()
            self.playback.notify_config_updated()
            req.send_json(reset_data)

        @router.get("/api/config/defaults", require_auth=True)
        def get_default_config(
            req: MatrixRequestHandler, _params: Dict[str, str]
        ) -> None:
            req.send_json({"config": self.config_store.load_default_config()})

        @router.get("/api/effects", require_auth=True)
        def get_effects(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            req.send_json(
                {
                    "effects": discover_effects(self.repo_root),
                    "fonts": discover_fonts(self.repo_root),
                }
            )

        @router.get("/api/effects/image/files", require_auth=True)
        def list_image_files(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            req.send_json({"files": self.media_store.list_images()})

        @router.post("/api/effects/image/upload", require_auth=True)
        def upload_image_file(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            body = req.read_json_body()
            if body is None:
                return
            filename = str(body.get("filename", "image.png"))
            rgba_base64 = body.get("rgbaBase64")
            width = body.get("width")
            height = body.get("height")
            if not isinstance(rgba_base64, str) or not rgba_base64:
                req.send_json(
                    {"error": "Missing rgbaBase64 payload."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                saved = self.media_store.save_uploaded_rgba(
                    filename=filename,
                    width=width,
                    height=height,
                    rgba_base64=rgba_base64,
                )
            except ValueError as exc:
                req.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            req.send_json(
                {"image": saved, "files": self.media_store.list_images()},
                status=HTTPStatus.CREATED,
            )

        @router.get("/api/effects/image/file", require_auth=True)
        def get_image_file(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            query = parse_qs(urlparse(req.path).query)
            rel_file = (query.get("file") or [""])[0]
            try:
                target = self.media_store.resolve_image_path(rel_file)
            except ValueError as exc:
                req.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            if not target.is_file():
                req.send_json({"error": "Image file not found."}, status=HTTPStatus.NOT_FOUND)
                return
            content_type, _ = mimetypes.guess_type(str(target))
            data = target.read_bytes()
            req.send_response(int(HTTPStatus.OK))
            req._write_security_headers()
            req.send_header("Content-Type", content_type or "application/octet-stream")
            req.send_header("Cache-Control", "private, max-age=3600")
            req.send_header("Content-Length", str(len(data)))
            req.end_headers()
            req.wfile.write(data)

        @router.delete("/api/effects/image/file", require_auth=True)
        def delete_image_file(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            query = parse_qs(urlparse(req.path).query)
            rel_file = (query.get("file") or [""])[0]
            try:
                deleted = self.media_store.delete_upload(rel_file)
            except ValueError as exc:
                req.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            if not deleted:
                req.send_json({"error": "Uploaded image not found."}, status=HTTPStatus.NOT_FOUND)
                return
            req.send_json({"deleted": rel_file, "files": self.media_store.list_images()})

        @router.get("/api/effects/video/files", require_auth=True)
        def list_video_files(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            req.send_json({"files": self.video_store.list_videos()})

        @router.post("/api/effects/video/upload", require_auth=True)
        def upload_video_file(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            raw_len = req.headers.get("Content-Length")
            try:
                content_length = int(raw_len) if raw_len is not None else -1
            except ValueError:
                content_length = -1
            if content_length <= 0:
                req.send_json(
                    {"error": "Missing or invalid Content-Length header."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            query = parse_qs(urlparse(req.path).query)
            filename = (query.get("filename") or ["video.mp4"])[0]
            fit_mode = (query.get("fitMode") or ["crop"])[0]

            try:
                width = int((query.get("width") or ["0"])[0])
                height = int((query.get("height") or ["0"])[0])
            except ValueError:
                req.send_json(
                    {"error": "width and height must be integers."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            crop_rect = None
            if all(k in query for k in ("cropX", "cropY", "cropW", "cropH")):
                try:
                    crop_rect = (
                        int(round(float(query["cropX"][0]))),
                        int(round(float(query["cropY"][0]))),
                        int(round(float(query["cropW"][0]))),
                        int(round(float(query["cropH"][0]))),
                    )
                except ValueError:
                    req.send_json(
                        {"error": "Invalid crop parameters."},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return

            start_sec = None
            end_sec = None
            try:
                if "startSec" in query and query["startSec"][0] != "":
                    start_sec = float(query["startSec"][0])
                if "endSec" in query and query["endSec"][0] != "":
                    end_sec = float(query["endSec"][0])
            except ValueError:
                req.send_json(
                    {"error": "Invalid trim startSec/endSec parameters."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            try:
                saved = self.video_store.save_uploaded_stream(
                    req.rfile,
                    content_length,
                    filename=filename,
                    width=width,
                    height=height,
                    fit_mode=fit_mode,
                    crop_rect=crop_rect,
                    start_sec=start_sec,
                    end_sec=end_sec,
                )
            except ValueError as exc:
                req.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except RuntimeError as exc:
                req.send_json(
                    {"error": str(exc)}, status=HTTPStatus.UNPROCESSABLE_ENTITY
                )
                return

            req.send_json(
                {"video": saved, "files": self.video_store.list_videos()},
                status=HTTPStatus.CREATED,
            )

        @router.get("/api/effects/video/file", require_auth=True)
        def get_video_file(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            query = parse_qs(urlparse(req.path).query)
            rel_file = (query.get("file") or [""])[0]
            try:
                target = self.video_store.resolve_video_path(rel_file)
            except ValueError as exc:
                req.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            if not target.is_file():
                req.send_json(
                    {"error": "Video file not found."}, status=HTTPStatus.NOT_FOUND
                )
                return
            req.send_file_with_range(target)

        @router.delete("/api/effects/video/file", require_auth=True)
        def delete_video_file(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            query = parse_qs(urlparse(req.path).query)
            rel_file = (query.get("file") or [""])[0]
            try:
                deleted = self.video_store.delete_upload(rel_file)
            except ValueError as exc:
                req.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            if not deleted:
                req.send_json(
                    {"error": "Uploaded video not found."}, status=HTTPStatus.NOT_FOUND
                )
                return
            req.send_json({"deleted": rel_file, "files": self.video_store.list_videos()})

        @router.get("/api/playback/status", require_auth=True)
        def playback_status(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            req.send_json(self.playback.get_status())

        @router.post("/api/playback/start", require_auth=True)
        def playback_start(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            body = req.read_json_body()
            if body is None:
                return
            try:
                status = self.playback.start(
                    index=body.get("index"),
                    effect=body.get("effect"),
                    config=body.get("config"),
                )
            except (ValueError, RuntimeError) as exc:
                req.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            req.send_json(status)

        @router.post("/api/playback/stop", require_auth=True)
        def playback_stop(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            req.send_json(self.playback.stop())

        @router.post("/api/playback/next", require_auth=True)
        def playback_next(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            try:
                status = self.playback.skip_next()
            except RuntimeError as exc:
                req.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            req.send_json(status)

        @router.post("/api/playback/jump", require_auth=True)
        def playback_jump(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            body = req.read_json_body()
            if body is None:
                return
            try:
                status = self.playback.jump_to(body.get("index"))  # type: ignore[arg-type]
            except (ValueError, RuntimeError) as exc:
                req.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            req.send_json(status)

        @router.post("/api/playback/play", require_auth=True)
        def playback_play_effect(
            req: MatrixRequestHandler, _params: Dict[str, str]
        ) -> None:
            body = req.read_json_body()
            if body is None:
                return
            try:
                status = self.playback.play_effect(
                    body.get("effect", ""), body.get("config")
                )
            except (ValueError, RuntimeError) as exc:
                req.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            req.send_json(status)

        @router.post("/api/playback/reload", require_auth=True)
        def playback_reload(req: MatrixRequestHandler, _params: Dict[str, str]) -> None:
            self.playback.notify_config_updated()
            req.send_json(self.playback.get_status())

        return router


class MatrixRequestHandler(BaseHTTPRequestHandler):
    """Handles API routes and serves the built React SPA."""

    server_version = "PiLEDMatrixWeb/1.0"

    @property
    def ctx(self) -> AppContext:
        return self.server.app_ctx  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        if os.environ.get("LED_MATRIX_WEB_QUIET") == "1":
            return
        super().log_message(format, *args)

    def is_https_request(self) -> bool:
        proto = self.headers.get("X-Forwarded-Proto", "")
        return proto.lower() == "https"

    def _write_security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "same-origin")

    def send_json(
        self,
        payload: Any,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(int(status))
        self._write_security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(encoded)

    def send_file_with_range(self, file_path: Path) -> None:
        """Stream a media file with HTTP Range (206 Partial Content) support for video players."""
        file_size = file_path.stat().st_size
        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"
        range_header = self.headers.get("Range")

        start = 0
        end = file_size - 1
        status = HTTPStatus.OK

        if range_header and range_header.startswith("bytes="):
            spec = range_header.replace("bytes=", "", 1).split(",", 1)[0].strip()
            parts = spec.split("-", 1)
            try:
                if parts[0]:
                    start = int(parts[0])
                if len(parts) > 1 and parts[1]:
                    end = int(parts[1])
                if not parts[0] and len(parts) > 1 and parts[1]:
                    suffix = int(parts[1])
                    start = max(0, file_size - suffix)
                    end = file_size - 1
            except ValueError:
                self.send_error(int(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE))
                return
            if start < 0 or start >= file_size or end < start:
                self.send_response(int(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE))
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.end_headers()
                return
            end = min(end, file_size - 1)
            status = HTTPStatus.PARTIAL_CONTENT

        length = end - start + 1
        self.send_response(int(status))
        self._write_security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "private, max-age=3600")
        self.send_header("Content-Length", str(length))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.end_headers()

        with file_path.open("rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def read_json_body(self) -> Optional[Dict[str, Any]]:
        raw_len = self.headers.get("Content-Length")
        if raw_len is None:
            self.send_json(
                {"error": "Missing Content-Length header."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return None
        try:
            length = int(raw_len)
        except ValueError:
            self.send_json(
                {"error": "Invalid Content-Length header."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return None
        if length < 0 or length > MAX_BODY_BYTES:
            self.send_json(
                {"error": "Request body too large."},
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
            return None
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            parsed = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json(
                {"error": "Request body must be valid JSON."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return None
        if not isinstance(parsed, dict):
            self.send_json(
                {"error": "JSON body must be an object."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return None
        return parsed

    def _dispatch(self, method: str) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/"):
            matched = self.ctx.router.match(method, path)
            if not matched:
                self.send_json(
                    {"error": f"Endpoint not found: {method} {path}"},
                    status=HTTPStatus.NOT_FOUND,
                )
                return
            route, params = matched
            if route.require_auth:
                session = self.ctx.auth.extract_session_from_cookie_header(
                    self.headers.get("Cookie")
                )
                if session is None:
                    self.send_json(
                        {"error": "Authentication required."},
                        status=HTTPStatus.UNAUTHORIZED,
                    )
                    return
            try:
                route.handler(self, params)
            except Exception as exc:  # pragma: no cover - defensive fallback
                self.send_json(
                    {"error": f"Internal server error: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if method in ("GET", "HEAD"):
            self._serve_static(path, head_only=(method == "HEAD"))
        else:
            self.send_json(
                {"error": "Method not allowed."},
                status=HTTPStatus.METHOD_NOT_ALLOWED,
            )

    def _serve_static(self, raw_path: str, *, head_only: bool = False) -> None:
        static_dir = self.ctx.static_dir
        if not static_dir.is_dir():
            message = (
                "Frontend build not found. Run `make web-build` (or `cd web/client && "
                "npm install && npm run build`) first, or run Vite dev server with `make web-dev`."
            ).encode("utf-8")
            self.send_response(int(HTTPStatus.SERVICE_UNAVAILABLE))
            self._write_security_headers()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            if not head_only:
                self.wfile.write(message)
            return

        normalized = posixpath.normpath(raw_path).lstrip("/")
        if normalized in ("", "."):
            candidate = static_dir / "index.html"
        else:
            candidate = (static_dir / normalized).resolve()
            # Prevent path traversal outside static_dir
            try:
                candidate.relative_to(static_dir)
            except ValueError:
                self.send_error(int(HTTPStatus.FORBIDDEN), "Forbidden")
                return
            if not candidate.is_file():
                # SPA fallback for client-side routes
                candidate = static_dir / "index.html"

        if not candidate.is_file():
            self.send_error(int(HTTPStatus.NOT_FOUND), "Not Found")
            return

        content_type, _ = mimetypes.guess_type(str(candidate))
        if not content_type:
            content_type = "application/octet-stream"
        data = candidate.read_bytes()

        self.send_response(int(HTTPStatus.OK))
        self._write_security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if candidate.name == "index.html":
            self.send_header("Cache-Control", "no-cache")
        else:
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("HEAD")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")


def create_server(
    host: str,
    port: int,
    *,
    repo_root: Path,
    static_dir: Optional[Path] = None,
    auth_file: Optional[Path] = None,
    env_password: Optional[str] = None,
) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), MatrixRequestHandler)
    httpd.app_ctx = AppContext(  # type: ignore[attr-defined]
        repo_root=repo_root,
        static_dir=static_dir,
        auth_file=auth_file,
        env_password=env_password,
    )
    return httpd


def _snapshot_server_mtimes(server_dir: Path) -> Dict[Path, float]:
    return {
        p: p.stat().st_mtime
        for p in server_dir.glob("*.py")
        if p.is_file()
    }


def _run_with_reloader(raw_args: list[str]) -> None:
    server_dir = Path(__file__).resolve().parent
    child_args = [arg for arg in raw_args if arg != "--reload"]
    cmd = [sys.executable, "-m", "web.server.app", *child_args]

    mtimes = _snapshot_server_mtimes(server_dir)
    proc = subprocess.Popen(cmd)
    try:
        while True:
            time.sleep(0.5)
            current = _snapshot_server_mtimes(server_dir)
            if current != mtimes:
                print("\nDetected server code change — reloading web server...")
                mtimes = current
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                proc = subprocess.Popen(cmd)
            elif proc.poll() is not None:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> None:
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Web configuration server for pi-led-matrix."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("LED_MATRIX_WEB_HOST", "0.0.0.0"),
        help="Bind address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("LED_MATRIX_WEB_PORT", "8080")),
        help="Port to listen on (default: 8080)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(os.environ.get("LED_MATRIX_REPO_ROOT", str(default_root))),
        help="Path to the pi-led-matrix repository root",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Auto-restart the server when Python files in web/server/ change",
    )
    args = parser.parse_args()

    if args.reload:
        _run_with_reloader(sys.argv[1:])
        return

    httpd = create_server(args.host, args.port, repo_root=args.repo_root)
    print(f"LED Matrix Web Server listening on http://{args.host}:{args.port}")
    print(f"Repository root: {args.repo_root.resolve()}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down web server...")
    finally:
        httpd.app_ctx.playback.shutdown()  # type: ignore[attr-defined]
        httpd.server_close()


if __name__ == "__main__":
    main()
