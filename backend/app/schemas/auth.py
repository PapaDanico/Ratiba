"""Auth schemas — login, token, current user."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DemoWorkspaceRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=128)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    operator_name: str | None = Field(default=None, max_length=128)


class DemoWorkspaceResponse(BaseModel):
    operator_id: uuid.UUID
    operator_name: str
    email: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenOnly(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    operator_id: uuid.UUID
    is_active: bool


class OperatorOut(BaseModel):
    id: uuid.UUID
    aoc_number: str
    name: str
    base: str
    contact_email: str
    tier: str
