from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    can_read = Column(Boolean, default=True, nullable=False)
    can_write = Column(Boolean, default=False, nullable=False)
    can_update = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    files = relationship("File", back_populates="owner")
    versions = relationship("FileVersion", back_populates="created_by_user")


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    current_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="files")
    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")


class FileVersion(Base):
    __tablename__ = "file_versions"

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    blob_name = Column(String(500), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    file = relationship("File", back_populates="versions")
    created_by_user = relationship("User", back_populates="versions")


class LogEvent(Base):
    __tablename__ = "log_events"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    username = Column(String(50), nullable=True)
    action = Column(String(50), nullable=False)
    resource = Column(String(255), nullable=True)
    result = Column(String(20), nullable=False, default="OK")
    details = Column(String(500), nullable=True)
