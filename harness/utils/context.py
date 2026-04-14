import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from .prompts import SYSTEM_PROMPT
from harness.config import load_config


_config = load_config()
DB_PATH = Path(_config.db_path) if _config.db_path else Path(__file__).parent.parent / "conversations.db"


class ConversationManager:
    def __init__(self, db_path=DB_PATH):
        self.db = sqlite3.connect(str(db_path))
        self.db.row_factory = sqlite3.Row
        self._current = None
        self._init_db()

    def _init_db(self):
        self.db.executescript("""
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
                position INTEGER,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
        """)
        self.db.commit()

    @property
    def current(self):
        return self._current

    def new(self, name=None):
        cid = uuid.uuid4().hex[:8]
        if name is None:
            count = self.db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            name = f"Chat {count + 1}"
        now = datetime.now().isoformat()
        self.db.execute(
            "INSERT INTO conversations (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (cid, name, now, now),
        )
        self.db.commit()
        self._current = cid
        return cid

    def list(self):
        rows = self.db.execute("""
            SELECT c.id, c.name, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

    def load(self, conversation_id):
        row = self.db.execute(
            "SELECT id FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if not row:
            return None

        self._current = conversation_id
        messages = [SYSTEM_PROMPT.copy()]

        rows = self.db.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY position",
            (conversation_id,),
        ).fetchall()

        for r in rows:
            messages.append({"role": r["role"], "content": r["content"]})

        return messages

    def save(self, conversation_id, messages):
        # Skip system prompt when saving
        to_save = [m for m in messages if m.get("role") != "system"]

        self.db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        for i, msg in enumerate(to_save):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if hasattr(msg, "content"):
                content = msg.content if hasattr(msg, "content") else str(msg)
                role = msg.role if hasattr(msg, "role") else role
            self.db.execute(
                "INSERT INTO messages (conversation_id, role, content, position) VALUES (?, ?, ?, ?)",
                (conversation_id, str(role), str(content), i),
            )
        now = datetime.now().isoformat()
        self.db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
        )
        self.db.commit()

    def delete(self, conversation_id):
        self.db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        self.db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        self.db.commit()
        if self._current == conversation_id:
            self._current = None

    def rename(self, conversation_id, name):
        self.db.execute(
            "UPDATE conversations SET name = ? WHERE id = ?", (name, conversation_id)
        )
        self.db.commit()
