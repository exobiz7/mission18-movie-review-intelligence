"""Write access policy for public demo safety.

Only backend/API-to-API clients can possess the server-side secret.
A token placed in public Streamlit is NOT end-user authorization.
"""

from __future__ import annotations

import ipaddress
import secrets
import threading
import time
from collections import deque

from fastapi import Depends, Request
from pydantic import SecretStr

from backend.app.config import Settings, get_settings
from backend.app.errors import ServiceError


def is_local_peer(host: str | None) -> bool:
    if host == "testclient":  # In-process Starlette TestClient only.
        return True
    if not host:
        return False
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def has_valid_bearer(header: str | None, secret: SecretStr | None) -> bool:
    """Require a single well-formed bearer header; never log/return its value."""
    if not header or not secret:
        return False
    pieces = header.split(" ")
    if len(pieces) != 2 or pieces[0] != "Bearer":
        return False
    value = pieces[1]
    expected = secret.get_secret_value()
    if len(value) > 512 or not value or not expected:
        return False
    return secrets.compare_digest(value.encode("utf-8"), expected.encode("utf-8"))


class DemoWriteLimiter:
    """Process-wide 60-second window for a single-worker educational demo.

    No client IP/header is trusted. This is a basic burst limit, not distributed
    authentication or DDoS protection. Ordinary instructor tests need no login.
    """

    def __init__(self) -> None:
        self.times: deque[float] = deque()
        self.lock = threading.Lock()

    def allow(self, limit: int, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self.lock:
            while self.times and self.times[0] <= now - 60:
                self.times.popleft()
            if len(self.times) >= limit:
                return False
            self.times.append(now)
            return True


_demo_writes = DemoWriteLimiter()


def require_write_access(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """Reject all unauthorized writes BEFORE invoking DB/inference services."""
    if settings.write_policy == "public_demo":
        if not settings.public_demo_acknowledged:
            raise ServiceError(403, "WRITE_DISABLED", "공개 체험 모드가 승인되지 않았습니다.")
        if not _demo_writes.allow(settings.demo_writes_per_minute):
            raise ServiceError(
                429, "DEMO_RATE_LIMIT", "체험 요청이 많습니다. 1분 후 다시 시도해 주세요."
            )
        return
    if settings.write_policy == "read_only":
        raise ServiceError(403, "WRITE_DISABLED", "공개 변경 기능이 비활성화되어 있습니다.")
    if settings.write_policy == "loopback":
        if not is_local_peer(request.client.host if request.client else None):
            raise ServiceError(403, "LOCAL_ONLY", "변경 작업은 로컬 개발 환경에서만 허용됩니다.")
        return
    if settings.write_policy == "token":
        if not has_valid_bearer(request.headers.get("Authorization"), settings.api_write_token):
            raise ServiceError(
                401, "AUTH_REQUIRED", "변경 요청에는 유효한 관리자 인증이 필요합니다."
            )
        return
    # Safe on unexpected future enum/value expansion.
    raise ServiceError(403, "WRITE_DISABLED", "변경 작업을 허용할 수 없습니다.")
