from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gestion_boutiques.api.audit import router as audit_router
from gestion_boutiques.api.auth import router as auth_router
from gestion_boutiques.api.catalog import router as catalog_router
from gestion_boutiques.api.inventory import router as inventory_router
from gestion_boutiques.api.owners import router as owners_router
from gestion_boutiques.api.ownerships import router as ownerships_router
from gestion_boutiques.api.sales import router as sales_router
from gestion_boutiques.api.stores import router as stores_router
from gestion_boutiques.config import get_settings
from gestion_boutiques.db.session import get_db_session


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(audit_router, prefix=settings.api_v1_prefix)
    application.include_router(auth_router, prefix=settings.api_v1_prefix)
    application.include_router(catalog_router, prefix=settings.api_v1_prefix)
    application.include_router(inventory_router, prefix=settings.api_v1_prefix)
    application.include_router(owners_router, prefix=settings.api_v1_prefix)
    application.include_router(ownerships_router, prefix=settings.api_v1_prefix)
    application.include_router(sales_router, prefix=settings.api_v1_prefix)
    application.include_router(stores_router, prefix=settings.api_v1_prefix)

    @application.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @application.get("/health/ready", tags=["system"])
    async def readiness_check(
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> dict[str, str]:
        await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "available"}

    return application


app = create_app()