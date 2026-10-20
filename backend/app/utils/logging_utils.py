"""Small logging/progress helpers shared by the processing pipeline and API."""
from __future__ import annotations

import sys
import time
from contextlib import contextmanager


def log(msg: str) -> None:
    print(msg, flush=True)


def stage(step: int, total: int, msg: str) -> None:
    log(f"[{step}/{total}] {msg}")


@contextmanager
def timed(label: str):
    """Context manager that prints how long a block took."""
    start = time.time()
    log(f"    -> {label} ...")
    try:
        yield
    finally:
        elapsed = time.time() - start
        log(f"    -> {label} done in {elapsed:.1f}s")


def fatal(msg: str) -> None:
    """Print a clear, actionable error and exit -- never a raw traceback."""
    log("")
    log("=" * 70)
    log("ERROR")
    log("=" * 70)
    log(msg)
    log("=" * 70)
    sys.exit(1)
