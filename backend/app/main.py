from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import admin, auth, files, logs
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


def ensure_schema() -> None:
    if engine.dialect.name != "postgresql":
        return

    migrations = [
        ("users", "quota_bytes", "BIGINT NOT NULL DEFAULT 1073741824"),
        ("files", "deleted_at", "TIMESTAMP WITH TIME ZONE"),
        ("file_versions", "content_type", "VARCHAR(100)"),
        ("file_versions", "sha256", "VARCHAR(64)"),
    ]

    with engine.begin() as connection:
        for table, column, ddl in migrations:
            connection.execute(
                text(
                    f"ALTER TABLE {table} "
                    f"ADD COLUMN IF NOT EXISTS {column} {ddl}"
                )
            )


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
    ensure_schema()
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
    app.include_router(logs.router)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
