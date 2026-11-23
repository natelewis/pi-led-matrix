"""Remote LED Matrix target registry and authenticated HTTP reverse proxy.

Allows a local Studio instance (e.g. running on a Mac) to manage and control
one or more remote Raspberry Pi Studio servers over the local network while
keeping browser requests same-origin (no CORS or cross-origin cookie issues).
"""

from __future__ import annotations

import http.client
import json
import os
import secrets
import ssl
import sys
import threading
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple
from urllib.parse import urlparse


LOCAL_TARGET_ID = "local"
SESSION_COOKIE_NAME = "led_matrix_session"
PROXY_CONNECT_TIMEOUT = 8.0
PROXY_GIT_TIMEOUT = 45.0
PROXY_UPLOAD_TIMEOUT = 310.0
TEST_TIMEOUT = 4.0
MAX_CONTROL_RESP_BYTES = 1_048_576  # 1 MiB cap for control/auth responses
MAX_PROXY_BODY_BYTES = 10_485_760  # 10 MiB for non-video proxied requests
MAX_PROXY_VIDEO_BYTES = 250 * 1024 * 1024  # 250 MiB for proxied video uploads

# Headers that must not be forwarded across HTTP proxy hops (RFC 7230)
HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)


class RemoteUnreachableError(RuntimeError):
    """Raised when a remote Studio server cannot be reached over the network."""


class RemoteRequestError(RuntimeError):
    """Raised when a remote Studio server rejects an auth/control request."""

    def __init__(
        self, message: str, *, status: int = 401, remote_auth_required: bool = False
    ) -> None:
        super().__init__(message)
        self.status = status
        self.remote_auth_required = remote_auth_required


def normalize_target_url(raw_url: str) -> str:
    """Validate and normalize a remote Studio base URL (http:// or https://)."""
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in raw_url):
        raise ValueError("Target URL contains invalid control characters.")
    cleaned = raw_url.strip()
    if not cleaned or any(ch.isspace() for ch in cleaned):
        raise ValueError("Target URL is required and must not contain spaces.")
    if "://" not in cleaned:
        cleaned = f"http://{cleaned}"
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Target URL must use http:// or https://.")
    if not parsed.hostname:
        raise ValueError("Target URL must include a hostname or IP address.")
    if parsed.hostname == "169.254.169.254":
        raise ValueError("Cloud metadata link-local addresses are not permitted.")
    if parsed.username or parsed.password:
        raise ValueError("Credentials in the URL are not allowed; sign in separately.")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("Target URL must be a base origin without a path or query string.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Target URL has an invalid port.") from exc

    host_part = parsed.hostname.lower()
    if ":" in host_part:
        host_part = f"[{host_part}]"
    default_port = 443 if parsed.scheme == "https" else 80
    if port is not None and port != default_port:
        return f"{parsed.scheme}://{host_part}:{port}"
    return f"{parsed.scheme}://{host_part}"


def _open_connection(
    base_url: str, *, timeout: float = PROXY_CONNECT_TIMEOUT
) -> Tuple[http.client.HTTPConnection, str]:
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    if parsed.scheme == "https":
        port = parsed.port or 443
        conn: http.client.HTTPConnection = http.client.HTTPSConnection(
            host, port, timeout=timeout, context=ssl.create_default_context()
        )
    else:
        port = parsed.port or 80
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
    return conn, parsed.netloc


def _extract_session_cookie_from_headers(
    headers: List[Tuple[str, str]]
) -> Optional[str]:
    for key, val in headers:
        if key.lower() != "set-cookie":
            continue
        cookie: SimpleCookie = SimpleCookie()
        try:
            cookie.load(val)
        except Exception:
            continue
        morsel = cookie.get(SESSION_COOKIE_NAME)
        if morsel is not None:
            return morsel.value
    return None


def _parse_connection_nominated_headers(resp: http.client.HTTPResponse) -> set[str]:
    nominated: set[str] = set()
    for key, val in resp.getheaders():
        if key.lower() == "connection":
            for token in val.split(","):
                cleaned = token.strip().lower()
                if cleaned:
                    nominated.add(cleaned)
    return nominated


class TargetManager:
    """Thread-safe registry of remote Pi targets and their server-side session cookies."""

    def __init__(self, targets_file: Path) -> None:
        self.targets_file = targets_file
        self._lock = threading.Lock()
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.targets_file.is_file():
            try:
                data = json.loads(self.targets_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("targets"), list):
                    valid_targets: List[Dict[str, Any]] = []
                    for item in data["targets"]:
                        if (
                            isinstance(item, dict)
                            and isinstance(item.get("id"), str)
                            and item["id"].strip()
                            and isinstance(item.get("name"), str)
                            and item["name"].strip()
                            and isinstance(item.get("url"), str)
                            and item["url"].strip()
                        ):
                            valid_targets.append(
                                {
                                    "id": item["id"],
                                    "name": item["name"],
                                    "url": item["url"],
                                    "sessionToken": str(item.get("sessionToken") or ""),
                                    "createdAt": item.get("createdAt"),
                                }
                            )
                    active = str(data.get("activeTargetId") or LOCAL_TARGET_ID)
                    if active != LOCAL_TARGET_ID and not any(
                        t["id"] == active for t in valid_targets
                    ):
                        active = LOCAL_TARGET_ID
                    return {"activeTargetId": active, "targets": valid_targets}
            except (OSError, json.JSONDecodeError):
                pass
        return {"activeTargetId": LOCAL_TARGET_ID, "targets": []}

    def _persist_locked(self) -> None:
        self.targets_file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._state, indent=2, allow_nan=False) + "\n"
        tmp_path = self.targets_file.with_name(
            f".{self.targets_file.name}.{secrets.token_hex(6)}.tmp"
        )
        fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_path, self.targets_file)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

    def _public_target(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": entry["id"],
            "name": entry["name"],
            "url": entry["url"],
            "isLocal": False,
            "hasSession": bool(entry.get("sessionToken")),
            "createdAt": entry.get("createdAt"),
        }

    def list_targets(self) -> Dict[str, Any]:
        with self._lock:
            active_id = self._state.get("activeTargetId", LOCAL_TARGET_ID)
            if active_id != LOCAL_TARGET_ID and not any(
                t["id"] == active_id for t in self._state["targets"]
            ):
                active_id = LOCAL_TARGET_ID
                self._state["activeTargetId"] = LOCAL_TARGET_ID

            items = [
                {
                    "id": LOCAL_TARGET_ID,
                    "name": "Local Machine",
                    "url": None,
                    "isLocal": True,
                    "hasSession": True,
                    "createdAt": None,
                },
                *[self._public_target(t) for t in self._state["targets"]],
            ]
            return {"activeTargetId": active_id, "targets": items}

    def resolve_remote_for_request(
        self, header_target_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Resolve which remote target a request should proxy to (None = handle locally).

        Honors per-request `X-Matrix-Target` header when present so multiple open
        tabs never clobber each other's active device.
        """
        with self._lock:
            requested = (
                header_target_id.strip()
                if isinstance(header_target_id, str) and header_target_id.strip()
                else self._state.get("activeTargetId", LOCAL_TARGET_ID)
            )
            if requested == LOCAL_TARGET_ID:
                return None
            for entry in self._state["targets"]:
                if entry["id"] == requested:
                    return dict(entry)
            if header_target_id:
                raise ValueError(f"Unknown target '{requested}'.")
            return None

    def get_target(self, target_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for entry in self._state["targets"]:
                if entry["id"] == target_id:
                    return dict(entry)
            return None

    def add_target(self, name: str, raw_url: str) -> Dict[str, Any]:
        clean_name = name.strip()
        if not clean_name or len(clean_name) > 64:
            raise ValueError("Target name must be between 1 and 64 characters.")
        url = normalize_target_url(raw_url)

        with self._lock:
            if any(t["url"] == url for t in self._state["targets"]):
                raise ValueError(f"A target with URL {url} already exists.")
            entry = {
                "id": f"remote_{secrets.token_hex(6)}",
                "name": clean_name,
                "url": url,
                "sessionToken": "",
                "createdAt": time.time(),
            }
            self._state["targets"].append(entry)
            self._persist_locked()
            return self._public_target(entry)

    def delete_target(self, target_id: str) -> bool:
        if target_id == LOCAL_TARGET_ID:
            raise ValueError("Cannot delete the built-in Local Machine target.")
        with self._lock:
            before = len(self._state["targets"])
            self._state["targets"] = [
                t for t in self._state["targets"] if t["id"] != target_id
            ]
            if len(self._state["targets"]) == before:
                return False
            if self._state.get("activeTargetId") == target_id:
                self._state["activeTargetId"] = LOCAL_TARGET_ID
            self._persist_locked()
            return True

    def set_active_target(self, target_id: str) -> Dict[str, Any]:
        with self._lock:
            if target_id != LOCAL_TARGET_ID and not any(
                t["id"] == target_id for t in self._state["targets"]
            ):
                raise ValueError(f"Unknown target '{target_id}'.")
            self._state["activeTargetId"] = target_id
            self._persist_locked()
        return self.list_targets()

    def set_target_session(self, target_id: str, session_token: str) -> None:
        with self._lock:
            for entry in self._state["targets"]:
                if entry["id"] == target_id:
                    entry["sessionToken"] = session_token
                    self._persist_locked()
                    return

    def clear_target_session(
        self, target_id: str, *, expected_token: Optional[str] = None
    ) -> bool:
        """Compare-and-swap session clear so stale 401s never wipe a newly signed-in token."""
        with self._lock:
            for entry in self._state["targets"]:
                if entry["id"] != target_id:
                    continue
                current = entry.get("sessionToken", "")
                if expected_token is not None and current != expected_token:
                    return False
                if not current:
                    return False
                entry["sessionToken"] = ""
                self._persist_locked()
                return True
            return False

    def test_url(self, raw_url: str, *, session_token: str = "") -> Dict[str, Any]:
        url = normalize_target_url(raw_url)
        conn, netloc = _open_connection(url, timeout=TEST_TIMEOUT)
        try:
            headers = {"Host": netloc, "Accept": "application/json"}
            if session_token:
                headers["Cookie"] = f"{SESSION_COOKIE_NAME}={session_token}"
            conn.request("GET", "/api/auth/status", headers=headers)
            resp = conn.getresponse()
            raw = resp.read(MAX_CONTROL_RESP_BYTES)
            if resp.status != 200:
                return {
                    "reachable": False,
                    "url": url,
                    "error": f"Remote server returned HTTP {resp.status}.",
                }
            data = json.loads(raw.decode("utf-8"))
            return {
                "reachable": True,
                "url": url,
                "initialized": bool(data.get("initialized")),
                "authenticated": bool(data.get("authenticated")),
                "envManaged": bool(data.get("envManaged")),
            }
        except (OSError, http.client.HTTPException, json.JSONDecodeError, ValueError) as exc:
            return {
                "reachable": False,
                "url": url,
                "error": f"Could not reach {url}: {exc}",
            }
        finally:
            conn.close()

    def authenticate_target(
        self, target_id: str, password: str, *, setup: bool = False
    ) -> Dict[str, Any]:
        entry = self.get_target(target_id)
        if not entry:
            raise ValueError(f"Unknown target '{target_id}'.")
        if not password:
            raise ValueError("Password is required.")

        endpoint = "/api/auth/setup" if setup else "/api/auth/login"
        body = json.dumps({"password": password}, allow_nan=False).encode("utf-8")
        conn, netloc = _open_connection(entry["url"], timeout=PROXY_CONNECT_TIMEOUT)
        try:
            conn.request(
                "POST",
                endpoint,
                body=body,
                headers={
                    "Host": netloc,
                    "Origin": entry["url"],
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                },
            )
            resp = conn.getresponse()
            raw = resp.read(MAX_CONTROL_RESP_BYTES)
            parsed: Dict[str, Any] = {}
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            if resp.status != 200:
                err_msg = parsed.get("error") or f"Remote authentication failed (HTTP {resp.status})."
                raise RemoteRequestError(
                    str(err_msg),
                    status=resp.status if resp.status in (400, 401, 429) else 401,
                    remote_auth_required=(resp.status == 401),
                )

            token = _extract_session_cookie_from_headers(resp.getheaders())
            if not token:
                raise RemoteRequestError(
                    "Remote server did not issue a session cookie.",
                    status=502,
                )

            self.set_target_session(target_id, token)
            return {
                "authenticated": True,
                "target": self._public_target({**entry, "sessionToken": token}),
            }
        except (OSError, http.client.HTTPException) as exc:
            raise RemoteUnreachableError(f"Could not reach {entry['url']}: {exc}") from exc
        finally:
            conn.close()

    def logout_target(self, target_id: str) -> Dict[str, Any]:
        entry = self.get_target(target_id)
        if not entry:
            raise ValueError(f"Unknown target '{target_id}'.")
        token = entry.get("sessionToken", "")
        if token:
            conn, netloc = _open_connection(entry["url"], timeout=TEST_TIMEOUT)
            try:
                body = b"{}"
                conn.request(
                    "POST",
                    "/api/auth/logout",
                    body=body,
                    headers={
                        "Host": netloc,
                        "Origin": entry["url"],
                        "Content-Type": "application/json",
                        "Content-Length": str(len(body)),
                        "Cookie": f"{SESSION_COOKIE_NAME}={token}",
                    },
                )
                conn.getresponse().read(MAX_CONTROL_RESP_BYTES)
            except (OSError, http.client.HTTPException):
                pass
            finally:
                conn.close()
        self.clear_target_session(target_id)
        return {
            "authenticated": False,
            "target": self._public_target({**entry, "sessionToken": ""}),
        }

    def proxy_request(
        self,
        target: Dict[str, Any],
        method: str,
        raw_path_and_query: str,
        req_headers: Any,
        body_stream: BinaryIO,
        handler: Any,
    ) -> None:
        """Stream an HTTP request to the active remote Pi and stream the response back."""
        if (req_headers.get("Transfer-Encoding") or "").strip():
            handler.send_json(
                {"error": "Chunked transfer encoding is not supported by the proxy."},
                status=HTTPStatus.LENGTH_REQUIRED,
            )
            return

        is_video_upload = raw_path_and_query.startswith("/api/effects/video/upload")
        max_body = MAX_PROXY_VIDEO_BYTES if is_video_upload else MAX_PROXY_BODY_BYTES

        raw_len = req_headers.get("Content-Length")
        content_length = 0
        if raw_len is not None:
            try:
                content_length = int(raw_len)
            except ValueError:
                handler.send_json(
                    {"error": "Invalid Content-Length header."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            if content_length < 0 or content_length > max_body:
                handler.send_json(
                    {"error": "Request body size out of allowed range."},
                    status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                )
                return

        is_git_op = raw_path_and_query.startswith("/api/system/git-")
        timeout = (
            PROXY_UPLOAD_TIMEOUT
            if is_video_upload
            else (PROXY_GIT_TIMEOUT if is_git_op else PROXY_CONNECT_TIMEOUT)
        )
        conn, netloc = _open_connection(target["url"], timeout=timeout)

        token = target.get("sessionToken", "")
        out_headers: Dict[str, str] = {
            "Host": netloc,
            "Origin": target["url"],
            "X-Led-Matrix-Proxy": "1",
        }
        if token:
            out_headers["Cookie"] = f"{SESSION_COOKIE_NAME}={token}"

        for header_name in ("Content-Type", "Range", "Accept", "If-None-Match"):
            val = req_headers.get(header_name)
            if val:
                out_headers[header_name] = val

        if content_length > 0:
            out_headers["Content-Length"] = str(content_length)
        elif method in ("POST", "PUT", "DELETE"):
            out_headers["Content-Length"] = "0"

        headers_sent = False
        try:
            conn.putrequest(method, raw_path_and_query, skip_host=True)
            for key, val in out_headers.items():
                conn.putheader(key, val)
            conn.endheaders()

            remaining = content_length
            while remaining > 0:
                chunk = body_stream.read(min(65536, remaining))
                if not chunk:
                    # Client disconnected mid-body — abort upstream instead of waiting 310s
                    return
                conn.send(chunk)
                remaining -= len(chunk)

            resp = conn.getresponse()

            # Intercept remote 401 so we do NOT log out the user's local Studio session
            if resp.status == 401:
                resp.read(MAX_CONTROL_RESP_BYTES)
                self.clear_target_session(target["id"], expected_token=token)
                handler.send_json(
                    {
                        "error": f"Sign in to remote device '{target['name']}' to continue.",
                        "remoteAuthRequired": True,
                        "targetId": target["id"],
                        "targetName": target["name"],
                        "targetUrl": target["url"],
                    },
                    status=HTTPStatus.UNAUTHORIZED,
                    extra_headers={"X-Remote-Auth-Required": "1"},
                )
                return

            skip_headers = HOP_BY_HOP_HEADERS | _parse_connection_nominated_headers(resp) | {
                "set-cookie",
                "server",
                "date",
                "cache-control",
                "x-content-type-options",
                "x-frame-options",
                "referrer-policy",
            }

            headers_sent = True
            handler.send_response(resp.status)
            handler._write_security_headers()
            # Prevent browser from caching identically-named media files across target switches
            handler.send_header("Cache-Control", "private, no-store")
            for key, val in resp.getheaders():
                if key.lower() in skip_headers:
                    continue
                handler.send_header(key, val)
            handler.end_headers()

            if method != "HEAD":
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    handler.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except (OSError, http.client.HTTPException) as exc:
            if not headers_sent:
                handler.send_json(
                    {
                        "error": f"Unable to reach remote device '{target['name']}' ({target['url']}): {exc}",
                        "remoteUnreachable": True,
                        "targetId": target["id"],
                        "targetName": target["name"],
                    },
                    status=HTTPStatus.BAD_GATEWAY,
                )
            else:
                print(
                    f"[proxy] Upstream stream interrupted mid-response from {target['url']}: {exc}",
                    file=sys.stderr,
                )
        finally:
            conn.close()
