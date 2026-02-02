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


async def delayed_shutdown():
    """Shutdown the server after a short delay to allow response to be sent."""
    await asyncio.sleep(1)
    logger.info("🔄 Initiating backend restart...")
    os.kill(os.getpid(), signal.SIGTERM)


@router.post("/restart", response_model=RestartResponse)
async def restart_backend(background_tasks: BackgroundTasks):
    """
    Restart the backend server.
    
    This will gracefully shutdown the current process.
    The process manager (run_all.sh) should restart it automatically.
    
    ⚠️ Use with caution - any in-progress operations will be interrupted.
    """
    logger.warning("⚠️ Backend restart requested via API")
    
    # Schedule shutdown in background so we can return a response first
    background_tasks.add_task(delayed_shutdown)
    
    return RestartResponse(
        success=True,
        message="Backend is restarting. Please wait a few seconds and refresh the page."
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
