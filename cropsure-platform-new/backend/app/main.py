"""CropSure Backend — FastAPI app on port 8000."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_tables
from .config import get_settings
from .routers import farms, mpesa_webhooks, trigger_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    logger.info("CropSure backend ready — DB tables ensured")
    yield


app = FastAPI(
    title="CropSure AI Backend",
    version="1.0.0",
    description="Parametric crop insurance backend for African smallholder farmers",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(farms.router)
app.include_router(mpesa_webhooks.router)
app.include_router(trigger_routes.router)


@app.get("/")
def root():
    return {
        "service": "CropSure AI Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    from .database import engine
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"
    return {"status": "ok", "database": db_status}
