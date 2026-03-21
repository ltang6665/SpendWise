# code for models for database
# login schema not neccessary just use OAuth2PasswordRequestForm

from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import EmailStr
from sqlmodel import Field, SQLModel, text


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True)
    active: bool = Field(default=False)

class UserCreate(UserBase):
    password: str  # plain password

class UserDetails(UserBase, table=True):
    __tablename__ = "user_details" # type: ignore
    user_id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
    hashed_password: str 

class UserResponse(UserBase):
    user_id: int

class Token(SQLModel):
    access_token: str
    token_type: str

class TokenData(SQLModel):
    email: str # | None = None #???
    #user_type: str














