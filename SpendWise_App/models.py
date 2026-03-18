# code for models for database

from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    email: EmailStr = Field(nullable=False, unique=True)

class UserCreate(UserBase):
    password: str = Field(nullable=False)

class UserDetails(UserCreate, table=True):
    user_id: int | None = Field(default=None, primary_key=True)
    created_at: datetime | None = Field(default_factory=lambda: datetime.now(timezone.utc),nullable=False) 

class UserOut(UserCreate):
    user_id: int















