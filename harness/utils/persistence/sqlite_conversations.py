import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[2] / "conversations.db"


class SQLiteConversationRepository:
    def __init__(self, db_path=DB_PATH):
        self.db = sqlite3.connect(str(db_path))
        self.db.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                name TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                metadata TEXT,
                position INTEGER,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
            """
        )
        columns = {
            row["name"]
            for row in self.db.execute("PRAGMA table_info(messages)").fetchall()
        }
        if "metadata" not in columns:
            self.db.execute("ALTER TABLE messages ADD COLUMN metadata TEXT")
        self.db.commit()

    def create_conversation(self, name: str) -> str:
        cid = uuid.uuid4().hex[:8]
        now = datetime.now().isoformat()
        self.db.execute(
            "INSERT INTO conversations (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (cid, name, now, now),
        )
        self.db.commit()
        return cid

    def list_conversations(self) -> list[dict]:
        rows = self.db.execute(
            """
            SELECT c.id, c.name, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def load_messages(self, conversation_id: str) -> list[dict] | None:
        row = self.db.execute(
            "SELECT id FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if not row:
            return None

        rows = self.db.execute(
            "SELECT role, content, metadata FROM messages WHERE conversation_id = ? ORDER BY position",
            (conversation_id,),
        ).fetchall()
        messages = []
        for row in rows:
            message = {"role": row["role"], "content": row["content"]}
            if row["metadata"]:
                metadata = json.loads(row["metadata"])
                if isinstance(metadata, dict):
                    message.update(metadata)
            messages.append(message)
        return messages

    def save_messages(self, conversation_id: str, messages: list[dict]) -> None:
        self.db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        for index, message in enumerate(messages):
            role = message.get("role", "")
            content = message.get("content", "")
            metadata = {
                key: value
                for key, value in message.items()
                if key not in {"role", "content"}
            }
            self.db.execute(
                """
                INSERT INTO messages (conversation_id, role, content, metadata, position)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    str(role),
                    str(content),
                    json.dumps(metadata) if metadata else None,
                    index,
                ),
            )
        now = datetime.now().isoformat()
        self.db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        self.db.commit()

    def delete_conversation(self, conversation_id: str) -> None:
        self.db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        self.db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        self.db.commit()

    def rename_conversation(self, conversation_id: str, name: str) -> None:
        self.db.execute(
            "UPDATE conversations SET name = ? WHERE id = ?",
            (name, conversation_id),
        )
        self.db.commit()
