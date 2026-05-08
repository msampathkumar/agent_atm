import os
import uvicorn


def run(
    host: str = "127.0.0.1",
    port: int = 8000,
    db_path: str = "agent_atm.db",
    reload: bool = False,
):
    """Start the FastAPI telemetry server and dashboard programmatically.

    Example:
        from agent_atm import server
        server.run(port=8080, db_path="usage.db")
    """
    os.environ["ATM_DB_PATH"] = db_path
    uvicorn.run("agent_atm.dashboard.server:app", host=host, port=port, reload=reload)
