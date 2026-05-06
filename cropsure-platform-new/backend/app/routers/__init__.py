"""API routers.

Exports a single `api_router` that composes all feature routers.
"""

from fastapi import APIRouter

from .farms import router as farms_router
from .mpesa_webhooks import router as mpesa_router
from .trigger_routes import router as trigger_router

api_router = APIRouter()
api_router.include_router(farms_router)
api_router.include_router(mpesa_router)
api_router.include_router(trigger_router)

__all__ = [
	"api_router",
	"farms_router",
	"mpesa_router",
	"trigger_router",
]

