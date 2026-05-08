from datetime import datetime, timedelta
import os
from typing import Dict, List, Literal, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from agent_atm.types import TokenEvent
from agent_atm.data_managers.sqlite import SqliteManager


app = FastAPI(
    title="Agent Token Manager Dashboard",
    description="Real-time token metrics, quota limit observances, and LLM telemetry."
)

# Mount static assets directory for CSS, Javascript, and HTML resources
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Resolve database path from environment or default
DB_PATH = os.environ.get("ATM_DB_PATH", "agent_atm.db")
db_manager = SqliteManager(db_path=DB_PATH)

class EventPostSchema(BaseModel):
    event_type: Literal["request", "response"] = Field(..., description="Event type: must be 'request' or 'response'")
    token_count: int = Field(..., ge=0, description="Calculated token count")
    model_id: str = Field(..., description="ID of the LLM model used")
    username: Optional[str] = None
    session_id: Optional[str] = None
    app_id: Optional[str] = None
    tags: Optional[List[str]] = None
    config: Optional[Dict[str, str]] = None

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "database": "connected"}

@app.post("/api/events", status_code=201)
def create_event(payload: EventPostSchema):
    """Endpoint for Enterprise customers to post token telemetry events from distributed backend nodes."""
    if payload.event_type not in ("request", "response"):
        raise HTTPException(status_code=400, detail="event_type must be either 'request' or 'response'")
        
    event = TokenEvent(
        timestamp=datetime.now(),
        event_type=payload.event_type,
        token_count=payload.token_count,
        model_id=payload.model_id,
        username=payload.username,
        session_id=payload.session_id,
        app_id=payload.app_id,
        _additional_metadata_tags=payload.tags or [],
        _additional_metadata_config=payload.config or {}
    )
    db_manager.save(event)
    return {"status": "success", "message": "Event successfully logged to backend telemetry store."}

@app.get("/api/events")

def get_events(limit: int = Query(100, description="Maximum number of events to return")):
    events = db_manager.get_all_events()
    # Return raw records in a serializable form
    serialized = []
    for ev in events[:limit]:
        serialized.append({
            "timestamp": ev.timestamp.isoformat(),
            "event_type": ev.event_type,
            "token_count": ev.token_count,
            "model_id": ev.model_id,
            "username": ev.username or "Anonymous",
            "session_id": ev.session_id or "N/A",
            "app_id": ev.app_id or "N/A",
            "hostname": ev.hostname or "Unknown",
            "tags": ev._additional_metadata_tags,
            "config": ev._additional_metadata_config
        })

    return serialized

@app.get("/api/metrics")
def get_metrics():
    events = db_manager.get_all_events()
    total_requests = sum(1 for e in events if e.event_type == "request")
    total_responses = sum(1 for e in events if e.event_type == "response")
    total_tokens = sum(e.token_count for e in events)
    
    # Calculate aggregates by model
    model_counts = {}
    for e in events:
        model_counts[e.model_id] = model_counts.get(e.model_id, 0) + e.token_count
        
    # Calculate aggregates by app
    app_counts = {}
    for e in events:
        app_name = e.app_id or "Default"
        app_counts[app_name] = app_counts.get(app_name, 0) + e.token_count

    # Calculate aggregates by user
    user_counts = {}
    for e in events:
        u_name = e.username or "Anonymous"
        user_counts[u_name] = user_counts.get(u_name, 0) + e.token_count

    # Token consumption over time (last 7 days breakdown)
    now = datetime.now()
    daily_usage = {}
    for i in range(7):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_usage[day] = 0

    for e in events:
        day_str = e.timestamp.strftime("%Y-%m-%d")
        if day_str in daily_usage:
            daily_usage[day_str] += e.token_count

    return {
        "stats": {
            "total_events": len(events),
            "total_requests": total_requests,
            "total_responses": total_responses,
            "total_tokens": total_tokens
        },
        "by_model": model_counts,
        "by_app": app_counts,
        "by_user": user_counts,
        "daily_usage": [{"day": k, "tokens": v} for k, v in sorted(daily_usage.items())]
    }

@app.get("/", response_class=HTMLResponse)
def dashboard_index():
    """Serve the standalone modular Dashboard HTML interface."""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()
