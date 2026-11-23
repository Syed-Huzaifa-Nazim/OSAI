"""OptiStratixAI API.

Run locally:
    cd backend
    uvicorn app.main:app --reload

With no configuration at all the service starts in demo mode and serves the
seeded sample project, so the frontend is fully walkable before Supabase or an
LLM key exists.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core import model_check
from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, register_middleware
from app.models.misc import HealthResponse
from app.vectorstore import chroma

configure_logging()
logger = logging.getLogger("optistratix")

app = FastAPI(
    title="OptiStratixAI API",
    version=__version__,
    description=(
        "Human-in-the-Loop Multi-Agentic RAG for Smarter Digital Marketing.\n\n"
        "Routes map 1:1 onto the nine pipeline stages. Two of those stages, 5 and 7, "
        "cannot be advanced by any agent; they require a human decision."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

register_middleware(app)
register_exception_handlers(app)
app.include_router(api_router)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    """What is actually wired up. Useful when a demo behaves unexpectedly."""
    models = model_check.report()
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.environment,
        demo_mode=settings.is_demo,
        supabase_configured=settings.has_supabase,
        openai_configured=settings.has_openai,
        vectorstore_available=chroma.get_client() is not None,
        models_ready=models["ready"],
        models_missing=model_check.summary_lines(models),
    )


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "OptiStratixAI API %s starting (env=%s demo=%s supabase=%s openai=%s)",
        __version__,
        settings.environment,
        settings.is_demo,
        settings.has_supabase,
        settings.has_openai,
    )
    models = model_check.report()
    if models["ready"]:
        logger.info("All trained models are ready (Instagram and Daraz).")
    else:
        for line in model_check.summary_lines(models):
            logger.warning("MODEL %s", line)
        if settings.require_models:
            raise RuntimeError("REQUIRE_MODELS is on and some trained models cannot run: "
                               + " | ".join(model_check.summary_lines(models)))
    if settings.is_demo:
        logger.warning(
            "Running in DEMO MODE: the seeded sample project is served and no database is "
            "written. Set DEMO_MODE=false with Supabase configured for real data."
        )
