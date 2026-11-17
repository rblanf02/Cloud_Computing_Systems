from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str
    is_admin: bool
    created_at: datetime
    quota_bytes: int


class FileOut(BaseModel):
    file_id: int
    filename: str
    extension: str | None
    owner_id: int
    owner_username: str
    deleted_at: datetime | None = None
    current_version: int | None = None
    size_bytes: int = 0
    uploaded_at: datetime | None = None
    uploaded_by: int | None = None


class FileVersionOut(BaseModel):
    file_id: int
    version_number: int
    blob_name: str
    uploaded_by: int
    uploaded_by_username: str
    uploaded_at: datetime
    size_bytes: int
    sha256: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Message(BaseModel):
    detail: str


class FileShareCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    granted_to_username: str = Field(..., description="Username to grant access to")
    access_level: str = Field(..., pattern="^(lector|editor|gestor|reader|editor|manager)$")


class FileShareOut(BaseModel):
    file_id: int
    granted_to: int
    granted_to_username: str
    granted_by: int
    granted_by_username: str
    access_level: str


class LogEventOut(BaseModel):
    log_id: int
    user_id: int | None
    username: str | None = None
    file_id: int | None
    action: str
    status: str
    ip_address: str | None
    created_at: datetime