# utils/database.py
import sqlite3
import os
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "connections.db")

def get_connection(db_path=None):
    """Returns a SQLite connection with timeout and row factory."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    """Initializes the database schema for storing DroidCam IP connections."""
    path = db_path or DEFAULT_DB_PATH
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS droidcam_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                connected_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Connected',
                notes TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_droidcam_ip 
            ON droidcam_history (ip_address)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_droidcam_time 
            ON droidcam_history (connected_at DESC)
        """)
        conn.commit()

        # Seed initial IP from config.json if database is freshly created
        cursor.execute("SELECT COUNT(*) as cnt FROM droidcam_history")
        count = cursor.fetchone()["cnt"]
        if count == 0:
            config_file = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "config.json")
            if os.path.exists(config_file):
                try:
                    import json
                    with open(config_file, "r") as f:
                        cfg = json.load(f)
                        saved = cfg.get("droidcam_ip", "").strip()
                        if saved:
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            cursor.execute("""
                                INSERT INTO droidcam_history (ip_address, connected_at, status, notes)
                                VALUES (?, ?, 'Saved', 'Imported from initial config')
                            """, (saved, now_str))
                            conn.commit()
                except Exception:
                    pass

def save_connection(ip_address, status="Connected", notes="", db_path=None):
    """
    Saves a DroidCam connection attempt or status to the database.
    Status can be 'Connected', 'Failed', 'Saved', etc.
    """
    clean_ip = str(ip_address).strip()
    if not clean_ip:
        return None

    path = db_path or DEFAULT_DB_PATH
    init_db(path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO droidcam_history (ip_address, connected_at, status, notes)
            VALUES (?, ?, ?, ?)
        """, (clean_ip, timestamp, status, notes))
        conn.commit()
        return cursor.lastrowid

def get_recent_ips(limit=10, db_path=None):
    """
    Returns a list of distinct IP strings ordered by the most recent connection time.
    Used to populate the UI dropdown / combobox.
    """
    path = db_path or DEFAULT_DB_PATH
    init_db(path)

    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ip_address, MAX(connected_at) as last_seen
            FROM droidcam_history
            GROUP BY ip_address
            ORDER BY last_seen DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [row["ip_address"] for row in rows]

def get_all_history(limit=100, db_path=None):
    """
    Retrieves full connection history records sorted from newest to oldest.
    Returns list of dicts: [{'id': ..., 'ip_address': ..., 'connected_at': ..., 'status': ..., 'notes': ...}]
    """
    path = db_path or DEFAULT_DB_PATH
    init_db(path)

    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, ip_address, connected_at, status, notes
            FROM droidcam_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def delete_record(record_id, db_path=None):
    """Deletes a single connection record by ID."""
    path = db_path or DEFAULT_DB_PATH
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM droidcam_history WHERE id = ?", (record_id,))
        conn.commit()
        return cursor.rowcount > 0

def clear_history(db_path=None):
    """Clears all connection history from the database."""
    path = db_path or DEFAULT_DB_PATH
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM droidcam_history")
        conn.commit()

def get_last_ip(db_path=None):
    """Returns the most recent IP address recorded, or None if empty."""
    recent = get_recent_ips(limit=1, db_path=db_path)
    return recent[0] if recent else None
