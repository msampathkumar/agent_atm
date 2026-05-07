from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from agent_atm.types import TokenEvent
from agent_atm.data_managers.sqlite import SqliteManager


app = FastAPI(
    title="Agent Token Manager Dashboard",
    description="Real-time token metrics, quota limit observances, and LLM telemetry."
)

# Resolve database path from environment or default
DB_PATH = os.environ.get("ATM_DB_PATH", "agent_atm.db")
db_manager = SqliteManager(db_path=DB_PATH)

class EventPostSchema(BaseModel):
    event_type: str = Field(..., description="Event type: must be 'request' or 'response'")
    token_count: int = Field(..., ge=0, description="Calculated token count")
    model_id: str = Field(..., description="ID of the LLM model used")
    username: Optional[str] = None
    session_id: Optional[str] = None
    app_id: Optional[str] = None
    tags: Optional[List[str]] = None
    config: Optional[Dict[str, str]] = None

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
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>agent-atm | Token Manager Dashboard</title>
        <!-- Premium Google Font -->
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
        <!-- Chart.js from CDN -->
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <!-- Premium Glassmorphism Styles -->
        <style>
            :root {
                --bg-color: #0a0b0d;
                --card-bg: rgba(20, 22, 28, 0.7);
                --border-color: rgba(255, 255, 255, 0.08);
                --text-primary: #f3f4f6;
                --text-secondary: #9ca3af;
                --accent-primary: #6366f1; /* Violet */
                --accent-secondary: #10b981; /* Emerald */
                --accent-warning: #f59e0b; /* Amber */
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Outfit', sans-serif;
            }

            body {
                background-color: var(--bg-color);
                color: var(--text-primary);
                min-height: 100vh;
                padding: 2rem;
                overflow-x: hidden;
                background-image: 
                    radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                    radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.1) 0%, transparent 40%);
            }

            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2.5rem;
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 1.5rem;
            }

            .logo-area h1 {
                font-size: 2.2rem;
                font-weight: 800;
                letter-spacing: -1px;
                background: linear-gradient(135deg, #818cf8 0%, #34d399 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .logo-area p {
                color: var(--text-secondary);
                font-size: 0.95rem;
                margin-top: 4px;
            }

            .btn {
                background: var(--accent-primary);
                border: none;
                color: #fff;
                padding: 0.6rem 1.2rem;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.2s ease;
                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
            }

            .btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
            }

            /* Stats Grid */
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2.5rem;
            }

            .stat-card {
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 16px;
                padding: 1.5rem;
                backdrop-filter: blur(12px);
                position: relative;
                overflow: hidden;
                transition: transform 0.3s ease, border-color 0.3s ease;
            }

            .stat-card:hover {
                transform: translateY(-2px);
                border-color: rgba(99, 102, 241, 0.3);
            }

            .stat-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
                height: 100%;
                background: var(--accent-primary);
            }

            .stat-card.responses::before { background: var(--accent-secondary); }
            .stat-card.tokens::before { background: var(--accent-warning); }

            .stat-label {
                font-size: 0.9rem;
                color: var(--text-secondary);
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 0.5rem;
            }

            .stat-value {
                font-size: 2rem;
                font-weight: 800;
            }

            /* Charts Area */
            .charts-grid {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 1.5rem;
                margin-bottom: 2.5rem;
            }

            @media (max-width: 968px) {
                .charts-grid {
                    grid-template-columns: 1fr;
                }
            }

            .chart-card {
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 20px;
                padding: 1.5rem;
                backdrop-filter: blur(12px);
            }

            .chart-title {
                font-size: 1.1rem;
                font-weight: 600;
                margin-bottom: 1rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            /* Table Card */
            .table-card {
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 20px;
                padding: 1.5rem;
                backdrop-filter: blur(12px);
                overflow-x: auto;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                text-align: left;
                margin-top: 1rem;
            }

            th, td {
                padding: 0.9rem 1.2rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }

            th {
                color: var(--text-secondary);
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-weight: 600;
            }

            td {
                font-size: 0.95rem;
            }

            tr:hover td {
                background: rgba(255, 255, 255, 0.02);
            }

            .badge {
                padding: 0.25rem 0.6rem;
                border-radius: 6px;
                font-size: 0.8rem;
                font-weight: 600;
                display: inline-block;
            }

            .badge.request {
                background: rgba(99, 102, 241, 0.15);
                color: #818cf8;
            }

            .badge.response {
                background: rgba(16, 185, 129, 0.15);
                color: #34d399;
            }

            .tag-badge {
                background: rgba(255, 255, 255, 0.05);
                color: var(--text-secondary);
                border: 1px solid var(--border-color);
                padding: 0.15rem 0.4rem;
                border-radius: 4px;
                font-size: 0.75rem;
                margin-right: 4px;
                display: inline-block;
            }

            .config-badge {
                background: rgba(99, 102, 241, 0.08);
                color: #818cf8;
                border: 1px solid rgba(99, 102, 241, 0.2);
                padding: 0.15rem 0.4rem;
                border-radius: 4px;
                font-size: 0.75rem;
                margin-right: 4px;
                display: inline-block;
            }
        </style>

    </head>
    <body>
        <header>
            <div class="logo-area">
                <h1>agent-atm</h1>
                <p>Real-time LLM Token usage metering & quota observability</p>
            </div>
            <button class="btn" onclick="loadData()">Refresh Telemetry</button>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Events</div>
                <div class="stat-value" id="stat-total-events">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Requests</div>
                <div class="stat-value" id="stat-total-requests">-</div>
            </div>
            <div class="stat-card responses">
                <div class="stat-label">Total Responses</div>
                <div class="stat-value" id="stat-total-responses">-</div>
            </div>
            <div class="stat-card tokens">
                <div class="stat-label">Total Tokens Used</div>
                <div class="stat-value" id="stat-total-tokens">-</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">Token Consumption Trend (Last 7 Days)</div>
                <div style="height: 280px; position: relative;">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <div class="chart-title">Usage By Application</div>
                <div style="height: 280px; position: relative; display: flex; justify-content: center;">
                    <canvas id="appChart"></canvas>
                </div>
            </div>
        </div>

        <div class="table-card">
            <div class="chart-title">Live Telemetry Logs (Last 100 Events)</div>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Type</th>
                        <th>Tokens</th>
                        <th>Model ID</th>
                        <th>App ID</th>
                        <th>Username</th>
                        <th>Session ID</th>
                        <th>Metadata</th>
                    </tr>
                </thead>

                <tbody id="events-tbody">
                    <tr>
                        <td colspan="8" style="text-align: center; color: var(--text-secondary);">Loading events...</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <script>
            let trendChartInstance = null;
            let appChartInstance = null;

            async function loadData() {
                try {
                    // 1. Fetch stats & charts data
                    const metricsRes = await fetch('/api/metrics');
                    const metrics = await metricsRes.json();

                    document.getElementById('stat-total-events').innerText = metrics.stats.total_events.toLocaleString();
                    document.getElementById('stat-total-requests').innerText = metrics.stats.total_requests.toLocaleString();
                    document.getElementById('stat-total-responses').innerText = metrics.stats.total_responses.toLocaleString();
                    document.getElementById('stat-total-tokens').innerText = metrics.stats.total_tokens.toLocaleString();

                    // Render Trend Chart
                    const trendCtx = document.getElementById('trendChart').getContext('2d');
                    if (trendChartInstance) trendChartInstance.destroy();
                    
                    trendChartInstance = new Chart(trendCtx, {
                        type: 'line',
                        data: {
                            labels: metrics.daily_usage.map(d => d.day),
                            datasets: [{
                                label: 'Tokens Consumed',
                                data: metrics.daily_usage.map(d => d.tokens),
                                borderColor: '#6366f1',
                                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                fill: true,
                                tension: 0.3,
                                borderWidth: 3
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: false } },
                            scales: {
                                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9ca3af' } },
                                x: { grid: { display: false }, ticks: { color: '#9ca3af' } }
                            }
                        }
                    });

                    // Render App Distribution Pie Chart
                    const appCtx = document.getElementById('appChart').getContext('2d');
                    if (appChartInstance) appChartInstance.destroy();
                    
                    const appLabels = Object.keys(metrics.by_app);
                    const appData = Object.values(metrics.by_app);

                    appChartInstance = new Chart(appCtx, {
                        type: 'doughnut',
                        data: {
                            labels: appLabels,
                            datasets: [{
                                data: appData,
                                backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'],
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { position: 'bottom', labels: { color: '#f3f4f6', boxWidth: 12 } }
                            }
                        }
                    });

                    // 2. Fetch live events
                    const eventsRes = await fetch('/api/events');
                    const events = await eventsRes.json();

                    const tbody = document.getElementById('events-tbody');
                    tbody.innerHTML = '';
                    
                    if (events.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">No events recorded yet.</td></tr>';
                        return;
                    }

                    events.forEach(ev => {
                        const tr = document.createElement('tr');
                        const timeStr = new Date(ev.timestamp).toLocaleTimeString();
                        const typeBadge = `<span class="badge ${ev.event_type}">${ev.event_type}</span>`;
                        
                        // Build inline metadata badges
                        let metaHtml = '';
                        if (ev.tags && ev.tags.length > 0) {
                            ev.tags.forEach(tag => {
                                metaHtml += `<span class="tag-badge">${tag}</span>`;
                            });
                        }
                        if (ev.config) {
                            Object.entries(ev.config).forEach(([k, v]) => {
                                metaHtml += `<span class="config-badge">${k}=${v}</span>`;
                            });
                        }
                        if (!metaHtml) {
                            metaHtml = '<span style="color: var(--text-secondary); font-size: 0.8rem;">None</span>';
                        }
                        
                        tr.innerHTML = `
                            <td>${timeStr}</td>
                            <td>${typeBadge}</td>
                            <td style="font-weight: 600;">${ev.token_count.toLocaleString()}</td>
                            <td>${ev.model_id}</td>
                            <td>${ev.app_id}</td>
                            <td>${ev.username}</td>
                            <td><code>${ev.session_id}</code></td>
                            <td>${metaHtml}</td>
                        `;
                        tbody.appendChild(tr);
                    });


                } catch (err) {
                    console.error("Error loading telemetry data:", err);
                }
            }

            // Initial load
            loadData();
            // Poll every 10 seconds for real-time update feel
            setInterval(loadData, 10000);
        </script>
    </body>
    </html>
    """
    return html_content
