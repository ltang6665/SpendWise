# code for models for database
# login schema not neccessary just use OAuth2PasswordRequestForm

from datetime import datetime, timezone, date
from email.policy import default
import re
from typing import Annotated, Optional
from pydantic import EmailStr, field_validator
from sqlmodel import Field, Relationship, SQLModel, text, AutoString, Column, String, ARRAY
from .utils import TransportationType


class UserBase(SQLModel):
    # index=True tells SQLModel to ask the database to create an index
    # makes lookups and filters on it faster.
    Email: EmailStr = Field(unique=True, sa_type=AutoString, index=True) #auto string?????
    Active: bool | None = Field(default=True) # check if user is banned

class UserCreate(UserBase):
    Password: str  # plain password

class RefreshToken(SQLModel):
    RefreshToken: str | None = Field(default=None)

class UserDetails(UserBase, RefreshToken, table=True):
    __tablename__ = "user_details" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    HashedPassword: str = Field(index=True)
    UserType: str = Field(default="user")
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
    UpdatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP")
        }
    )
    PreviousExpenses: list["PreviousExpenseDB"] = Relationship(back_populates="UserDetails")
    AddedExpenses: list["ExpensesDB"] = Relationship(back_populates="UserDetails")

# Annotated[UserResponse, Depends(get_current_active_user)] avoid returning iportant data --> use id to fetch from db?
class UserResponse(UserBase):
    UserId: int

class Token(RefreshToken):
    AccessToken: str
    TokenType: str
    UserType: str

class UserExpenses(SQLModel): 
    Type: str # change to enum
    ItemName: str 
    AmountSpent: float 
    DatePurchased: date
    Note: str | None = None

class ExpensesDB(UserExpenses, table=True):
    __tablename__ = "user_expenses" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key = "user_details.id", index=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
    UpdatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP")
        }
    )
    UserDetails: "UserDetails" = Relationship(back_populates="AddedExpenses")

# for the budget page (add check to make sure addition makes sense? or do in method/route)
class UserBudget(SQLModel):
    AutoBudget: bool = True
    TotalBudget: int
    Food: int
    Transport: int
    Utilities: int
    Entertainment: int
    Shopping: int
    Healthcare: int

class BudgetDB(UserBudget, table=True):
    __tablename__ = "user_budget" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key = "user_details.id", index=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
    UpdatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP")
        }
    )

class UserSettings(SQLModel):
    MonthlyIncome: float = Field(default=0.0, ge=0)
    HouseholdSize: int = Field(default=1, ge=1)
    TransportationTypes: TransportationType = TransportationType.default
    #TransportationTypes: list[str] = Field(sa_column=Column(ARRAY(String)))
    MonthlyTransportSpending: float = Field(default=0.0, ge=0)
    MonthlyUtilityBill: float = Field(default=0.0, ge=0)
    PriceIncreaseAlerts: bool = True
    BudgetThresholdAlerts: bool = True
    AlertThreshold: int = Field(default=80, ge=1, le=100)

class UserSettingsDB(UserSettings, table=True):
    __tablename__ = "user_settings"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key="user_details.id", index=True)
    Email: EmailStr # same email used for account creation
    SetupMode: str = "none" # "none" | "quick" | "detailed" | "skipped"
    SetupCompleted: bool = False

    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
    UpdatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP")
        }
    )
    PreviousExpenses: list["PreviousExpenseDB"] = Relationship(
        back_populates="Settings",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class QuickSetup(SQLModel):
    MonthlyIncome: float
    Email: EmailStr

class UserSetup(SQLModel):
    MonthlyIncome: float
    HouseholdSize: int 
    TransportationTypes: list[TransportationType] = Field(default_factory=list) # tells postgres it is storing a list unique to everybody
    PriceIncreaseAlerts: bool = True
    BudgetThresholdAlerts: bool = True
    AlertThreshold: int = Field(default=80, ge=1, le=100)










class PreviousExpense(SQLModel):
    Month: str = Field(min_length=7, max_length=7, description="format: YYYY-MM")
    Food: float = Field(default=0.0, ge=0)
    Transport: float = Field(default=0.0, ge=0)
    Utilities: float = Field(default=0.0, ge=0)
    Entertainment: float = Field(default=0.0, ge=0)
    Shopping: float = Field(default=0.0, ge=0)
    Healthcare: float = Field(default=0.0, ge=0)

    @field_validator("Month")
    @classmethod
    def validate_month(cls, value: str):
        if not re.match(r"^\d{4}-\d{2}$", value):
            raise ValueError("Month must be in YYYY-MM format.")
        return value

class PreviousExpenseDB(PreviousExpense, table=True):
    __tablename__ = "previous_expenses" # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key = "user_details.id", index=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )    
    UpdatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP")
        }
    )
    UserDetails: "UserDetails" = Relationship(back_populates="PreviousExpenses")

class AllPreviousExpenses(SQLModel):
    AllExpenseRows: list[PreviousExpense]

    @field_validator("AllExpenseRows")
    @classmethod
    def validate_unique_months(cls, value):
        months = [e.Month for e in value]
        if len(months) != len(set(months)):
            raise ValueError("Duplicate months are not allowed.")
        return value
    
class DeleteExpensesRequest(SQLModel):
    expenses_ids: list[int]














