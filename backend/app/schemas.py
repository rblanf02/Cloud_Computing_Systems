from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    can_read: bool
    can_write: bool
    can_update: bool
    is_admin: bool
    created_at: datetime


class FileOut(BaseModel):
    id: int
    owner_id: int
    owner_username: str
    filename: str
    content_type: str | None
    current_version: int
    size_bytes: int
    version_created_at: datetime
    created_at: datetime


class FileVersionOut(BaseModel):
    id: int
    version_number: int
    size_bytes: int
    content_type: str | None
    created_at: datetime
    created_by: int
    created_by_username: str


class UserPermissionsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_read: bool | None = None
    can_write: bool | None = None
    can_update: bool | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Message(BaseModel):
    detail: str
