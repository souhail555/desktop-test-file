import sqlite3
from pathlib import Path
from typing import Any

from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parents[2] / "ai_agent.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                model TEXT DEFAULT 'gpt-4o-mini',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        columns = [row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()]
        if "model" not in columns:
            conn.execute("ALTER TABLE messages ADD COLUMN model TEXT DEFAULT 'gpt-4o-mini'")
        conn.commit()


def ensure_default_user() -> None:
    if get_user("admin") is None:
        add_user("admin", "admin123")


def add_user(username: str, password: str) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "username": username}


def get_user(username: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def save_message(user_id: int, prompt: str, response: str, model: str = "gpt-4o-mini") -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (user_id, prompt, response, model) VALUES (?, ?, ?, ?)",
            (user_id, prompt, response, model),
        )
        conn.commit()


def get_messages_for_user(user_id: int, limit: int = 20):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, prompt, response, model, created_at
            FROM messages
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def get_dashboard_stats():
    with get_connection() as conn:
        user_count = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
        message_count = conn.execute("SELECT COUNT(*) AS total FROM messages").fetchone()["total"]
        newest = conn.execute(
            "SELECT username FROM users ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return {
            "user_count": user_count,
            "message_count": message_count,
            "latest_user": newest["username"] if newest else "None",
        }
