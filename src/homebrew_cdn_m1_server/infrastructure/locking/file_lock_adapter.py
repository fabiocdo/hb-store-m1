from __future__ import annotations

from filelock import FileLock, Timeout

from homebrew_cdn_m1_server.domain.protocols.lock_port import LockPort


class FileLockAdapter(LockPort):
    def __init__(self, lock_path: str, timeout_seconds: float = 0.0) -> None:
        self._lock = FileLock(lock_path)
        self._timeout_seconds = float(timeout_seconds)
        self._held = False

    def acquire(self) -> bool:
        try:
            self._lock.acquire(timeout=self._timeout_seconds)
            self._held = True
            return True
        except Timeout:
            return False

    def release(self) -> None:
        if not self._held:
            return
        self._held = False
        self._lock.release()
