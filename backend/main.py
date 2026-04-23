import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine, Base, AsyncSessionLocal
from routers import farms, mpesa_webhooks, trigger_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="CropSure AI",
    description=(
        "Parametric crop micro-insurance for Kenyan smallholder farmers. "
        "Automatically pays via M-Pesa when satellite data detects crop stress."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all in development; tighten origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(farms.router, prefix="/farms", tags=["farms"])
app.include_router(mpesa_webhooks.router, prefix="/mpesa", tags=["mpesa"])
app.include_router(trigger_routes.router, prefix="/trigger", tags=["trigger"])


@app.get("/", tags=["info"])
async def root():
    return {
        "service": "CropSure AI Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "enroll": "POST /farms/enroll",
            "farm_detail": "GET /farms/{farm_id}",
            "farm_list": "GET /farms",
            "run_monitoring": "POST /trigger/run",
            "simulate_drought": "POST /trigger/simulate-drought/{farm_id}",
            "stk_callback": "POST /mpesa/stk-callback",
            "b2c_callback": "POST /mpesa/b2c-callback",
        },
    }


@app.get("/health", tags=["info"])
async def health():
    db_status = "disconnected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        pass
    return {"status": "ok", "database": db_status}
