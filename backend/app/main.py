from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import admin, auth, files
from .security import hash_password


def seed_admin() -> None:
    db = SessionLocal()
    try:
        if (
            db.query(User)
            .filter(User.username == settings.seed_admin_username)
            .first()
        ):
            return
        admin = User(
            username=settings.seed_admin_username,
            email=settings.seed_admin_email,
            hashed_password=hash_password(settings.seed_admin_password),
            can_read=True,
            can_write=True,
            can_update=True,
            is_admin=True,
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment != "development":
        if settings.jwt_secret == "dev-only-change-me":
            raise RuntimeError("JWT_SECRET debe configurarse fuera de desarrollo")
        if settings.seed_admin and settings.seed_admin_password == "admin123":
            raise RuntimeError(
                "SEED_ADMIN_PASSWORD debe cambiarse fuera de desarrollo"
            )

    Base.metadata.create_all(bind=engine)
    if settings.seed_admin:
        seed_admin()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CloudFile Exchange API",
        version="0.1.0",
        description="Sistema de intercambio de ficheros con auth, permisos, versiones y LogBook.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    app.include_router(auth.router)
    app.include_router(files.router)
    app.include_router(admin.router)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
