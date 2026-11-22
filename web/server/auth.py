"""Simple local authentication using PBKDF2 password hashing and HttpOnly signed cookies."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections import defaultdict
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SESSION_COOKIE_NAME = "led_matrix_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
PBKDF2_ITERATIONS = 310_000
MIN_PASSWORD_LENGTH = 4
RATE_LIMIT_WINDOW_SECONDS = 300
RATE_LIMIT_MAX_ATTEMPTS = 12


def _hash_password(password: str, salt: bytes) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return base64.b64encode(derived).decode("ascii")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


class AuthManager:
    """Manages admin credentials, signed HttpOnly session cookies, and rate limiting."""

    def __init__(
        self,
        auth_file: Path,
        *,
        env_password: Optional[str] = None,
        session_ttl: int = SESSION_TTL_SECONDS,
    ) -> None:
        self.auth_file = auth_file
        self.env_password = env_password if env_password is not None else os.environ.get("LED_MATRIX_PASSWORD")
        self.session_ttl = session_ttl
        self._failed_attempts: Dict[str, List[float]] = defaultdict(list)
        self._state = self._load_or_init_state()

    def _load_or_init_state(self) -> Dict[str, str]:
        if self.auth_file.exists():
            try:
                data = json.loads(self.auth_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("session_secret"):
                    return data
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "session_secret": secrets.token_hex(32),
            "password_salt": "",
            "password_hash": "",
        }

    def _persist_state(self) -> None:
        self.auth_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.auth_file.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(self._state, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(tmp_path, 0o600)
        except OSError:
            pass
        os.replace(tmp_path, self.auth_file)

    @property
    def is_env_managed(self) -> bool:
        return bool(self.env_password)

    @property
    def is_initialized(self) -> bool:
        return self.is_env_managed or bool(
            self._state.get("password_hash") and self._state.get("password_salt")
        )

    def _verify_password(self, password: str) -> bool:
        if self.is_env_managed and self.env_password is not None:
            return hmac.compare_digest(password.encode("utf-8"), self.env_password.encode("utf-8"))
        if not self.is_initialized:
            return False
        salt = base64.b64decode(self._state["password_salt"])
        candidate = _hash_password(password, salt)
        return hmac.compare_digest(candidate, self._state["password_hash"])

    def is_rate_limited(self, client_ip: str) -> bool:
        now = time.time()
        attempts = [
            ts for ts in self._failed_attempts[client_ip] if now - ts < RATE_LIMIT_WINDOW_SECONDS
        ]
        self._failed_attempts[client_ip] = attempts
        return len(attempts) >= RATE_LIMIT_MAX_ATTEMPTS

    def _record_failure(self, client_ip: str) -> None:
        self._failed_attempts[client_ip].append(time.time())

    def _clear_failures(self, client_ip: str) -> None:
        self._failed_attempts.pop(client_ip, None)

    def setup_password(self, password: str) -> Tuple[bool, Optional[str]]:
        if self.is_initialized:
            return False, "Password is already configured."
        if len(password) < MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        salt = secrets.token_bytes(16)
        self._state["password_salt"] = base64.b64encode(salt).decode("ascii")
        self._state["password_hash"] = _hash_password(password, salt)
        if not self._state.get("session_secret"):
            self._state["session_secret"] = secrets.token_hex(32)
        self._persist_state()
        return True, None

    def change_password(
        self, current_password: str, new_password: str
    ) -> Tuple[bool, Optional[str]]:
        if self.is_env_managed:
            return False, "Password is managed via the LED_MATRIX_PASSWORD environment variable."
        if not self.is_initialized:
            return False, "Password has not been set up yet."
        if not self._verify_password(current_password):
            return False, "Current password is incorrect."
        if len(new_password) < MIN_PASSWORD_LENGTH:
            return False, f"New password must be at least {MIN_PASSWORD_LENGTH} characters."

        salt = secrets.token_bytes(16)
        self._state["password_salt"] = base64.b64encode(salt).decode("ascii")
        self._state["password_hash"] = _hash_password(new_password, salt)
        # Rotate session secret to invalidate older sessions elsewhere
        self._state["session_secret"] = secrets.token_hex(32)
        self._persist_state()
        return True, None

    def authenticate(self, password: str, client_ip: str) -> Tuple[bool, Optional[str]]:
        if not self.is_initialized:
            return False, "Password has not been set up yet."
        if self.is_rate_limited(client_ip):
            return False, "Too many failed login attempts. Please wait a few minutes."
        if not self._verify_password(password):
            self._record_failure(client_ip)
            return False, "Invalid password."
        self._clear_failures(client_ip)
        return True, None

    def create_session_token(self) -> str:
        payload = {
            "sub": "admin",
            "iat": int(time.time()),
            "exp": int(time.time()) + self.session_ttl,
            "nonce": secrets.token_hex(8),
        }
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = hmac.new(
            self._state["session_secret"].encode("utf-8"),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{payload_b64}.{_b64url_encode(signature)}"

    def verify_session_token(self, token: Optional[str]) -> Optional[Dict[str, object]]:
        if not token or "." not in token:
            return None
        try:
            payload_b64, sig_b64 = token.split(".", 1)
            expected_sig = hmac.new(
                self._state["session_secret"].encode("utf-8"),
                payload_b64.encode("ascii"),
                hashlib.sha256,
            ).digest()
            provided_sig = _b64url_decode(sig_b64)
            if not hmac.compare_digest(expected_sig, provided_sig):
                return None
            payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
            if not isinstance(payload, dict):
                return None
            exp = payload.get("exp")
            if not isinstance(exp, int) or exp < int(time.time()):
                return None
            return payload
        except (ValueError, json.JSONDecodeError):
            return None

    def extract_session_from_cookie_header(
        self, cookie_header: Optional[str]
    ) -> Optional[Dict[str, object]]:
        if not cookie_header:
            return None
        cookie: SimpleCookie = SimpleCookie()
        try:
            cookie.load(cookie_header)
        except Exception:
            return None
        morsel = cookie.get(SESSION_COOKIE_NAME)
        if not morsel:
            return None
        return self.verify_session_token(morsel.value)

    def build_set_cookie_header(self, token: str, *, secure: bool = False) -> str:
        parts = [
            f"{SESSION_COOKIE_NAME}={token}",
            "Path=/",
            "HttpOnly",
            "SameSite=Lax",
            f"Max-Age={self.session_ttl}",
        ]
        if secure:
            parts.append("Secure")
        return "; ".join(parts)

    def build_clear_cookie_header(self) -> str:
        return f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
