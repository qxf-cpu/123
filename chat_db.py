"""Minimal in-memory SQLite helpers for local UI preview."""
import sqlite3
import os
import json
from datetime import datetime

_DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")


def _conn():
    c = sqlite3.connect(_DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                start_time TEXT,
                last_time TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT
            )
            """
        )


def _touch_session(session_id):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _conn() as c:
        row = c.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            c.execute(
                "INSERT INTO sessions (session_id, start_time, last_time) VALUES (?, ?, ?)",
                (session_id, now, now),
            )
        else:
            c.execute(
                "UPDATE sessions SET last_time = ? WHERE session_id = ?",
                (now, session_id),
            )


def save_messages(session_id, messages):
    _touch_session(session_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _conn() as c:
        for m in messages:
            c.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, m["role"], m["content"], now),
            )
        count = c.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        c.execute(
            "UPDATE sessions SET last_time = ? WHERE session_id = ?",
            (now, session_id),
        )
    return count


def load_history(session_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    if not rows:
        return None
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def clear_history(session_id):
    with _conn() as c:
        c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))


def get_all_sessions():
    with _conn() as c:
        rows = c.execute(
            """
            SELECT s.session_id, s.title, s.start_time, s.last_time,
                   (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.session_id) AS msg_count
            FROM sessions s
            ORDER BY COALESCE(s.last_time, s.start_time) DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def set_session_title(session_id, title):
    _touch_session(session_id)
    with _conn() as c:
        c.execute("UPDATE sessions SET title = ? WHERE session_id = ?", (title, session_id))


def rename_session(session_id, title):
    set_session_title(session_id, title)


def delete_all_sessions():
    with _conn() as c:
        c.execute("DELETE FROM messages")
        c.execute("DELETE FROM sessions")


def search_sessions(keyword):
    kw = f"%{keyword.strip()}%"
    with _conn() as c:
        rows = c.execute(
            """
            SELECT DISTINCT s.session_id, s.title, s.start_time, s.last_time,
                   (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.session_id) AS msg_count
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.session_id
            WHERE s.title LIKE ? OR m.content LIKE ?
            ORDER BY COALESCE(s.last_time, s.start_time) DESC
            """,
            (kw, kw),
        ).fetchall()
    return [dict(r) for r in rows]
