# code for models for database
# login schema not neccessary just use OAuth2PasswordRequestForm

from datetime import datetime, timezone, date
from email.policy import default
import re
from typing import Annotated, Optional
from pydantic import EmailStr, field_validator
from sqlmodel import Field, Relationship, SQLModel, text, AutoString
from .utils import TransportationType as TransportationTypeEnum


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

# Annotated[UserResponse, Depends(get_current_active_user)] avoid returning iportant data --> use id to fetch from db?
class UserResponse(UserBase):
    id: int

class Token(RefreshToken):
    AccessToken: str
    TokenType: str
    UserType: str

class TokenData(SQLModel):
    sub: str # univesal naming convention of the subject eg the email


""" class RefreshTokenDB(RefreshToken):
    __tablename__ = "refresh_tokens" # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
 """
class UserExpenses(SQLModel): 
    type: str # change to enum
    ItemName: str 
    AmountSpent: float 
    DatePurchased: date
    note: str | None = None

class ExpensesDB(UserExpenses, table=True):
    __tablename__ = "user_expenses" # type: ignore
    # user_id relationship column?
    id: int | None = Field(default=None, primary_key=True)
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

class UserSettingsBase(SQLModel):
    EmailOrPhone: Optional[str] = None
    MonthlyIncome: float = Field(default=0.0, ge=0)
    HouseholdSize: int = Field(default=1, ge=1)
    TransportationType: TransportationTypeEnum = Field(default=TransportationTypeEnum.public)
    MonthlyTransportSpending: float = Field(default=0.0, ge=0)
    MonthlyUtilityBill: float = Field(default=0.0, ge=0)
    PriceIncreaseAlerts: bool = True
    BudgetThresholdAlerts: bool = True
    AlertThreshold: int = Field(default=80, ge=1, le=100)

# class UserSettingsBase(SQLModel):
#     UserId: int = Field(foreign_key="user_details.id", unique=True, index=True)
#     EmailOrPhone: Optional[str] = None
#     MonthlyIncome: float = Field(default=0.0, ge=0)
#     HouseholdSize: int = Field(default=1, ge=1)
#     TransportationType: TransportationTypeEnum = Field(default(TransportationTypeEnum.public))
#     MonthlyTransportSpending: float = Field(default=0.0, ge=0)
#     MonthlyUtilityBill: float = Field(default=0.0, ge=0)
#     PriceIncreaseAlerts: bool = True
#     BudgetThresholdAlerts: bool = True
#     AlertThreshold: int = Field(default=80, ge=1, le=100)

class UserSettingsDB(UserSettingsBase, table=True):
    __tablename__ = "user_settings"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)

    # link to user
    UserId: int = Field(
        foreign_key="user_details.id",
        unique=True,
        index=True
    )

    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )

    UpdatedAt: datetime | None = None

    PreviousExpenses: list["PreviousExpenseDB"] = Relationship(
        back_populates="Settings",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    SetupMode: str = Field(default="none")  
    # "none" | "quick" | "detailed" | "skipped"

    SetupCompleted: bool = Field(default=False)
    


class UserSettingsRead(SQLModel):
    id: int
    UserId: int
    EmailOrPhone: Optional[str]
    MonthlyIncome: float
    HouseholdSize: int
    TransportationType: TransportationTypeEnum
    MonthlyTransportSpending: float
    MonthlyUtilityBill: float
    PriceIncreaseAlerts: bool
    BudgetThresholdAlerts: bool
    AlertThreshold: int
    SetupMode: str
    SetupCompleted: bool
    CreatedAt: datetime
    UpdatedAt: datetime | None = None

class UserSettingsUpdate(SQLModel):
    EmailOrPhone: Optional[str] = None
    MonthlyIncome: Optional[float] = Field(default=None, ge=0)
    HouseholdSize: Optional[int] = Field(default=None, ge=1)
    TransportationType: Optional[TransportationTypeEnum] = None
    MonthlyTransportSpending: Optional[float] = Field(default=None, ge=0)
    MonthlyUtilityBill: Optional[float] = Field(default=None, ge=0)
    PriceIncreaseAlerts: Optional[bool] = None
    BudgetThresholdAlerts: Optional[bool] = None
    AlertThreshold: Optional[int] = Field(default=None, ge=1, le=100)

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

class AllPreviousExpenses(SQLModel):
    AllExpenseRows: list[PreviousExpense]

    @field_validator("AllExpenseRows")
    @classmethod
    def validate_unique_months(cls, value):
        months = [e.Month for e in value]
        if len(months) != len(set(months)):
            raise ValueError("Duplicate months are not allowed.")
        return value
    
class PreviousExpenseDB(PreviousExpense, table=True):
    __tablename__ = "previous_expenses" # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    CreatedAt: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )    
    #??
    SettingsId: int = Field(
        foreign_key="user_settings.id", 
        ondelete="CASCADE", 
        nullable=False, 
        index=True
    )
    
    Settings: Optional["UserSettingsDB"] = Relationship(back_populates="PreviousExpenses")

class FullSettingsResponse(UserSettingsRead):
    # Id: int
    # UserId: int
    # CreatedAt: datetime
    # UpdatedAt: datetime
    PreviousExpenses: list[PreviousExpense] = []

class QuickSetupPayload(SQLModel):
    MonthlyIncome: float












