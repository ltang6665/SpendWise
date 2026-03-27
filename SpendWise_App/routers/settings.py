from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlmodel import Session, delete
from ..utils import get_password_hash
from ..models import *
from ..oauth2 import *
from ..database import *

router = APIRouter(
    prefix="/settings",
    tags=['Settings']
)

def get_settings_by_user_id(db: Session, user_id: int) -> Optional[UserSettings]:
    # relationship/foreign key search (where)?
    statement = select(UserSettingsDB).where(UserSettingsDB.UserId == user_id) #user id or id
    return db.exec(statement).first()


def create_default_settings(db: Session, user_id: int) -> UserSettings:
    settings = UserSettings(
        UserId=user_id,
        EmailOrPhone=None,
        MonthlyIncome=0.0,
        HouseholdSize=1,
        TransportationType=TransportationEnum.public,
        MonthlyTransportSpending=0.0,
        MonthlyUtilityBill=0.0,
        PriceIncreaseAlerts=True,
        BudgetThresholdAlerts=True,
        AlertThreshold=80,
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings

@router.get("/{user_id}", response_model=FullSettingsResponse)
def get_user_settings(user_id: int, db: SessionDependency):
    """Load all settings. Auto-creates defaults if missing."""
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)
    return settings


@router.put("/{user_id}", response_model=UserSettings)
def save_settings(user_id: int, payload: UserSettings, db: SessionDependency):
    """Updates user settings fields."""
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    try:
         # check how frontend handles the data input?
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(settings, key, value)
        
        settings.UpdatedAt = datetime.utcnow() # change 

        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save settings."
        )



"""@router.get("/{user_id}/previous-expenses", response_model=List[PreviousExpenseResponse])
def get_previous_expenses(user_id: int, db: Session = Depends(get_db)):

    Load previous expenses table.

    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    rows = (
        db.query(PreviousExpense)
        .filter(PreviousExpense.settings_id == settings.id)
        .order_by(PreviousExpense.month.desc())
        .all()
    )
    return rows"""


# for importing previous expenses and saving to db
@router.put("/{user_id}/previous-expenses", response_model=list[PreviousExpense]) # no need response model?
def save_previous_expenses(
    user_id: int,
    payload: AllPreviousExpenses,
    db: SessionDependency
):
    """Replaces all previous expense rows for a user."""
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    try:
        # Delete existing rows using SQLModel delete statement
        statement = delete(PreviousExpenseDB).where(PreviousExpenseDB.SettingsId == settings.Id)
        db.exec(statement)

        new_rows = []
        for row_data in payload.AllExpensesRows:
            # Create new record using PascalCase fields
            record = PreviousExpense(
                **row_data.model_dump() 
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

# for deleting past expenses that were already saved into the db
@router.delete("/{user_id}/previous-expenses/{expense_id}")
def delete_previous_expense(user_id: int, expense_id: int, db: SessionDependency)):
    """Delete a specific expense row."""
    # Verify settings exist first
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found.")

    # Find the specific row
    statement = select(PreviousExpenseDB).where(
        PreviousExpenseDB.id == expense_id,
        PreviousExpenseDB.SettingsId == settings.Id #??
    )
    expense = db.exec(statement).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Expense record not found.")

    try:
        db.delete(expense)
        db.commit()
        return {"success": True}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Deletion failed.")
    