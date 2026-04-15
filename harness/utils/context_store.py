"""Mmap-backed context store for agent context switching.

Stores serialized message lists in a memory-mapped file so the Python
heap is freed while another agent runs.  Data stays in OS page cache
— fast to read back, no GC pressure.
"""

import json
import mmap
import os
from pathlib import Path


class ContextStore:
    """Single-slot mmap store keyed by a string name."""

    def __init__(self, path: str | Path, size: int = 4 * 1024 * 1024):
        self._path = str(path)
        self._size = size
        self._fd = os.open(self._path, os.O_RDWR | os.O_CREAT)
        os.ftruncate(self._fd, size)
        self._mm = mmap.mmap(self._fd, size)

    def save(self, key: str, messages: list[dict]):
        """Serialize messages into the mmap region."""
        data = json.dumps(messages).encode("utf-8")
        key_bytes = key.encode("utf-8")

        # Layout: [4B key_len][key][4B data_len][data]
        payload = (
            len(key_bytes).to_bytes(4, "little")
            + key_bytes
            + len(data).to_bytes(4, "little")
            + data
        )

        if len(payload) > self._size:
            self._mm.close()
            self._size = len(payload) * 2
            os.ftruncate(self._fd, self._size)
            self._mm = mmap.mmap(self._fd, self._size)

        self._mm.seek(0)
        self._mm.write(payload)

    def load(self, key: str) -> list[dict] | None:
        """Deserialize messages from the mmap region."""
        self._mm.seek(0)

        raw_key_len = self._mm.read(4)
        if len(raw_key_len) < 4:
            return None
        key_len = int.from_bytes(raw_key_len, "little")
        if key_len == 0:
            return None

        stored_key = self._mm.read(key_len).decode("utf-8")
        if stored_key != key:
            return None

        data_len = int.from_bytes(self._mm.read(4), "little")
        data = self._mm.read(data_len)
        return json.loads(data)

    def close(self):
        self._mm.close()
        os.close(self._fd)
