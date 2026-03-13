"""Audio analysis endpoints — upload, SSE streaming, results polling."""
import asyncio
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.limiter import limiter
from app.services.validation import validate_upload, validate_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["analyze"])

# Concurrency controls
UPLOAD_SEMAPHORE = asyncio.Semaphore(3)  # Max 3 concurrent uploads
SSE_LIMITER = asyncio.Semaphore(50)  # Max 50 SSE connections

# Temp directory for uploads
TEMP_DIR = os.environ.get("BEATTRACK_TEMP_DIR", tempfile.mkdtemp(prefix="beattrack_"))
Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)

# In-memory job status tracking (simple dict, sufficient for single-worker)
# In production, this would be read from procrastinate_jobs table
_job_status: dict[str, dict] = {}


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str


@router.post("", response_model=AnalyzeResponse)
@limiter.limit("10/minute")
async def upload_and_analyze(request: Request, file: UploadFile):
    """Upload audio file for analysis.

    Validates the file, saves to temp, enqueues analysis job.
    Returns job_id for tracking via SSE or polling.
    """
    # Check capacity
    if UPLOAD_SEMAPHORE._value == 0:
        raise HTTPException(status_code=503, detail="Server at capacity. Please retry shortly.")

    async with UPLOAD_SEMAPHORE:
        # 1. Validate upload (MIME + size)
        await validate_upload(file)

        # 2. Save to temp file
        job_id = str(uuid.uuid4())
        ext = Path(file.filename or "audio.mp3").suffix or ".mp3"
        temp_path = os.path.join(TEMP_DIR, f"{job_id}{ext}")

        try:
            content = await file.read()
            with open(temp_path, "wb") as f:
                f.write(content)
        except Exception as exc:
            logger.error("Failed to save upload: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

        # 3. Validate audio (ffprobe: format, duration) — sync call, run in executor
        loop = asyncio.get_event_loop()
        audio_info = await loop.run_in_executor(None, validate_audio, temp_path)

        # 4. Track job status
        _job_status[job_id] = {
            "status": "queued",
            "progress": 0.0,
            "audio_path": temp_path,
            "duration_sec": audio_info.get("duration_sec"),
        }

        # 5. Enqueue analysis job
        try:
            from app.workers import app as procrastinate_app, analyze_audio
            analyze_audio.defer(audio_path=temp_path, job_id=job_id)
        except Exception as exc:
            logger.error("Failed to enqueue job %s: %s", job_id, exc)
            _job_status[job_id]["status"] = "failed"
            raise HTTPException(status_code=502, detail="Failed to start analysis.")

        return AnalyzeResponse(job_id=job_id, status="queued")


@router.get("/{job_id}/stream")
async def stream_progress(job_id: str):
    """SSE endpoint for real-time analysis progress.

    Events:
    - status: queued | processing | completed | failed
    - progress: 0.0 - 1.0 (during processing)
    - result: full analysis result (on completed)
    - heartbeat: keepalive every 15s
    """
    if job_id not in _job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    if SSE_LIMITER._value == 0:
        raise HTTPException(status_code=503, detail="Too many active connections.")

    async def event_generator():
        async with SSE_LIMITER:
            heartbeat_interval = 15
            stale_timeout = 300
            elapsed = 0.0

            while elapsed < stale_timeout:
                job = _job_status.get(job_id)
                if not job:
                    yield {"event": "error", "data": json.dumps({"detail": "Job not found"})}
                    return

                status = job["status"]

                if status == "completed":
                    yield {
                        "event": "status",
                        "data": json.dumps({
                            "status": "completed",
                            "progress": 1.0,
                            "result": job.get("result"),
                        }),
                    }
                    return

                if status == "failed":
                    yield {
                        "event": "status",
                        "data": json.dumps({
                            "status": "failed",
                            "error": job.get("error", "Analysis failed"),
                        }),
                    }
                    return

                # Send current status
                yield {
                    "event": "status",
                    "data": json.dumps({
                        "status": status,
                        "progress": job.get("progress", 0.0),
                    }),
                }

                # Wait before next update
                await asyncio.sleep(heartbeat_interval)
                elapsed += heartbeat_interval

                # Send heartbeat
                yield {"event": "heartbeat", "data": ""}

            # Stale timeout reached
            yield {"event": "error", "data": json.dumps({"detail": "Connection timed out"})}

    return EventSourceResponse(event_generator())


@router.get("/{job_id}/results")
async def get_results(job_id: str):
    """Polling fallback for analysis results.

    Returns current job status. If completed, includes full results.
    """
    job = _job_status.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JSONResponse(content={
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress", 0.0),
        "result": job.get("result") if job["status"] == "completed" else None,
        "error": job.get("error") if job["status"] == "failed" else None,
    })


def update_job_status(job_id: str, status: str, **kwargs):
    """Update job status from worker. Called by the analyze task."""
    if job_id in _job_status:
        _job_status[job_id]["status"] = status
        _job_status[job_id].update(kwargs)
