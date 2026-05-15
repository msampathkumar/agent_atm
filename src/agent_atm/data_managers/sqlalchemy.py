import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    and_,
)
try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from agent_atm.context import TokenEvent
from agent_atm.data_managers.base import BaseDataManager

import logging
logger = logging.getLogger("agent_atm")

Base = declarative_base()

class TokenEventModel(Base):
    __tablename__ = "token_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    event_type = Column(String(50), nullable=False)
    token_count = Column(Integer, nullable=False)
    model_id = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=True)
    app_id = Column(String(255), nullable=True)
    hostname = Column(String(255), nullable=True)
    _additional_metadata_tags = Column(Text, nullable=True)
    _additional_metadata_config = Column(Text, nullable=True)


class LimitRuleModel(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope_app = Column(String(255), nullable=False, default="*")
    scope_user = Column(String(255), nullable=False, default="*")
    scope_session = Column(String(255), nullable=False, default="*")
    minute_limit = Column(Integer, nullable=True)
    hour_limit = Column(Integer, nullable=True)
    day_limit = Column(Integer, nullable=True)
    total_limit = Column(Integer, nullable=True)
    alert_level = Column(String(50), nullable=False, default="BLOCKING")


class SQLAlchemyManager(BaseDataManager):
    """General purpose SQL Database Manager using SQLAlchemy."""

    def __init__(self, db_url: str = "sqlite:///agent_atm.db"):
        # If a simple file path is passed instead of full db_url, assume sqlite
        if "://" not in db_url:
            db_url = f"sqlite:///{db_url}"
        
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save(self, event: TokenEvent) -> None:
        session = self.Session()
        try:
            logger.debug(f"Saving TokenEvent to database: {event.token_count} tokens")
            db_event = TokenEventModel(
                timestamp=event.timestamp,
                event_type=event.event_type,
                token_count=event.token_count,
                model_id=event.model_id,
                username=event.username,
                session_id=event.session_id,
                app_id=event.app_id,
                hostname=event.hostname,
                _additional_metadata_tags=json.dumps(event._additional_metadata_tags),
                _additional_metadata_config=json.dumps(event._additional_metadata_config)
            )
            session.add(db_event)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_usage(
        self,
        app_id: Optional[str] = None,
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        session = self.Session()
        try:
            query = session.query(TokenEventModel)
            if app_id:
                query = query.filter(TokenEventModel.app_id == app_id)
            if username:
                query = query.filter(TokenEventModel.username == username)
            if session_id:
                query = query.filter(TokenEventModel.session_id == session_id)
            if start_time:
                query = query.filter(TokenEventModel.timestamp >= start_time)
            if end_time:
                query = query.filter(TokenEventModel.timestamp <= end_time)

            total = sum(row.token_count for row in query.all())
            return total
        finally:
            session.close()

    def get_usage_summary(
        self,
        app_id: Optional[str] = None,
        username: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Retrieve aggregate token consumption for 1m, 1h, 1d, and total in a single pass."""
        from datetime import timedelta
        now = datetime.now()
        cutoff_1m = now - timedelta(minutes=1)
        cutoff_1h = now - timedelta(hours=1)
        cutoff_1d = now - timedelta(days=1)

        session = self.Session()
        try:
            query = session.query(TokenEventModel)
            if app_id:
                query = query.filter(TokenEventModel.app_id == app_id)
            if username:
                query = query.filter(TokenEventModel.username == username)
            if session_id:
                query = query.filter(TokenEventModel.session_id == session_id)

            rows = query.all()
            total = 0
            day = 0
            hour = 0
            minute = 0

            for r in rows:
                tc = r.token_count
                total += tc
                if r.timestamp >= cutoff_1d:
                    day += tc
                    if r.timestamp >= cutoff_1h:
                        hour += tc
                        if r.timestamp >= cutoff_1m:
                            minute += tc

            return {
                "total": total,
                "day": day,
                "hour": hour,
                "minute": minute
            }
        finally:
            session.close()

    def get_all_events(self) -> List[TokenEvent]:
        session = self.Session()
        try:
            rows = session.query(TokenEventModel).order_by(TokenEventModel.timestamp.desc()).all()
            events = []
            for r in rows:
                try:
                    tags = json.loads(r._additional_metadata_tags) if r._additional_metadata_tags else []
                except Exception:
                    tags = []

                try:
                    config = json.loads(r._additional_metadata_config) if r._additional_metadata_config else {}
                except Exception:
                    config = {}

                events.append(TokenEvent(
                    timestamp=r.timestamp,
                    event_type=r.event_type,
                    token_count=r.token_count,
                    model_id=r.model_id,
                    username=r.username,
                    session_id=r.session_id,
                    app_id=r.app_id,
                    hostname=r.hostname,
                    _additional_metadata_tags=tags,
                    _additional_metadata_config=config
                ))
            return events
        finally:
            session.close()

    # --- Rule Management Queries ---

    def register_rule(
        self,
        scope_app: str = "*",
        scope_user: str = "*",
        scope_session: str = "*",
        minute_limit: Optional[int] = None,
        hour_limit: Optional[int] = None,
        day_limit: Optional[int] = None,
        total_limit: Optional[int] = None,
        alert_level: str = "BLOCKING"
    ) -> None:
        session = self.Session()
        try:
            logger.info(f"Registering database limit rule: app='{scope_app}', user='{scope_user}', session='{scope_session}'")
            db_rule = LimitRuleModel(
                scope_app=scope_app,
                scope_user=scope_user,
                scope_session=scope_session,
                minute_limit=minute_limit,
                hour_limit=hour_limit,
                day_limit=day_limit,
                total_limit=total_limit,
                alert_level=alert_level
            )
            session.add(db_rule)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_all_rules(self) -> List[Dict[str, Any]]:
        session = self.Session()
        try:
            rows = session.query(LimitRuleModel).all()
            rules = []
            for r in rows:
                rules.append({
                    "id": r.id,
                    "scope_app": r.scope_app,
                    "scope_user": r.scope_user,
                    "scope_session": r.scope_session,
                    "minute_limit": r.minute_limit,
                    "hour_limit": r.hour_limit,
                    "day_limit": r.day_limit,
                    "total_limit": r.total_limit,
                    "alert_level": r.alert_level
                })
            return rules
        finally:
            session.close()

    def clear_all_rules(self) -> None:
        session = self.Session()
        try:
            session.query(LimitRuleModel).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
