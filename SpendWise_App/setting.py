from datetime import datetime
from enum import Enum
from typing import List, Optional
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, relationship

from .database import Base, get_db




router = APIRouter(
    prefix="/settings",
    tags=["Settings"]
)


# =========================================================
# ENUMS
# =========================================================
class TransportationType(str, Enum):
    public = "public"
    bike = "bike"
    electric = "electric"
    normal = "normal"


# =========================================================
# SQLALCHEMY MODELS
# =========================================================
# If you already created these inside models.py,
# move them there and import them instead.
class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)

    email_or_phone = Column(String, nullable=True)
    monthly_income = Column(Float, nullable=False, default=0.0)
    household_size = Column(Integer, nullable=False, default=1)

    transportation_type = Column(String, nullable=False, default=TransportationType.public.value)
    monthly_transport_spending = Column(Float, nullable=False, default=0.0)
    monthly_utility_bill = Column(Float, nullable=False, default=0.0)

    price_increase_alerts = Column(Boolean, nullable=False, default=True)
    budget_threshold_alerts = Column(Boolean, nullable=False, default=True)
    alert_threshold = Column(Integer, nullable=False, default=80)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    previous_expenses = relationship(
        "PreviousExpense",
        back_populates="settings",
        cascade="all, delete-orphan"
    )


class PreviousExpense(Base):
    __tablename__ = "previous_expenses"

    id = Column(Integer, primary_key=True, index=True)
    settings_id = Column(Integer, ForeignKey("user_settings.id", ondelete="CASCADE"), nullable=False, index=True)

    month = Column(String, nullable=False)  # Example: "January", "2026-01", etc.
    food = Column(Float, nullable=False, default=0.0)
    transport = Column(Float, nullable=False, default=0.0)
    utilities = Column(Float, nullable=False, default=0.0)
    entertainment = Column(Float, nullable=False, default=0.0)
    shopping = Column(Float, nullable=False, default=0.0)
    healthcare = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    settings = relationship("UserSettings", back_populates="previous_expenses")


# =========================================================
# PYDANTIC SCHEMAS
# =========================================================
class SettingsPayload(BaseModel):
    email_or_phone: Optional[str] = Field(default=None, max_length=100)
    monthly_income: float = Field(default=0, ge=0)
    household_size: int = Field(default=1, ge=1)
    transportation_type: TransportationType = TransportationType.public
    monthly_transport_spending: float = Field(default=0, ge=0)
    monthly_utility_bill: float = Field(default=0, ge=0)
    price_increase_alerts: bool = True
    budget_threshold_alerts: bool = True
    alert_threshold: int = Field(default=80, ge=1, le=100)

    @field_validator("email_or_phone")
    @classmethod
    def validate_contact(cls, value: Optional[str]):
        if value is None:
            return None

        value = value.strip()
        if value == "":
            return None

        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        phone_regex = r"^\+?[0-9\s\-]{7,20}$"

        if not re.match(email_regex, value) and not re.match(phone_regex, value):
            raise ValueError("Enter a valid email or phone number.")
        return value


class SettingsResponse(SettingsPayload):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PreviousExpenseRow(BaseModel):
    # must match React input type="month", e.g. 2025-12
    month: str = Field(..., min_length=7, max_length=7)
    food: float = Field(default=0, ge=0)
    transport: float = Field(default=0, ge=0)
    utilities: float = Field(default=0, ge=0)
    entertainment: float = Field(default=0, ge=0)
    shopping: float = Field(default=0, ge=0)
    healthcare: float = Field(default=0, ge=0)

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str):
        if not re.match(r"^\d{4}-\d{2}$", value):
            raise ValueError("Month must be in YYYY-MM format.")
        year, month = value.split("-")
        month_num = int(month)
        if month_num < 1 or month_num > 12:
            raise ValueError("Month must be between 01 and 12.")
        return value


class PreviousExpenseBulkPayload(BaseModel):
    expenses: List[PreviousExpenseRow]

    @field_validator("expenses")
    @classmethod
    def validate_unique_months(cls, value):
        months = [e.month for e in value]
        if len(months) != len(set(months)):
            raise ValueError("Duplicate months are not allowed.")
        return value


class PreviousExpenseResponse(PreviousExpenseRow):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FullSettingsResponse(SettingsResponse):
    previous_expenses: List[PreviousExpenseResponse] = []

    model_config = {"from_attributes": True}

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def get_settings_by_user_id(db: Session, user_id: int) -> Optional[UserSettings]:
    return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()


def create_default_settings(db: Session, user_id: int) -> UserSettings:
    settings = UserSettings(
        user_id=user_id,
        email_or_phone=None,
        monthly_income=0.0,
        household_size=1,
        transportation_type=TransportationType.public.value,
        monthly_transport_spending=0.0,
        monthly_utility_bill=0.0,
        price_increase_alerts=True,
        budget_threshold_alerts=True,
        alert_threshold=80,
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


# =========================================================
# ROUTES
# =========================================================

@router.get("/{user_id}", response_model=FullSettingsResponse)
def get_user_settings(user_id: int, db: Session = Depends(get_db)):
    """
    Load all settings for Settings page.
    Auto-creates defaults if missing.
    """
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)
    return settings


@router.put("/{user_id}", response_model=SettingsResponse)
def save_settings(user_id: int, payload: SettingsPayload, db: Session = Depends(get_db)):
    """
    Saves:
    - contact
    - income
    - household size
    - transport type
    - transport spend
    - utility bill
    - alert toggles
    - alert threshold
    """
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    try:
        settings.email_or_phone = payload.email_or_phone
        settings.monthly_income = payload.monthly_income
        settings.household_size = payload.household_size
        settings.transportation_type = payload.transportation_type.value
        settings.monthly_transport_spending = payload.monthly_transport_spending
        settings.monthly_utility_bill = payload.monthly_utility_bill
        settings.price_increase_alerts = payload.price_increase_alerts
        settings.budget_threshold_alerts = payload.budget_threshold_alerts
        settings.alert_threshold = payload.alert_threshold
        settings.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(settings)
        return settings

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save settings."
        )



@router.get("/{user_id}/previous-expenses", response_model=List[PreviousExpenseResponse])
def get_previous_expenses(user_id: int, db: Session = Depends(get_db)):
    """
    Load previous expenses table.
    """
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    rows = (
        db.query(PreviousExpense)
        .filter(PreviousExpense.settings_id == settings.id)
        .order_by(PreviousExpense.month.desc())
        .all()
    )
    return rows



@router.put("/{user_id}/previous-expenses", response_model=List[PreviousExpenseResponse])
def save_previous_expenses(
    user_id: int,
    payload: PreviousExpenseBulkPayload,
    db: Session = Depends(get_db)
):
    """
    Matches the UI 'Save Previous Expenses' button.
    Replaces the entire table with the submitted rows.
    """
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    try:
        db.query(PreviousExpense).filter(
            PreviousExpense.settings_id == settings.id
        ).delete()

        new_rows = []
        for row in payload.expenses:
            record = PreviousExpense(
                settings_id=settings.id,
                month=row.month,
                food=row.food,
                transport=row.transport,
                utilities=row.utilities,
                entertainment=row.entertainment,
                shopping=row.shopping,
                healthcare=row.healthcare,
            )
            db.add(record)
            new_rows.append(record)

        db.commit()

        for row in new_rows:
            db.refresh(row)

        return new_rows

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save previous expenses."
        )

@router.delete("/{user_id}/previous-expenses/{expense_id}", status_code=status.HTTP_200_OK)
def delete_previous_expense(user_id: int, expense_id: int, db: Session = Depends(get_db)):
    """
    Delete one imported expense row.
    """
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settings not found for this user."
        )

    expense = (
        db.query(PreviousExpense)
        .filter(
            PreviousExpense.id == expense_id,
            PreviousExpense.settings_id == settings.id
        )
        .first()
    )

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Previous expense row not found."
        )

    try:
        db.delete(expense)
        db.commit()
        return {"success":True}

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete previous expense row."
        )
    