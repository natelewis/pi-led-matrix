"""Simple local authentication using PBKDF2 password hashing and HttpOnly signed cookies."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SESSION_COOKIE_NAME = "led_matrix_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
PBKDF2_ITERATIONS = 310_000
MIN_PASSWORD_LENGTH = 4
RATE_LIMIT_WINDOW_SECONDS = 300
RATE_LIMIT_MAX_ATTEMPTS = 12
MAX_TRACKED_IPS = 1024


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
    """Thread-safe admin credential, signed HttpOnly cookie, and rate-limit manager."""

    def __init__(
        self,
        auth_file: Path,
        *,
        env_password: Optional[str] = None,
        session_ttl: int = SESSION_TTL_SECONDS,
    ) -> None:
        self.auth_file = auth_file
        self.env_password = (
            env_password if env_password is not None else os.environ.get("LED_MATRIX_PASSWORD")
        )
        self.session_ttl = session_ttl
        self._lock = threading.Lock()
        self._failed_attempts: Dict[str, List[float]] = {}
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

    def _persist_state_locked(self) -> None:
        """Atomically persist auth state with 0600 permissions from creation (no TOCTOU)."""
        self.auth_file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._state, indent=2, allow_nan=False) + "\n"
        tmp_path = self.auth_file.with_name(
            f".{self.auth_file.name}.{secrets.token_hex(6)}.tmp"
        )
        fd = os.open(
            str(tmp_path),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp_path, self.auth_file)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

    @property
    def is_env_managed(self) -> bool:
        return bool(self.env_password)

    @property
    def is_initialized(self) -> bool:
        with self._lock:
            return self._is_initialized_locked()

    def _is_initialized_locked(self) -> bool:
        return self.is_env_managed or bool(
            self._state.get("password_hash") and self._state.get("password_salt")
        )

    def _verify_password_snapshot(
        self, password: str, salt_b64: str, expected_hash: str
    ) -> bool:
        if self.is_env_managed and self.env_password is not None:
            return hmac.compare_digest(
                password.encode("utf-8"), self.env_password.encode("utf-8")
            )
        if not salt_b64 or not expected_hash:
            return False
        salt = base64.b64decode(salt_b64)
        candidate = _hash_password(password, salt)
        return hmac.compare_digest(candidate, expected_hash)

    def _prune_attempts_locked(self, client_ip: str, now: float) -> List[float]:
        attempts = [
            ts
            for ts in self._failed_attempts.get(client_ip, [])
            if now - ts < RATE_LIMIT_WINDOW_SECONDS
        ]
        if attempts:
            self._failed_attempts[client_ip] = attempts
        else:
            self._failed_attempts.pop(client_ip, None)
        return attempts

    def _evict_if_oversized_locked(self, now: float) -> None:
        if len(self._failed_attempts) <= MAX_TRACKED_IPS:
            return
        stale_ips = [
            ip
            for ip, stamps in self._failed_attempts.items()
            if not any(now - ts < RATE_LIMIT_WINDOW_SECONDS for ts in stamps)
        ]
        for ip in stale_ips:
            self._failed_attempts.pop(ip, None)
        while len(self._failed_attempts) > MAX_TRACKED_IPS:
            oldest_ip = next(iter(self._failed_attempts))
            self._failed_attempts.pop(oldest_ip, None)

    def is_rate_limited(self, client_ip: str) -> bool:
        with self._lock:
            return len(self._prune_attempts_locked(client_ip, time.time())) >= RATE_LIMIT_MAX_ATTEMPTS

    def setup_password(self, password: str) -> Tuple[bool, Optional[str]]:
        if len(password) < MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        salt = secrets.token_bytes(16)
        derived = _hash_password(password, salt)
        with self._lock:
            if self._is_initialized_locked():
                return False, "Password is already configured."
            self._state["password_salt"] = base64.b64encode(salt).decode("ascii")
            self._state["password_hash"] = derived
            if not self._state.get("session_secret"):
                self._state["session_secret"] = secrets.token_hex(32)
            self._persist_state_locked()
            return True, None

    def change_password(
        self, current_password: str, new_password: str
    ) -> Tuple[bool, Optional[str]]:
        if self.is_env_managed:
            return False, "Password is managed via the LED_MATRIX_PASSWORD environment variable."
        if len(new_password) < MIN_PASSWORD_LENGTH:
            return False, f"New password must be at least {MIN_PASSWORD_LENGTH} characters."

        with self._lock:
            if not self._is_initialized_locked():
                return False, "Password has not been set up yet."
            salt_b64 = self._state["password_salt"]
            expected_hash = self._state["password_hash"]

        if not self._verify_password_snapshot(current_password, salt_b64, expected_hash):
            return False, "Current password is incorrect."

        new_salt = secrets.token_bytes(16)
        new_hash = _hash_password(new_password, new_salt)
        with self._lock:
            self._state["password_salt"] = base64.b64encode(new_salt).decode("ascii")
            self._state["password_hash"] = new_hash
            # Rotate session secret to invalidate older sessions elsewhere
            self._state["session_secret"] = secrets.token_hex(32)
            self._persist_state_locked()
        return True, None

    def authenticate(self, password: str, client_ip: str) -> Tuple[bool, Optional[str]]:
        now = time.time()
        with self._lock:
            if not self._is_initialized_locked():
                return False, "Password has not been set up yet."
            attempts = self._prune_attempts_locked(client_ip, now)
            if len(attempts) >= RATE_LIMIT_MAX_ATTEMPTS:
                return False, "Too many failed login attempts. Please wait a few minutes."
            # Reserve attempt slot before releasing lock for PBKDF2 so concurrent bursts can't bypass limit
            self._evict_if_oversized_locked(now)
            self._failed_attempts.setdefault(client_ip, []).append(now)
            salt_b64 = self._state.get("password_salt", "")
            expected_hash = self._state.get("password_hash", "")

        ok = self._verify_password_snapshot(password, salt_b64, expected_hash)
        if not ok:
            return False, "Invalid password."

        with self._lock:
            self._failed_attempts.pop(client_ip, None)
        return True, None

    def create_session_token(self) -> str:
        with self._lock:
            secret = self._state["session_secret"]
        payload = {
            "sub": "admin",
            "iat": int(time.time()),
            "exp": int(time.time()) + self.session_ttl,
            "nonce": secrets.token_hex(8),
        }
        payload_b64 = _b64url_encode(
            json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
        )
        signature = hmac.new(
            secret.encode("utf-8"),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{payload_b64}.{_b64url_encode(signature)}"

    def verify_session_token(self, token: Optional[str]) -> Optional[Dict[str, object]]:
        if not token or "." not in token:
            return None
        with self._lock:
            secret = self._state["session_secret"]
        try:
            payload_b64, sig_b64 = token.split(".", 1)
            expected_sig = hmac.new(
                secret.encode("utf-8"),
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
            "SameSite=Strict",
            f"Max-Age={self.session_ttl}",
        ]
        if secure:
            parts.append("Secure")
        return "; ".join(parts)

    def build_clear_cookie_header(self, *, secure: bool = False) -> str:
        parts = [
            f"{SESSION_COOKIE_NAME}=",
            "Path=/",
            "HttpOnly",
            "SameSite=Strict",
            "Max-Age=0",
        ]
        if secure:
            parts.append("Secure")
        return "; ".join(parts)
