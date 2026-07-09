from fastapi import FastAPI

from fastapi.staticfiles import StaticFiles
from app.api.routes import appointments, health, intake, shopware
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import request_observability_middleware
from app.core.startup import validate_shopware_startup
from app.db.session import create_db_and_tables


def create_app() -> FastAPI:
    configure_logging(settings.log_level, settings.log_format)
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.middleware("http")(request_observability_middleware)

    @app.on_event("startup")
    def on_startup() -> None:
        validate_shopware_startup(settings)
        create_db_and_tables()

    app.include_router(health.router)
    app.include_router(appointments.router, prefix="/api/v1")
    app.include_router(shopware.router, prefix="/api/v1")
    app.include_router(intake.router, prefix="/api/v1")

    app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
    
    return app


app = create_app()
