"""Authentication request/response contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole

PASSWORD_POLICY = "At least 8 characters, including one letter and one digit."


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120, examples=["Aakash Malipeddi"])
    email: EmailStr = Field(examples=["student@university.edu"])
    password: str = Field(min_length=8, max_length=128, description=PASSWORD_POLICY)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters long.")
        return cleaned

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if not any(char.isalpha() for char in value):
            raise ValueError("Password must contain at least one letter.")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse
