from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from agent_atm.types import TokenEvent

class BaseDataManager(ABC):
    @abstractmethod
    def save(self, event: TokenEvent) -> None:
        """Persist a single token event.
        
        Args:
            event: The TokenEvent object containing metadata and token counts.
        """
        pass

    @abstractmethod
    def get_usage(
        self, 
        app_id: Optional[str] = None, 
        username: Optional[str] = None, 
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """Retrieve the total token count matching the filters in the specified time range.
        
        Args:
            app_id: Filter by application ID.
            username: Filter by user ID / name.
            session_id: Filter by session ID.
            start_time: Start timestamp filter (inclusive).
            end_time: End timestamp filter (inclusive).
            
        Returns:
            Total sum of tokens matching the filters.
        """
        pass
