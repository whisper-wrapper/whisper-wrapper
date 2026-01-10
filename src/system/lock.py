"""Single instance lock helpers."""

import fcntl
import os
from pathlib import Path
from typing import Optional


def acquire_lock(lock_file: Path) -> Optional[object]:
    try:
        lock = open(lock_file, "w")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock.write(str(os.getpid()))
        lock.flush()
        return lock
    except (IOError, OSError):
        return None


def release_lock(lock: Optional[object], lock_file: Path):
    if lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()
            lock_file.unlink(missing_ok=True)
        except Exception:
            pass
