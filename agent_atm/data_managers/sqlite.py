from datetime import datetime
import json
import sqlite3
import threading
from typing import List, Optional
from agent_atm.context import TokenEvent
from agent_atm.data_managers.base import BaseDataManager

class SqliteManager(BaseDataManager):
    """Persistent SQLite DataManager implementation for single-server state retention."""
    
    def __init__(self, db_path: str = "agent_atm.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if old table exists with outdated schema 'tags'
            cursor.execute("PRAGMA table_info(token_events)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if columns and "tags" in columns:
                # Recreate the table to migrate schema for version 0.1.0 refactoring
                cursor.execute("DROP TABLE IF EXISTS token_events")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    model_id TEXT NOT NULL,
                    username TEXT,
                    session_id TEXT,
                    app_id TEXT,
                    hostname TEXT,
                    _additional_metadata_tags TEXT,
                    _additional_metadata_config TEXT
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_token_events_filters ON token_events (
                    app_id, username, session_id, timestamp
                )
            """)
            conn.commit()
            conn.close()

    def save(self, event: TokenEvent) -> None:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO token_events (
                    timestamp, event_type, token_count, model_id, username, session_id, app_id, hostname,
                    _additional_metadata_tags, _additional_metadata_config
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp.isoformat(),
                event.event_type,
                event.token_count,
                event.model_id,
                event.username,
                event.session_id,
                event.app_id,
                event.hostname,
                json.dumps(event._additional_metadata_tags),
                json.dumps(event._additional_metadata_config)
            ))
            conn.commit()
            conn.close()

    def get_usage(
        self, 
        app_id: Optional[str] = None, 
        username: Optional[str] = None, 
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        query = "SELECT SUM(token_count) FROM token_events WHERE 1=1"
        params = []

        if app_id:
            query += " AND app_id = ?"
            params.append(app_id)
        if username:
            query += " AND username = ?"
            params.append(username)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            conn.close()
            
        return result[0] if result and result[0] is not None else 0

    def get_all_events(self) -> List[TokenEvent]:
        """Retrieve all events from the database. Helper for the dashboard/daemon server."""
        query = """
            SELECT timestamp, event_type, token_count, model_id, username, session_id, app_id, hostname, 
                   _additional_metadata_tags, _additional_metadata_config 
            FROM token_events 
            ORDER BY timestamp DESC
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

        events = []
        for row in rows:
            try:
                tags = json.loads(row[8]) if row[8] else []
            except Exception:
                tags = []
                
            try:
                config = json.loads(row[9]) if row[9] else {}
            except Exception:
                config = {}
                
            events.append(TokenEvent(
                timestamp=datetime.fromisoformat(row[0]),
                event_type=row[1],
                token_count=row[2],
                model_id=row[3],
                username=row[4],
                session_id=row[5],
                app_id=row[6],
                hostname=row[7],
                _additional_metadata_tags=tags,
                _additional_metadata_config=config
            ))
        return events
