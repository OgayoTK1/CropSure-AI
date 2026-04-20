from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import engine, Base
from routers import farms, mpesa_webhooks, trigger_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="CropSure AI",
    description="Index-based crop insurance platform — farm enrollment, M-Pesa payments, drought monitoring.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(farms.router, prefix="/farms", tags=["farms"])
app.include_router(mpesa_webhooks.router, prefix="/webhooks", tags=["mpesa"])
app.include_router(trigger_routes.router, prefix="/trigger", tags=["trigger"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
