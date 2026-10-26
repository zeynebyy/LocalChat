import sqlite3
import os
from datetime import datetime

# -----------------------------
# Genel Ayarlar
# -----------------------------
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chat_history.db"))


def _get_connection():
    """SQLite bağlantısı oluşturur."""
    return sqlite3.connect(DB_PATH)


# -----------------------------
# Şema Oluşturma
# -----------------------------
def create_tables():
    """Uygulama ilk çalıştığında tablo(ları) oluşturur (idempotent)."""
    conn = _get_connection()
    cur = conn.cursor()

    # Konuşmalar tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            last_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            favorite INTEGER DEFAULT 0,
            archived INTEGER DEFAULT 0
        )
    """)

    # Mesajlar tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            favorite INTEGER DEFAULT 0,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)

    # Gelişmiş ayarlar tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT UNIQUE NOT NULL,
            behavior TEXT,
            temperature REAL DEFAULT 0.7,
            top_p REAL DEFAULT 0.9,
            top_k INTEGER DEFAULT 40,
            repetition_penalty REAL DEFAULT 1.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# CRUD Yardımcıları
# -----------------------------

def save_message(conversation_id: str, role: str, message: str, timestamp: str | None = None):
    """Yeni bir mesaj ekler ve conversations.last_time alanını günceller."""
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO conversations(id) VALUES (?)", (conversation_id,))
    cur.execute(
        "INSERT INTO messages (conversation_id, role, message, timestamp) VALUES (?, ?, ?, ?)",
        (conversation_id, role, message, timestamp)
    )
    cur.execute(
        "UPDATE conversations SET last_time = ? WHERE id = ?",
        (timestamp, conversation_id)
    )

    conn.commit()
    conn.close()


def set_conversation_title(conversation_id: str, title: str):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id))
    conn.commit()
    conn.close()


def set_conversation_favorite(conversation_id: str, is_favorite: bool):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE conversations SET favorite = ? WHERE id = ?", (1 if is_favorite else 0, conversation_id))
    conn.commit()
    conn.close()


def get_conversations():
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, last_time, favorite
        FROM conversations
        WHERE archived = 0
        ORDER BY last_time DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "title": r["title"] if r["title"] else "Yeni Sohbet",
            "last_time": r["last_time"],
            "favorite": bool(r["favorite"]),
        }
        for r in rows
    ]


def get_messages(conversation_id: str):
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, role, message, timestamp, favorite
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
    """, (conversation_id,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "role": r["role"],
            "text": r["message"],
            "timestamp": r["timestamp"],
            "favorite": bool(r["favorite"]),
        }
        for r in rows
    ]


def delete_conversation(conversation_id: str):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()


def set_favorite_message(message_id: int, is_favorite: bool):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE messages SET favorite = ? WHERE id = ?",
        (1 if is_favorite else 0, message_id)
    )
    conn.commit()
    conn.close()


def get_favorite_messages(conversation_id: str):
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, role, message, timestamp
        FROM messages
        WHERE conversation_id = ? AND favorite = 1
        ORDER BY timestamp ASC
    """, (conversation_id,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "role": r["role"],
            "text": r["message"],
            "timestamp": r["timestamp"],
        }
        for r in rows
    ]

# -----------------------------
# Gelişmiş Ayarlar CRUD
# -----------------------------

def save_settings(conversation_id: str, behavior: str, temperature: float, top_p: float, top_k: int, repetition_penalty: float):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO settings (conversation_id, behavior, temperature, top_p, top_k, repetition_penalty)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            behavior = excluded.behavior,
            temperature = excluded.temperature,
            top_p = excluded.top_p,
            top_k = excluded.top_k,
            repetition_penalty = excluded.repetition_penalty,
            updated_at = CURRENT_TIMESTAMP
    """, (conversation_id, behavior, temperature, top_p, top_k, repetition_penalty))
    conn.commit()
    conn.close()


def get_settings(conversation_id: str):
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT behavior, temperature, top_p, top_k, repetition_penalty
        FROM settings
        WHERE conversation_id = ?
    """, (conversation_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        return {
            "behavior": row["behavior"],
            "temperature": row["temperature"],
            "top_p": row["top_p"],
            "top_k": row["top_k"],
            "repetition_penalty": row["repetition_penalty"]
        }
    return {}

# -----------------------------
# Başlangıçta tabloları oluştur
# -----------------------------
create_tables()
