from datetime import datetime
import threading
from typing import List, Optional
from agent_atm.context import TokenEvent
from agent_atm.data_managers.base import BaseDataManager

class InMemoryManager(BaseDataManager):
    """Thread-safe in-memory DataManager implementation."""
    
    def __init__(self):
        self._events: List[TokenEvent] = []
        self._lock = threading.Lock()

    def save(self, event: TokenEvent) -> None:
        with self._lock:
            self._events.append(event)

    def get_usage(
        self, 
        app_id: Optional[str] = None, 
        username: Optional[str] = None, 
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        total = 0
        with self._lock:
            for event in self._events:
                # Filter by time window
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                
                # Filter by metadata fields
                if app_id and event.app_id != app_id:
                    continue
                if username and event.username != username:
                    continue
                if session_id and event.session_id != session_id:
                    continue
                
                total += event.token_count
        return total
