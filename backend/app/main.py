from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import auth
from .security import hash_password

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def seed_admin() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == ADMIN_USERNAME).first():
            return
        admin = User(
            username=ADMIN_USERNAME,
            email="admin@example.com",
            hashed_password=hash_password(ADMIN_PASSWORD),
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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
