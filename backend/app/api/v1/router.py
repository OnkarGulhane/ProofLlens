"""Aggregated API v1 router."""

from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.documents import router as documents_router
from app.api.v1.retrievals import router as retrievals_router
from app.api.v1.queries import router as queries_router
from app.api.v1.comparisons import router as comparisons_router

api_v1_router = APIRouter()

# Register endpoint routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(workspaces_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(retrievals_router)
api_v1_router.include_router(queries_router)
api_v1_router.include_router(comparisons_router)
