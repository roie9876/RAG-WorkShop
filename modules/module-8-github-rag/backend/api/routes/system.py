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
    status: str
    uptime_seconds: float
    pid: int


class RestartResponse(BaseModel):
    success: bool
    message: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    uptime = (datetime.utcnow() - STARTUP_TIME).total_seconds()
    return HealthResponse(
        status="healthy",
        uptime_seconds=uptime,
        pid=os.getpid(),
    )


async def _delayed_shutdown():
    """Shutdown after a short delay so the HTTP response can be sent."""
    await asyncio.sleep(1)
    logger.info("🔄 Initiating backend restart...")
    os.kill(os.getpid(), signal.SIGTERM)


@router.post("/restart", response_model=RestartResponse)
async def restart_backend(background_tasks: BackgroundTasks):
    """
    Restart the backend server.
    The process manager (run_all.sh) should restart it automatically.
    """
    logger.warning("⚠️ Backend restart requested via API")
    background_tasks.add_task(_delayed_shutdown)
    return RestartResponse(
        success=True,
        message="Backend is restarting. Please wait a few seconds.",
    )


@router.get("/status")
async def system_status():
    """Comprehensive system status."""
    uptime = (datetime.utcnow() - STARTUP_TIME).total_seconds()
    return {
        "status": "running",
        "pid": os.getpid(),
        "uptime_seconds": uptime,
        "uptime_formatted": _format_uptime(uptime),
        "started_at": STARTUP_TIME.isoformat(),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
    }


def _format_uptime(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
