"""Abstract persistence interface and SQLite backend."""

from __future__ import annotations

import json
import sqlite3
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def new_id() -> str:
    """Generate a short unique ID."""
    return uuid.uuid4().hex[:8]


@dataclass
class Document:
    """A stored document — the universal unit of persistence."""

    id: str
    collection: str
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class PersistenceBackend(ABC):
    """Abstract persistence interface.

    Operations:
        write  — upsert a document into a collection
        read   — fetch one document by id
        query  — fetch documents from a collection, optionally filtered
        delete — remove a document by id
    """

    @abstractmethod
    def write(
        self,
        collection: str,
        doc_id: str,
        data: dict,
        metadata: Optional[dict] = None,
    ) -> Document: ...

    @abstractmethod
    def read(self, collection: str, doc_id: str) -> Optional[Document]: ...

    @abstractmethod
    def query(
        self,
        collection: str,
        *,
        filter_metadata: Optional[dict] = None,
        order_by: str = "created_at",
        limit: int = 100,
    ) -> list[Document]: ...

    @abstractmethod
    def delete(self, collection: str, doc_id: str) -> bool: ...


class SQLiteBackend(PersistenceBackend):
    """SQLite implementation — single 'documents' table, JSON columns."""

    def __init__(self, db_path: str | Path):
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT NOT NULL,
                collection TEXT NOT NULL,
                data TEXT NOT NULL DEFAULT '{}',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (collection, id)
            )
            """
        )
        self._db.commit()

    def _row_to_doc(self, row: sqlite3.Row) -> Document:
        return Document(
            id=row["id"],
            collection=row["collection"],
            data=json.loads(row["data"]),
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def write(self, collection, doc_id, data, metadata=None):
        now = datetime.now().isoformat()
        meta = metadata or {}

        existing = self.read(collection, doc_id)
        if existing:
            created = existing.created_at
            merged_meta = {**existing.metadata, **meta}
        else:
            created = now
            merged_meta = meta

        self._db.execute(
            """
            INSERT OR REPLACE INTO documents
                (id, collection, data, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                collection,
                json.dumps(data),
                json.dumps(merged_meta),
                created,
                now,
            ),
        )
        self._db.commit()

        return Document(
            id=doc_id,
            collection=collection,
            data=data,
            metadata=merged_meta,
            created_at=created,
            updated_at=now,
        )

    def read(self, collection, doc_id):
        row = self._db.execute(
            "SELECT * FROM documents WHERE collection = ? AND id = ?",
            (collection, doc_id),
        ).fetchone()
        if not row:
            return None
        return self._row_to_doc(row)

    def query(self, collection, *, filter_metadata=None, order_by="created_at", limit=100):
        sql = "SELECT * FROM documents WHERE collection = ?"
        params: list[Any] = [collection]

        if filter_metadata:
            for key, value in filter_metadata.items():
                sql += " AND json_extract(metadata, ?) = ?"
                params.append(f"$.{key}")
                params.append(json.dumps(value) if isinstance(value, (dict, list)) else value)

        if order_by in ("created_at", "updated_at", "id"):
            sql += f" ORDER BY {order_by}"

        sql += " LIMIT ?"
        params.append(limit)

        rows = self._db.execute(sql, params).fetchall()
        return [self._row_to_doc(r) for r in rows]

    def delete(self, collection, doc_id):
        cursor = self._db.execute(
            "DELETE FROM documents WHERE collection = ? AND id = ?",
            (collection, doc_id),
        )
        self._db.commit()
        return cursor.rowcount > 0
