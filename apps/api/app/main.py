import asyncio
import atexit
import logging
import os
import shutil
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter
from app.routes import songs, similar, feedback, analyze, identify

logger = logging.getLogger(__name__)

_default_origins = ["https://beattrack.vercel.app", "http://localhost:3000"]
_origins = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else _default_origins

app = FastAPI(
    title="Beattrack API",
    description="Find sonically similar songs through audio analysis",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

app.include_router(songs.router)
app.include_router(similar.router)
app.include_router(feedback.router)
app.include_router(analyze.router)
app.include_router(identify.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# === Temp-Cleanup ===
async def periodic_cleanup(temp_dir: str, max_age_minutes: int = 15, interval_minutes: int = 15):
    """Periodically remove old temp files."""
    while True:
        await asyncio.sleep(interval_minutes * 60)
        try:
            cutoff = time.time() - (max_age_minutes * 60)
            temp_path = Path(temp_dir)
            if not temp_path.exists():
                continue
            for f in temp_path.iterdir():
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
                    logger.debug("Cleaned up temp file: %s", f.name)
        except Exception as exc:
            logger.warning("Temp cleanup error: %s", exc)


@app.on_event("startup")
async def startup():
    from app.routes.analyze import TEMP_DIR
    asyncio.create_task(periodic_cleanup(TEMP_DIR))


@app.on_event("shutdown")
async def shutdown():
    from app.routes.analyze import TEMP_DIR
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


# atexit als Fallback
def _atexit_cleanup():
    from app.routes.analyze import TEMP_DIR
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


atexit.register(_atexit_cleanup)
