from datetime import datetime, timedelta
import os
from typing import Dict, List, Literal, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from agent_atm.types import TokenEvent
from agent_atm.data_managers.sqlalchemy import SQLAlchemyManager
from agent_atm.rules.engine import RuleEngine
from agent_atm.rules.exceptions import DBRuleTokenAllowanceExceeded, CustomServerPyRuleViolation

app = FastAPI(
    title="Agent Token Manager Dashboard",
    description="Real-time token metrics, quota limit observances, and LLM telemetry.",
)

# Mount static assets directory for CSS, Javascript, and HTML resources if present
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Resolve database path from environment or default
DB_PATH = os.environ.get("ATM_DB_PATH", "agent_atm.db")
db_manager = SQLAlchemyManager(db_url=DB_PATH)

# Load Rule Engine and dynamic server-side rules
rule_engine = RuleEngine()
# DEPRECATED in v1.0: Dynamic server-side rules.py auto-import has been disabled.
# Rationale: Magic auto-imports violate explicit design principles and introduce security risks.
# Developers should explicitly register server rules via rule_engine.add_server_rule().
# server_rules_path = os.path.join(os.getcwd(), "rules.py")
# if os.path.exists(server_rules_path):
#     try:
#         import importlib.util
#         spec = importlib.util.spec_from_file_location("server_rules", server_rules_path)
#         if spec and spec.loader:
#             module = importlib.util.module_from_spec(spec)
#             spec.loader.exec_module(module)
#             if hasattr(module, "validate_request"):
#                 rule_engine.add_server_rule(getattr(module, "validate_request"))
#     except Exception as e:
#         print(f"[agent-atm-server] Warning: Failed to dynamically load server rules.py: {e}")



class EventPostSchema(BaseModel):
    event_type: Literal["request", "response"] = Field(
        ..., description="Event type: must be 'request' or 'response'"
    )
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


@app.post("/api/validate", status_code=200)
def validate_event(payload: EventPostSchema):
    """Endpoint to validate token usage limits against server rules and DB quotas."""
    event = TokenEvent(
        timestamp=datetime.now(),
        event_type=payload.event_type,
        token_count=payload.token_count,
        model_id=payload.model_id,
        username=payload.username,
        session_id=payload.session_id,
        app_id=payload.app_id,
        _additional_metadata_tags=payload.tags or [],
        _additional_metadata_config=payload.config or {},
    )

    # Evaluate server dynamic validation rules and DB validation rules
    try:
        rule_engine.validate_server_rules(event)
        rule_engine.validate_db_rules(event, db_manager)
    except CustomServerPyRuleViolation as e:
        raise HTTPException(status_code=400, detail=f"CUSTOM-SERVER-PY-RULE: {str(e)}")
    except DBRuleTokenAllowanceExceeded as e:
        raise HTTPException(status_code=402, detail=f"DB-RULE-TOKEN-ALLOWANCE: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "allowed",
        "message": "Validation checks passed successfully."
    }



@app.post("/api/events", status_code=201)
def create_event(payload: EventPostSchema):
    """Endpoint for Enterprise customers to post token telemetry events from distributed backend nodes."""
    if payload.event_type not in ("request", "response"):
        raise HTTPException(
            status_code=400, detail="event_type must be either 'request' or 'response'"
        )

    event = TokenEvent(
        timestamp=datetime.now(),
        event_type=payload.event_type,
        token_count=payload.token_count,
        model_id=payload.model_id,
        username=payload.username,
        session_id=payload.session_id,
        app_id=payload.app_id,
        _additional_metadata_tags=payload.tags or [],
        _additional_metadata_config=payload.config or {},
    )
    db_manager.save(event)
    return {
        "status": "success",
        "message": "Event successfully logged to backend telemetry store.",
    }


@app.get("/api/events")
def get_events(
    limit: int = Query(100, description="Maximum number of events to return"),
):
    events = db_manager.get_all_events()
    # Return raw records in a serializable form
    serialized = []
    for ev in events[:limit]:
        serialized.append(
            {
                "timestamp": ev.timestamp.isoformat(),
                "event_type": ev.event_type,
                "token_count": ev.token_count,
                "model_id": ev.model_id,
                "username": ev.username or "Anonymous",
                "session_id": ev.session_id or "N/A",
                "app_id": ev.app_id or "N/A",
                "hostname": ev.hostname or "Unknown",
                "tags": ev._additional_metadata_tags,
                "config": ev._additional_metadata_config,
            }
        )

    return serialized


@app.get("/api/metrics")
def get_metrics(
    window: str = Query("7d", description="Time window for metrics dashboard"),
):
    now = datetime.now()

    window_map = {
        "1m": timedelta(days=30),
        "7d": timedelta(days=7),
        "3d": timedelta(days=3),
        "1d": timedelta(days=1),
        "12h": timedelta(hours=12),
        "6h": timedelta(hours=6),
        "4h": timedelta(hours=4),
        "2h": timedelta(hours=2),
        "1h": timedelta(hours=1),
        "30m": timedelta(minutes=30),
        "15m": timedelta(minutes=15),
        "5m": timedelta(minutes=5),
    }

    delta = window_map.get(window, timedelta(days=7))
    cutoff = now - delta

    all_events = db_manager.get_all_events()
    events = [e for e in all_events if e.timestamp >= cutoff]

    total_requests = sum(1 for e in events if e.event_type == "request")
    total_responses = sum(1 for e in events if e.event_type == "response")
    total_tokens = sum(e.token_count for e in events)

    total_request_tokens = sum(
        e.token_count for e in events if e.event_type == "request"
    )
    total_response_tokens = sum(
        e.token_count for e in events if e.event_type == "response"
    )

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

    # Dynamic chart aggregation: Divide the window into 12 intervals
    num_intervals = 12
    interval_duration = delta / num_intervals

    def format_label(dt: datetime, w_delta: timedelta) -> str:
        if w_delta > timedelta(days=2):
            return dt.strftime("%b %d")
        elif w_delta > timedelta(hours=2):
            return dt.strftime("%H:%M")
        else:
            return dt.strftime("%H:%M:%S")

    intervals = []
    for i in range(num_intervals):
        start_time = cutoff + (i * interval_duration)
        end_time = start_time + interval_duration
        intervals.append(
            {
                "start": start_time,
                "end": end_time,
                "label": format_label(start_time, delta),
                "request_tokens": 0,
                "response_tokens": 0,
                "total_tokens": 0,
            }
        )

    for e in events:
        for interval in intervals:
            if interval["start"] <= e.timestamp < interval["end"]:
                interval["total_tokens"] += e.token_count
                if e.event_type == "request":
                    interval["request_tokens"] += e.token_count
                elif e.event_type == "response":
                    interval["response_tokens"] += e.token_count
                break

    return {
        "stats": {
            "total_events": len(events),
            "total_requests": total_requests,
            "total_responses": total_responses,
            "total_tokens": total_tokens,
            "total_request_tokens": total_request_tokens,
            "total_response_tokens": total_response_tokens,
        },
        "by_model": model_counts,
        "by_app": app_counts,
        "by_user": user_counts,
        "chart_data": [
            {
                "label": item["label"],
                "request_tokens": item["request_tokens"],
                "response_tokens": item["response_tokens"],
                "total_tokens": item["total_tokens"],
            }
            for item in intervals
        ],
    }


@app.get("/", response_class=HTMLResponse)
def dashboard_index():
    """Serve the standalone modular Dashboard HTML interface."""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if not os.path.exists(index_path):
        return HTMLResponse(
            content="<h1>Dashboard UI Assets Missing</h1><p>Please ensure the package was installed correctly with static assets, or run within a fully developed repository source tree.</p>",
            status_code=404,
        )
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()


def run_dashboard():
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Launch the Agent Token Manager analytics dashboard.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to (default: 8000)")
    parser.add_argument("--db-path", default="agent_atm.db", help="Path to the SQLite telemetry database (default: agent_atm.db)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development mode)")
    args = parser.parse_args()

    os.environ["ATM_DB_PATH"] = args.db_path

    print(f"--> Starting Agent Token Manager dashboard on http://{args.host}:{args.port}")
    print(f"--> Telemetry Database: {args.db_path}")
    uvicorn.run("agent_atm.dashboard.server:app", host=args.host, port=args.port, reload=args.reload)


