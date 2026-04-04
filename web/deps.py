from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

from paths import get_data_file_path
from store import StoreJSON

_lock = threading.Lock()
_store: StoreJSON | None = None


@contextmanager
def store_ctx() -> Iterator[StoreJSON]:
    """同一 JSON を Tk 版と共有。リクエスト単位でロック（単一プロセス想定）。"""
    global _store
    with _lock:
        if _store is None:
            _store = StoreJSON(get_data_file_path())
        yield _store
