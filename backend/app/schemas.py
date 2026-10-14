from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=72)
    can_read: bool = True
    can_write: bool = False
    can_update: bool = False
    is_admin: bool = False


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


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Message(BaseModel):
    detail: str
