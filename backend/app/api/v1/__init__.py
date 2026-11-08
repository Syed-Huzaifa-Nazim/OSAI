"""API v1 router aggregation.

FEATURE INTEGRATION POINT
=========================
A teammate's feature backend is mounted by adding one line to ``include_router``
below. Nothing else in the codebase needs to change. No edits to main.py, no
edits to existing routers. The matching frontend side is
``frontend/src/features/registry.ts``. See docs/architecture.md.
"""

from fastapi import APIRouter

from app.api.v1.auth.routes import router as auth_router
from app.api.v1.documents.routes import router as documents_router
from app.api.v1.pipeline.routes import router as pipeline_router
from app.api.v1.projects.routes import router as projects_router
from app.api.v1.scrapers.routes import router as scrapers_router
from app.api.v1.users.routes import router as users_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(projects_router)
api_router.include_router(pipeline_router)
api_router.include_router(documents_router)
api_router.include_router(scrapers_router)

# --- feature modules ---------------------------------------------------------
# Add a teammate's router here, one line each. Example:
#   from app.features.seo_audit.routes import router as seo_audit_router
#   api_router.include_router(seo_audit_router)
