import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import songs, similar, feedback

_default_origins = ["https://beattrack.vercel.app", "http://localhost:3000"]
_origins = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else _default_origins

app = FastAPI(
    title="Beattrack API",
    description="Find sonically similar songs through audio analysis",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(songs.router)
app.include_router(similar.router)
app.include_router(feedback.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
