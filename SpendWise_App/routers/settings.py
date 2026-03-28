from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlmodel import Session, delete
from ..utils import TransportationType, get_password_hash
from ..models import *
from ..oauth2 import *
from ..database import *


router = APIRouter(
    prefix="/settings",
    tags=['Settings']
)

def get_settings_by_user_id(db: Session, user_id: int) -> Optional[UserSettingsDB]: #used to check if user already has settings saved in the db and return it
    # relationship/foreign key search (where) --> search for settings with the user id (foreign key)
    statement = select(UserSettingsDB).where(UserSettingsDB.UserId == user_id) #user id or id
    return db.exec(statement).first()


def create_default_settings(db: Session, user_id: int) -> UserSettingsDB: #if not, create default settings for the user
    settings = UserSettingsDB(
        UserId=user_id,
        EmailOrPhone=None,
        MonthlyIncome=0.0,
        HouseholdSize=1,
        #TransportationType=TransportationEnum.public,
        TransportationType=TransportationTypeEnum.public,
        MonthlyTransportSpending=0.0,
        MonthlyUtilityBill=0.0,
        PriceIncreaseAlerts=True,
        BudgetThresholdAlerts=True,
        AlertThreshold=80,
        SetupMode="none",
        SetupCompleted=False,
        UpdatedAt=datetime.utcnow(),
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings

@router.get("/{user_id}", response_model=FullSettingsResponse) #create default settings if user does not have settings saved in db yet
def get_user_settings(user_id: int, db: SessionDependency):
    """Load all settings. Auto-creates defaults if missing."""
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)
    return settings


#to update (save) a user’s settings in the database.
@router.put("/{user_id}", response_model=UserSettingsRead) 
def save_settings(user_id: int, payload: UserSettingsUpdate, db: SessionDependency):
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
        statement = delete(PreviousExpenseDB).where(PreviousExpenseDB.SettingsId == settings.id)
        db.exec(statement)

        new_rows = []
        for row_data in payload.AllExpenseRows:
            # Create new record using PascalCase fields
            record = PreviousExpenseDB(
                **row_data.model_dump(), SettingsId=settings.id 
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
def delete_previous_expense(user_id: int, expense_id: int, db: SessionDependency):
    """Delete a specific expense row."""
    # Verify settings exist first
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found.")

    # Find the specific row
    statement = select(PreviousExpenseDB).where(
        PreviousExpenseDB.id == expense_id,
        PreviousExpenseDB.SettingsId == settings.id 
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

# FOR QUICK SETUP, DETAILED SETUP AND FILL IN LATER OPTIONS

#FILL IN LATER OPTION
@router.post("/{user_id}/skip")
def skip_setup(user_id: int, db: SessionDependency):
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    settings.SetupMode = "skipped"
    settings.SetupCompleted = False
    settings.UpdatedAt = datetime.utcnow()

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings

#QUICK SETUP OPTION
@router.put("/{user_id}/quick-setup", response_model=UserSettingsRead)
def quick_setup(user_id: int, payload: QuickSetupPayload, db: SessionDependency):
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    settings.MonthlyIncome = payload.MonthlyIncome
    settings.SetupMode = "quick"
    settings.SetupCompleted = True
    settings.UpdatedAt = datetime.utcnow()

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings

#DETAILED SETUP OPTION
@router.put("/{user_id}/detailed-setup", response_model=UserSettingsRead)
def detailed_setup(user_id: int, payload: UserSettingsUpdate, db: SessionDependency):
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        settings = create_default_settings(db, user_id)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(settings, key, value)

    settings.SetupMode = "detailed"
    settings.SetupCompleted = True
    settings.UpdatedAt = datetime.utcnow()

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings
    