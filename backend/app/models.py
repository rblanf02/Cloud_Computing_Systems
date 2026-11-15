from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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

    user_id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    quota_bytes = Column(BigInteger, nullable=False, default=1073741824)

    __table_args__ = (
        CheckConstraint("quota_bytes >= 0", name="ck_users_quota_bytes_non_negative"),
    )

    files = relationship("File", back_populates="owner")
    versions_uploaded = relationship("FileVersion", back_populates="uploader")
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
        ForeignKey("users.user_id", ondelete="CASCADE"),
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

    file_id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    extension = Column(String(50), nullable=True)
    owner_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    owner = relationship("User", back_populates="files")
    versions = relationship(
        "FileVersion",
        back_populates="file",
        cascade="all, delete-orphan",
    )
    shares = relationship(
        "FileShare",
        back_populates="file",
        cascade="all, delete-orphan",
    )


class FileVersion(Base):
    __tablename__ = "file_versions"

    file_id = Column(
        Integer,
        ForeignKey("files.file_id", ondelete="CASCADE"),
        primary_key=True,
    )
    version_number = Column(Integer, primary_key=True)
    blob_name = Column(String(500), nullable=False)
    uploaded_by = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False,
        index=True,
    )
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("file_id", "version_number", name="uq_versions_file_number"),
    )

    file = relationship("File", back_populates="versions")
    uploader = relationship("User", back_populates="versions_uploaded")


class FileShare(Base):
    __tablename__ = "file_shares"
    __table_args__ = (
        CheckConstraint(
            "access_level IN ('lector', 'editor', 'gestor')",
            name="ck_file_shares_access_level",
        ),
    )

    file_id = Column(
        Integer,
        ForeignKey("files.file_id", ondelete="CASCADE"),
        primary_key=True,
    )
    granted_to = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    granted_by = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    access_level = Column(String(20), nullable=False)

    file = relationship("File", back_populates="shares")
    receiver = relationship("User", foreign_keys=[granted_to])
    granter = relationship("User", foreign_keys=[granted_by])


class LogEvent(Base):
    __tablename__ = "log_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OK', 'FAIL')",
            name="ck_log_events_status",
        ),
    )

    log_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True, index=True)
    file_id = Column(Integer, nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )