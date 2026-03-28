# code for models for database
# login schema not neccessary just use OAuth2PasswordRequestForm

from datetime import datetime, timezone, date
from typing import Annotated
from pydantic import EmailStr
from sqlmodel import Field, SQLModel, text, AutoString


class UserBase(SQLModel):
    # index=True tells SQLModel to ask the database to create an index
    # makes lookups and filters on it faster.
    email: EmailStr = Field(unique=True, sa_type=AutoString, index=True) #auto string?????
    active: bool | None = Field(default=True) # check if user is banned

class UserCreate(UserBase):
    password: str  # plain password

class RefreshToken(SQLModel):
    RefreshToken: str | None = Field(default=None)

class UserDetails(UserBase, RefreshToken, table=True):
    __tablename__ = "user_details" # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
    HashedPassword: str = Field(index=True)
    UserType: str = Field(default="user")

class UserResponse(UserBase):
    id: int

class Token(RefreshToken):
    AccessToken: str
    TokenType: str
    UserType: str

class TokenData(SQLModel):
    sub: str # | None = None #??? univesal naming convention of the subject eg the email


""" class RefreshTokenDB(RefreshToken):
    __tablename__ = "refresh_tokens" # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
 """
class UserExpenses(SQLModel): 
    type: str 
    ItemName: str 
    AmountSpent: float 
    DatePurchased: date
    note: str | None = None

class ExpensesDB(UserExpenses, table=True):
    __tablename__ = "user_expenses" # type: ignore
    # user_id relationship column?
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key = "user_details.id")
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )

class UserMonthly(SQLModel):
    income: int
    HouseholdSize: int
    TransportType: str
    TransportCost: int
    utilities: int 

class MonthlyDB(UserMonthly):
    __tablename__ = "user_Monthly" # type: ignore
    # user_id relationship column?
    id: int | None = Field(default=None, primary_key=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )

class UserAlerts(SQLModel):
    PriceIncrease: bool = False
    BudgetThreshold: bool = False
    AlertThreshold: int

class AlertsDB(UserAlerts):
    __tablename__ = "user_alerts" # type: ignore
    # user_id relationship column?
    id: int | None = Field(default=None, primary_key=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )

class UserBudget(SQLModel):
    AutoBudget: bool = True
    TotalBudget: int
    food: int
    transport: int
    utilities: int
    entertainment: int
    shopping: int
    healthcare: int

class BudgetDB(UserBudget):
    __tablename__ = "user_budget" # type: ignore
    # user_id relationship column?
    id: int | None = Field(default=None, primary_key=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )














