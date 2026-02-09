"""
System management routes.
Provides health checks, restart capabilities, and system status.
"""

import os
import signal
import logging
import asyncio
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Track startup time
STARTUP_TIME = datetime.utcnow()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    uptime_seconds: float
    pid: int


class RestartResponse(BaseModel):
    """Restart response."""
    success: bool
    message: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns server status and uptime.
    """
    uptime = (datetime.utcnow() - STARTUP_TIME).total_seconds()
    return HealthResponse(
        status="healthy",
        uptime_seconds=uptime,
        pid=os.getpid()
    )


async def delayed_restart():
    """Trigger a restart after a short delay to allow the response to be sent."""
    await asyncio.sleep(1)
    logger.info("🔄 Initiating backend restart...")
    
    # If running with --reload, touching a watched file triggers automatic restart
    main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "main.py")
    if os.path.exists(main_py):
        os.utime(main_py)  # Touch the file → uvicorn --reload detects change
        logger.info(f"✅ Touched {main_py} to trigger uvicorn reload")
    else:
        # Fallback: SIGTERM (run_all.sh monitor loop will restart)
        logger.warning("⚠️ main.py not found, falling back to SIGTERM")
        os.kill(os.getpid(), signal.SIGTERM)


@router.post("/restart", response_model=RestartResponse)
async def restart_backend(background_tasks: BackgroundTasks):
    """
    Restart the backend server.
    
    Triggers uvicorn's --reload watcher by touching main.py.
    Falls back to SIGTERM if --reload is not active (run_all.sh will restart).
    
    ⚠️ Use with caution - any in-progress operations will be interrupted.
    """
    logger.warning("⚠️ Backend restart requested via API")
    
    # Schedule restart in background so we can return a response first
    background_tasks.add_task(delayed_restart)
    
    return RestartResponse(
        success=True,
        message="Backend is restarting. Please wait a few seconds."
    )


@router.get("/status")
async def system_status():
    """
    Get comprehensive system status.
    """
    uptime = (datetime.utcnow() - STARTUP_TIME).total_seconds()
    
    return {
        "status": "running",
        "pid": os.getpid(),
        "uptime_seconds": uptime,
        "uptime_formatted": format_uptime(uptime),
        "started_at": STARTUP_TIME.isoformat(),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
    }


def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
