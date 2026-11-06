from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
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
    quota_bytes = Column(BigInteger, nullable=False, default=1073741824)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    files = relationship("File", back_populates="owner")
    versions = relationship("FileVersion", back_populates="created_by_user")
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True, index=True)

    user = relationship("User", back_populates="sessions")


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("owner_id", "filename", name="uq_files_owner_filename"),
    )

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    current_version = Column(Integer, default=0, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="files")
    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")


class FileVersion(Base):
    __tablename__ = "file_versions"
    __table_args__ = (
        UniqueConstraint(
            "file_id",
            "version_number",
            name="uq_versions_file_number",
        ),
    )

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    content_type = Column(String(100), nullable=True)
    blob_name = Column(String(500), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    file = relationship("File", back_populates="versions")
    created_by_user = relationship("User", back_populates="versions")


class LogEvent(Base):
    __tablename__ = "log_events"

    id = Column(Integer, primary_key=True)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    username = Column(String(50), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource = Column(String(255), nullable=True)
    result = Column(String(20), nullable=False, default="OK", index=True)
    details = Column(String(500), nullable=True)

class FileShare(Base):
    __tablename__ = "file_shares"

    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), primary_key=True)
    granted_to = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    granted_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_level = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    file = relationship("File", backref="shares")
    receiver = relationship("User", foreign_keys=[granted_to], backref="received_shares")
    granter = relationship("User", foreign_keys=[granted_by], backref="given_shares")