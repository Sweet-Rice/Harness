import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from harness.utils.config import SETTINGS
from harness.utils.context.models import ThreadRecord
from harness.utils.persistence.serialization import deserialize_messages, serialize_messages

DB_PATH = Path(SETTINGS.db_path)


class SQLiteConversationRepository:
    def __init__(self, db_path=DB_PATH):
        self.db = sqlite3.connect(str(db_path))
        self.db.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                name TEXT,
                thread_type TEXT NOT NULL,
                mode TEXT NOT NULL,
                source TEXT,
                client_id TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT,
                content TEXT,
                message_type TEXT NOT NULL,
                tool_name TEXT,
                source TEXT,
                tool_calls TEXT,
                metadata TEXT NOT NULL,
                position INTEGER,
                FOREIGN KEY (thread_id) REFERENCES threads(id)
            );
            """
        )
        self.db.commit()

    def _row_to_thread(self, row) -> ThreadRecord:
        return ThreadRecord(
            id=row["id"],
            name=row["name"],
            thread_type=row["thread_type"],
            mode=row["mode"],
            source=row["source"],
            client_id=row["client_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            message_count=row["message_count"] if "message_count" in row.keys() else 0,
        )

    def create_thread(
        self,
        name: str,
        *,
        thread_type: str,
        mode: str,
        source: str | None,
        client_id: str | None,
    ) -> ThreadRecord:
        cid = uuid.uuid4().hex[:8]
        now = datetime.now().isoformat()
        self.db.execute(
            """
            INSERT INTO threads (id, name, thread_type, mode, source, client_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (cid, name, thread_type, mode, source, client_id, now, now),
        )
        self.db.commit()
        return ThreadRecord(
            id=cid,
            name=name,
            thread_type=thread_type,
            mode=mode,
            source=source,
            client_id=client_id,
            created_at=now,
            updated_at=now,
        )

    def list_threads(
        self,
        *,
        source: str | None = None,
        client_id: str | None = None,
        include_global: bool = True,
    ) -> list[ThreadRecord]:
        conditions = []
        params: list[str] = []

        if source is not None and client_id is not None:
            if include_global:
                conditions.append(
                    "(t.thread_type = 'global_thread' OR (t.thread_type = 'client_scratch' AND t.source = ? AND t.client_id = ?))"
                )
                params.extend([source, client_id])
            else:
                conditions.append("(t.thread_type = 'client_scratch' AND t.source = ? AND t.client_id = ?)")
                params.extend([source, client_id])
        elif not include_global:
            conditions.append("t.thread_type = 'client_scratch'")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self.db.execute(
            f"""
            SELECT t.id, t.name, t.thread_type, t.mode, t.source, t.client_id, t.created_at, t.updated_at,
                   COUNT(m.id) as message_count
            FROM threads t
            LEFT JOIN messages m ON m.thread_id = t.id
            {where_clause}
            GROUP BY t.id
            ORDER BY t.updated_at DESC
            """,
            params,
        ).fetchall()
        return [self._row_to_thread(row) for row in rows]

    def get_thread(self, thread_id: str) -> ThreadRecord | None:
        row = self.db.execute(
            """
            SELECT t.id, t.name, t.thread_type, t.mode, t.source, t.client_id, t.created_at, t.updated_at,
                   COUNT(m.id) as message_count
            FROM threads t
            LEFT JOIN messages m ON m.thread_id = t.id
            WHERE t.id = ?
            GROUP BY t.id
            """,
            (thread_id,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_thread(row)

    def find_thread_by_identity(
        self,
        *,
        thread_type: str,
        source: str | None,
        client_id: str | None,
    ) -> ThreadRecord | None:
        row = self.db.execute(
            """
            SELECT t.id, t.name, t.thread_type, t.mode, t.source, t.client_id, t.created_at, t.updated_at,
                   COUNT(m.id) as message_count
            FROM threads t
            LEFT JOIN messages m ON m.thread_id = t.id
            WHERE t.thread_type = ? AND t.source IS ? AND t.client_id IS ?
            GROUP BY t.id
            ORDER BY t.updated_at DESC
            LIMIT 1
            """,
            (thread_type, source, client_id),
        ).fetchone()
        if not row:
            return None
        return self._row_to_thread(row)

    def load_thread_messages(self, thread_id: str):
        rows = self.db.execute(
            """
            SELECT role, content, message_type, tool_name, source, tool_calls, metadata
            FROM messages
            WHERE thread_id = ?
            ORDER BY position
            """,
            (thread_id,),
        ).fetchall()
        normalized_rows = []
        for row in rows:
            normalized_rows.append(
                {
                    "role": row["role"],
                    "content": row["content"],
                    "message_type": row["message_type"],
                    "tool_name": row["tool_name"],
                    "source": row["source"],
                    "tool_calls": json.loads(row["tool_calls"]) if row["tool_calls"] else [],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
            )
        return deserialize_messages(normalized_rows)

    def save_thread_messages(self, thread_id: str, messages) -> None:
        if thread_id is None:
            raise ValueError("thread_id cannot be None")
        serialized = serialize_messages(messages)
        self.db.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
        for index, message in enumerate(serialized):
            self.db.execute(
                """
                INSERT INTO messages (
                    thread_id, role, content, message_type, tool_name, source, tool_calls, metadata, position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    message.role,
                    message.content,
                    message.message_type,
                    message.tool_name,
                    message.source,
                    json.dumps(message.tool_calls) if message.tool_calls else None,
                    json.dumps(message.metadata or {}),
                    index,
                ),
            )
        now = datetime.now().isoformat()
        self.db.execute(
            "UPDATE threads SET updated_at = ? WHERE id = ?",
            (now, thread_id),
        )
        self.db.commit()

    def delete_thread(self, thread_id: str) -> None:
        self.db.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
        self.db.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
        self.db.commit()

    def rename_thread(self, thread_id: str, name: str) -> None:
        self.db.execute(
            "UPDATE threads SET name = ? WHERE id = ?",
            (name, thread_id),
        )
        self.db.commit()
