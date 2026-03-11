from fastapi import FastAPI

app = FastAPI(
    title="Beattrack API",
    description="Find sonically similar songs through audio analysis",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
