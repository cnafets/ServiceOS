from fastapi import FastAPI

from app.api.routes import appointments, health, shopware
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import create_db_and_tables


def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.app_name, version="0.1.0")

    @app.on_event("startup")
    def on_startup() -> None:
        create_db_and_tables()

    app.include_router(health.router)
    app.include_router(appointments.router, prefix="/api/v1")
    app.include_router(shopware.router, prefix="/api/v1")
    return app


app = create_app()
