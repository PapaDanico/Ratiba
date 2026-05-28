"""Auth schemas — login, token, current user."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
