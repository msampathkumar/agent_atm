from datetime import datetime, timedelta
import json
import os
import sqlite3
import threading
from typing import Any, Optional
from agent_atm.cache.base import BaseStore

class DiskCacheStore(BaseStore):
    """Thread-safe SQLite-based local cache store with automatic TTL validation."""

    def __init__(self, db_path: str = ".agent_atm_cache.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TEXT
                )
            """)
            conn.commit()
            conn.close()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value, expires_at FROM cache WHERE key = ?", (key,))
            row = cursor.fetchone()
            conn.close()

        if not row:
            return None

        val_str, expires_at_str = row
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now() > expires_at:
                self.delete(key)
                return None

        try:
            return json.loads(val_str)
        except Exception:
            return val_str

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        try:
            val_str = json.dumps(value)
        except Exception:
            val_str = str(value)

        expires_at_str = None
        if ttl is not None:
            expires_at_str = (datetime.now() + timedelta(seconds=ttl)).isoformat()

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cache (key, value, expires_at)
                VALUES (?, ?, ?)
            """, (key, val_str, expires_at_str))
            conn.commit()
            conn.close()

    def delete(self, key: str) -> None:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
            conn.close()

    def clear(self) -> None:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache")
            conn.commit()
            conn.close()
