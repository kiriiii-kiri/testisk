import sqlite3
import os

DB_PATH = "snake_game.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            record INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user_record(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT record FROM players WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_user_record(user_id, username, score):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    current_record = get_user_record(user_id)
    if score > current_record:
        cursor.execute("""
            INSERT OR REPLACE INTO players (user_id, username, record)
            VALUES (?, ?, ?)
        """, (user_id, username, score))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_top_players(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username, record FROM players ORDER BY record DESC LIMIT ?", (limit,))
    results = cursor.fetchall()
    conn.close()
    return results
