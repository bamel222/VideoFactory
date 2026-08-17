from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str
    user_id: int
    workspace_id: int


class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str
    role: str = "reviewer"


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: str = "reviewer"


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    active: bool | None = None


class UserOut(ORMModel):
    id: int
    email: str
    name: str
    role: str
    active: bool
