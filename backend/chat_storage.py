"""
Chat storage module with session-based history management
Supports sidebar display and individual session deletion
"""

import sqlite3
import time
from pathlib import Path
from typing import List, Tuple, Optional
import logging

# Get the data directory
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
(DATA / "chats").mkdir(parents=True, exist_ok=True)

DB_PATH = DATA / "chats" / "chats.db"


def _init_db():
    """Initialize the database with session support"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Create table with session_id field
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            ts REAL NOT NULL
        )
    """)

    # Create index for faster session queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_session_id ON messages(session_id)
    """)

    # Create index for timestamp queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ts ON messages(ts DESC)
    """)

    conn.commit()
    conn.close()


# Initialize database on module load
_init_db()


def save_message(role: str, content: str, session_id: str = None):
    """
    Save a message to the database with session tracking

    Args:
        role: 'user' or 'assistant'
        content: Message content
        session_id: Session identifier (auto-generated if not provided)
    """
    if session_id is None:
        session_id = f"session_{int(time.time())}"

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO messages (session_id, role, content, ts) VALUES (?, ?, ?, ?)",
        (session_id, role, content, time.time())
    )

    conn.commit()
    conn.close()

    logging.info(f"Saved {role} message to session {session_id}")


def history(limit: int = 100, session_id: Optional[str] = None) -> List[Tuple[str, str, float, str]]:
    """
    Get chat history, optionally filtered by session

    Args:
        limit: Maximum number of messages to return
        session_id: If provided, only return messages from this session

    Returns:
        List of tuples: (role, content, timestamp, session_id)
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    if session_id:
        cursor.execute(
            "SELECT role, content, ts, session_id FROM messages WHERE session_id = ? ORDER BY ts DESC LIMIT ?",
            (session_id, limit)
        )
    else:
        cursor.execute(
            "SELECT role, content, ts, session_id FROM messages ORDER BY ts DESC LIMIT ?",
            (limit,)
        )

    rows = cursor.fetchall()
    conn.close()

    # Return in chronological order (oldest first)
    return list(reversed(rows))


def get_chat_sessions() -> List[dict]:
    """
    Get list of all chat sessions for sidebar display

    Returns:
        List of session dicts with: session_id, last_message_ts, message_count, preview
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Get session info with last message time and count
    cursor.execute("""
        SELECT
            session_id,
            MAX(ts) as last_ts,
            COUNT(*) as msg_count,
            (SELECT content FROM messages m2
             WHERE m2.session_id = m1.session_id
             AND m2.role = 'user'
             ORDER BY ts ASC LIMIT 1) as first_user_msg
        FROM messages m1
        GROUP BY session_id
        ORDER BY last_ts DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    sessions = []
    for session_id, last_ts, msg_count, first_msg in rows:
        # Create a preview from the first user message
        preview = first_msg[:50] + "..." if first_msg and len(first_msg) > 50 else (first_msg or "Empty session")

        sessions.append({
            "session_id": session_id,
            "last_message_ts": last_ts,
            "message_count": msg_count,
            "preview": preview,
            "created_at": last_ts  # For sorting
        })

    return sessions


def delete_chat_session(session_id: str) -> int:
    """
    Delete all messages from a specific session

    Args:
        session_id: Session to delete

    Returns:
        Number of messages deleted
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    logging.info(f"Deleted session {session_id}: {deleted_count} messages")
    return deleted_count


def clear_all_history() -> int:
    """
    Clear all chat history

    Returns:
        Number of messages deleted
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("DELETE FROM messages")

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    logging.info(f"Cleared all history: {deleted_count} messages")
    return deleted_count


def get_session_stats(session_id: str) -> dict:
    """
    Get statistics for a specific session

    Args:
        session_id: Session to analyze

    Returns:
        Dict with session statistics
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total_messages,
            SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
            SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
            MIN(ts) as first_message_ts,
            MAX(ts) as last_message_ts
        FROM messages
        WHERE session_id = ?
    """, (session_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "session_id": session_id,
            "total_messages": row[0],
            "user_messages": row[1],
            "assistant_messages": row[2],
            "first_message_ts": row[3],
            "last_message_ts": row[4],
            "duration_seconds": (row[4] - row[3]) if row[3] and row[4] else 0
        }
    else:
        return {
            "session_id": session_id,
            "total_messages": 0,
            "error": "Session not found"
        }
