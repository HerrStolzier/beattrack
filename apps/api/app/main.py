import asyncio
import atexit
import logging
import os
import shutil
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.limiter import limiter
from app.routes import songs, similar, feedback, analyze, identify

logger = logging.getLogger(__name__)

_default_origins = ["https://beattrack.app", "http://localhost:3000"]
_origins = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else _default_origins


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


async def _periodic_cleanup(temp_dir: str, max_age_minutes: int = 15, interval_minutes: int = 15):
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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage startup/shutdown lifecycle."""
    from app.routes.analyze import TEMP_DIR

    cleanup_task = asyncio.create_task(_periodic_cleanup(TEMP_DIR))
    yield
    cleanup_task.cancel()
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


app = FastAPI(
    title="Beattrack API",
    description="Find sonically similar songs through audio analysis",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Ensure allow_credentials is not combined with wildcard origins
_use_credentials = "*" not in _origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_use_credentials,
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


# atexit als Fallback bei hartem Prozess-Kill
def _atexit_cleanup():
    from app.routes.analyze import TEMP_DIR
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


atexit.register(_atexit_cleanup)
