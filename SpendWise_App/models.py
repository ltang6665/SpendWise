# code for models for database
# login schema not neccessary just use OAuth2PasswordRequestForm

from datetime import datetime, date 
from .enums import *
import re
import math
from pydantic import AfterValidator, EmailStr, field_validator
from sqlalchemy import DateTime, text
from sqlmodel import Field, Relationship, SQLModel, text, AutoString, Column, String, ARRAY, BigInteger
from typing import Annotated, Optional



def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(v) > 100:
        raise ValueError("Password has a maximum length of 100 characters")
    if not any(char.isdigit() for char in v):
        raise ValueError("Password must contain at least one number")
    if not any(char.isupper() for char in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>+]", v):
        raise ValueError("Password must contain at least one special character")
    return v

StrongPassword = Annotated[str, AfterValidator(validate_password_strength)]

class UserBase(SQLModel):
    # index=True tells SQLModel to ask the database to create an index
    # makes lookups and filters on it faster.S
    Email: EmailStr = Field(unique=True, sa_type=AutoString, index=True) #auto string?????
    Active: bool | None = Field(default=True) # check if user is banned

class UserCreate(UserBase):
    Password: StrongPassword # plain password

class UserVerifyPassword(SQLModel):
    Password: str # plain password to compare to db pw

class UserChangePassword(SQLModel):
    CurrentPassword: str
    Password: StrongPassword
    RePassword: StrongPassword # re-enter the same pw

class UserDeleteAccount(UserVerifyPassword):
    IsSure: bool = False # ask user if they are sure they want to delete their account 
    DataDelete: bool = False # warn user all data will be deleted

class RefreshToken(SQLModel):
    RefreshToken: str | None = Field(default=None)

class UserDetails(UserBase, RefreshToken, table=True):
    __tablename__ = "user_details" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    HashedPassword: str = Field(index=True)
    UserType: str = Field(default="user")
    EmailVerified: bool = Field(default=False)  # Email verification status
    PendingEmail: EmailStr | None = Field(default=None, sa_type=AutoString) # for change of email in settings
    VerificationCode: str | None = Field(default=None)  # Code sent to email
    VerificationCodeExpiry: datetime | None = Field(default=None)  # Expiry time for verification code
    VerificationCodeFailedAttempts: int = Field(default=0)
    ResetToken: str | None = Field(default=None)  # Token for password reset
    ResetTokenExpiry: datetime | None = Field(default=None)  # Expiry time for reset token
    ResetTokenFailedAttempts: int = Field(default=0)
    LockToken: str | None = Field(default=None, sa_type=AutoString)
    TelegramChatId: int | None = Field(
        default=None, 
        index=True, 
        sa_type=BigInteger  # This forces SQLAlchemy to use a 64-bit BIGINT
    )
    TelegramLinkCode: str | None = Field(default=None) # Keyed digest of a temporary 6-digit code
    TelegramLinkCodeExpiry: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
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

    AddedExpenses: list["ExpensesDB"] = Relationship(back_populates="UserDetails", cascade_delete=True)
    AddedBasket: list["BasketDB"] = Relationship(back_populates="UserDetails", cascade_delete=True)
    MonthlyTotal: list["MonthlyCategoryDB"] = Relationship(back_populates="UserDetails", cascade_delete=True)
    BasketTotal: "BasketCategoryDB" = Relationship(back_populates="UserDetails", cascade_delete=True)
    UserBudget: "UserBudgetDB" = Relationship(back_populates="UserDetails", cascade_delete=True)
    UserSettings: "UserSettingsDB" = Relationship(back_populates="UserDetails", cascade_delete=True)
    UserAlerts: list["AlertDB"] = Relationship(back_populates="UserDetails", cascade_delete=True)
    # Money others owe you (Tabs where you are the Payer)
    OwedTabs: list["GroupLedgerDB"] = Relationship(
        back_populates="Payer", 
        sa_relationship_kwargs={"foreign_keys": "[GroupLedgerDB.PayerId]"}
    )
    # Money you owe others (Tabs where you are the Owee)
    OwingTabs: list["GroupLedgerDB"] = Relationship(
        back_populates="Owee", 
        sa_relationship_kwargs={"foreign_keys": "[GroupLedgerDB.OweeId]"}
    )
    UserChallenge: list["GroupChallengeDB"] = Relationship(back_populates="UserDetails", cascade_delete=True)


class TelegramLinkAttemptDB(SQLModel, table=True):
    __tablename__ = "telegram_link_attempts"  # type: ignore

    TelegramId: int = Field(primary_key=True, sa_type=BigInteger)
    FailedAttempts: int = Field(default=0, nullable=False)
    WindowStartedAt: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    LockedUntil: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    

# Avoid returning iportant data --> use id to fetch from db?
class UserResponse(UserBase):
    Id: int

class Token(RefreshToken):
    AccessToken: str
    TokenType: str
    UserType: str

class TokenData(SQLModel):
    Sub: str

# Email verification
class VerifyEmailRequest(SQLModel):
    Email: EmailStr
    VerificationCode: str

# Forgot password - request reset
class ForgotPasswordRequest(SQLModel):
    Email: EmailStr

# Forgot password - verify code and reset
class ResetPasswordRequest(SQLModel):
    Email: EmailStr
    ResetCode: str
    NewPassword: StrongPassword
    ReNewPassword: StrongPassword

    @field_validator("ReNewPassword")
    @classmethod
    def passwords_match(cls, v, info):
        if info.data.get("NewPassword") != v:
            raise ValueError("Passwords do not match")
        return v

class RequestEmailChange(SQLModel):
    Password: str # Require their current password for security
    NewEmail: EmailStr

class ConfirmEmailChange(SQLModel):
    VerificationCode: str


#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# expenses stuff
class UserExpensesBase(SQLModel): 
    Type: str # change to enum?
    ItemName: str 
    AmountSpent: float = Field(gt=0)
    Note: str | None = None

    @field_validator("AmountSpent")
    @classmethod
    def amount_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Amount must be finite")
        return value

class UserExpenses(UserExpensesBase):
    Recurring: bool = False
    DatePurchased: date # uses yyyy-mm-dd format

class ExpensesDB(UserExpenses, table=True):
    __tablename__ = "user_expenses" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key = "user_details.Id", index=True, ondelete="CASCADE")
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

class BasketDB(UserExpensesBase, table=True):
    __tablename__ = "user_basket" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key = "user_details.Id", index=True, ondelete="CASCADE")
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
    UserDetails: "UserDetails" = Relationship(back_populates="AddedBasket")

class DeleteBasketExpenses(SQLModel):
    BasketExpensesId: list[int]

class DeleteMonthlyExpenses(SQLModel):
    MonthlyExpensesId: list[int]

class ExpensesByCategory(SQLModel):
    Food: float = Field(default=0.0, ge=0)
    Transport: float = Field(default=0.0, ge=0)
    Utilities: float = Field(default=0.0, ge=0)
    Entertainment: float = Field(default=0.0, ge=0)
    Shopping: float = Field(default=0.0, ge=0)
    Healthcare: float = Field(default=0.0, ge=0)
    Other: float = Field(default=0.0, ge=0)

class MonthlyCategory(ExpensesByCategory):
    Month: str = Field(min_length=7, max_length=7, index=True, description="format: YYYY-MM")

    @field_validator("Month")
    @classmethod
    def validate_month(cls, value: str):
        if not re.match(r"^\d{4}-\d{2}$", value):
            raise ValueError("Month must be in YYYY-MM format.")
        return value
    
class MonthlyCategoryDB(MonthlyCategory, table=True):
    __tablename__ = "monthly_category_total_spending" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key = "user_details.Id", index=True, ondelete="CASCADE")
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
    UserDetails: "UserDetails" = Relationship(back_populates="MonthlyTotal")

class BasketCategoryDB(ExpensesByCategory, table=True):
    __tablename__ = "bakset_category_total_spending" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key = "user_details.Id", index=True, ondelete="CASCADE")
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
    UserDetails: "UserDetails" = Relationship(back_populates="BasketTotal")

class ExpenseItem(SQLModel):
    Id: int
    ItemName: str
    AmountSpent: float
    DatePurchased: date
    Recurring: bool = False
    Note: str | None = None
    Type: str

    class Config:
        from_attributes = True

class CategorySummary(SQLModel):
    category: str
    total: float
    expenses: list[ExpenseItem]

class BasketItem(SQLModel):
    Id: int
    ItemName: str
    AmountSpent: float
    Note: str | None = None
    Type: str
 
    class Config:
        from_attributes = True

class BasketSummary(SQLModel):
    Category: str
    Total: float
    Basket: list[BasketItem]


#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# for the budget page (add check to make sure addition makes sense? or do in method/route)
class UserBudget(ExpensesByCategory):
    TotalBudget: float
    AutoBudget: bool = True

class UserBudgetDB(UserBudget, table=True):
    __tablename__ = "user_budget" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key = "user_details.Id", index=True, ondelete="CASCADE")
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
    UserDetails: "UserDetails" = Relationship(back_populates="UserBudget")

class CategoryBudgetInput(SQLModel):
    Food: float | None = Field(default=None, ge=0)
    Transport: float | None = Field(default=None, ge=0)
    Utilities: float | None = Field(default=None, ge=0)
    Entertainment: float | None = Field(default=None, ge=0)
    Shopping: float | None = Field(default=None, ge=0)
    Healthcare: float | None = Field(default=None, ge=0)
    Other: float | None = Field(default=None, ge=0)

class BudgetSettingsRequest(SQLModel):
    AutoBudget: bool
    TotalBudget: float | None = Field(default=None, ge=0)
    CategoryBudgets: CategoryBudgetInput | None = None

class BudgetSettingsResponse(SQLModel):
    AutoBudget: bool
    TotalBudget: float
    Food: float
    Transport: float
    Utilities: float
    Entertainment: float
    Shopping: float
    Healthcare: float
    Other: float
    AutoComputedBudget: float | None = None

class SuggestionActionRequest(SQLModel):
    title: str
    category: str
    action: str  # "accept" or "dismiss"

class UserSuggestionDB(SQLModel, table=True):
    __tablename__ = "user_suggestion_tracking" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key="user_details.Id", index=True, ondelete="CASCADE")
    Month: str = Field(index=True, description="format: YYYY-MM")
    Title: str
    Category: str
    IsAccepted: bool = False
    IsDismissed: bool = False
    
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

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# settings stuff
class UserSettings(SQLModel):
    MonthlyIncome: float = Field(default=0.0, ge=0)
    HouseholdSize: int = Field(default=1, ge=1)
    TransportationTypes: list[TransportationType] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    MonthlyTransportSpending: float = Field(default=0.0, ge=0)
    MonthlyUtilityBill: float = Field(default=0.0, ge=0)

    PriceIncreaseAlerts: bool = True
    BudgetThresholdAlerts: bool = True
    PaceAlerts: bool = True
    AnomalyAlerts: bool = True
    InflationBeaterAlerts: bool = True

    PriceThreshold: int = Field(default=10, ge=1, le=100)
    BudgetThreshold: int = Field(default=80, ge=1, le=100)
    AnomalyThreshold: int = Field(default=25, ge=1, le=100)

class UserSettingsDB(UserSettings, table=True):
    __tablename__ = "user_settings"  # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key="user_details.Id", index=True, ondelete="CASCADE")
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
    UserDetails: "UserDetails" = Relationship(back_populates="UserSettings")

class UserSettingsUpdate(SQLModel):
    MonthlyIncome: float | None = Field(default=None, ge=0)
    HouseholdSize: int | None = Field(default=None, ge=1)
    TransportationTypes: list[TransportationType] | None = None
    MonthlyTransportSpending: float | None = Field(default=None, ge=0)
    MonthlyUtilityBill: float | None = Field(default=None, ge=0)

    PriceIncreaseAlerts: bool | None = None
    BudgetThresholdAlerts: bool | None = None
    PaceAlerts: bool | None = None
    AnomalyAlerts: bool | None = None
    InflationBeaterAlerts: bool | None = None

    PriceThreshold: int | None = Field(default=None, ge=1, le=100)
    BudgetThreshold: int | None = Field(default=None, ge=1, le=100)
    AnomalyThreshold: int | None = Field(default=None, ge=1, le=100)


#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# import expenses stuff
class DeleteExpensesRequest(SQLModel):
    expenses_ids: list[int]




#------------------------------------------------------------------------------------------------
#alerts stuff
class AlertBase(SQLModel):
    Title: str
    Message: str
    AlertType: str # use enums instead?

class AlertCheck(AlertBase):
    IsRead: bool = False

class AlertDB(AlertCheck, table=True):
    __tablename__ = "user_alerts" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key="user_details.Id", index=True, ondelete="CASCADE")
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
    UserDetails: "UserDetails" = Relationship(back_populates="UserAlerts")

    

#------------------------------------------------------------------------------------------------
# external data stuff 

class NationalCPIDB(SQLModel, table=True):
    __tablename__ = "national_cpi_data" # type: ignore

    Id: int | None = Field(default=None, primary_key=True)
    Month: str = Field(index=True, description="format: YYYY-MM")
    Category: str = Field(index=True)
    IndexValue: float
    YoYChange: float | None = None
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




#------------------------------------------------------------------------------------------------
# Telegram bot stuff

class SplitBillRequest(SQLModel):
    Amount: float = Field(gt=0)
    ItemName: str
    TelegramIds: list[int] 
    Category: str = "Other" 
    Description: str = "" 

    @field_validator("Amount")
    @classmethod
    def amount_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Amount must be finite")
        return value

class LinkAccountRequest(SQLModel):
    TelegramId: int = Field(gt=0)
    LinkCode: str = Field(min_length=6, max_length=6)

    @field_validator("LinkCode")
    @classmethod
    def validate_link_code(cls, value: str) -> str:
        if not value.isascii() or not value.isdigit():
            raise ValueError("Link code must contain exactly six digits.")
        return value

class TabAddRequest(SQLModel):
    GroupId: int
    PayerTgId: int # Telegram ID
    OweeTgId: int # Telegram ID
    Amount: float
    Description: str

class ChallengeJoinRequest(SQLModel):
    GroupId: int
    TelegramId: int
    Month: str

    @field_validator("Month")
    @classmethod
    def validate_month(cls, value: str):
        if not re.match(r"^\d{4}-\d{2}$", value):
            raise ValueError("Month must be in YYYY-MM format.")
        return value

class SharedGroupBase(SQLModel):
    GroupId: int = Field(sa_type=BigInteger, index=True)

class GroupLedgerDB(SharedGroupBase, table=True):
    __tablename__ = "group_ledger" # type: ignore
    
    Id: int | None = Field(default=None, primary_key=True)
    PayerId: int = Field(foreign_key="user_details.Id", index=True)
    OweeId: int = Field(foreign_key="user_details.Id", index=True)
    Amount: float = Field(ge=0)
    Description: str
    DateAdded: date = Field(default_factory=date.today)
    
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
    # Link the Payer relationship to the PayerId column
    Payer: "UserDetails" = Relationship(
        back_populates="OwedTabs",
        sa_relationship_kwargs={"foreign_keys": "[GroupLedgerDB.PayerId]"}
    )
    # Link the Owee relationship to the OweeId column
    Owee: "UserDetails" = Relationship(
        back_populates="OwingTabs",
        sa_relationship_kwargs={"foreign_keys": "[GroupLedgerDB.OweeId]"}
    )

class GroupChallengeDB(SharedGroupBase, table=True):
    __tablename__ = "group_challenge" # type: ignore
    
    Id: int | None = Field(default=None, primary_key=True)
    UserId: int = Field(foreign_key="user_details.Id", index=True, ondelete="CASCADE")    
    Month: str = Field(min_length=7, max_length=7, index=True, description="format: YYYY-MM")
    
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
    UserDetails: "UserDetails" = Relationship(back_populates="UserChallenge")

    @field_validator("Month")
    @classmethod
    def validate_month(cls, value: str):
        if not re.match(r"^\d{4}-\d{2}$", value):
            raise ValueError("Month must be in YYYY-MM format.")
        return value





