from calendar import Month
from math import e
from re import M
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter, Query
from sqlmodel import Session, col, delete
from ..utils import TransportationType, get_password_hash
from ..models import *
from ..oauth2 import *
from ..database import *


router = APIRouter(
    prefix="/settings",
    tags=['Settings']
)

def get_settings_by_user_id(db: Session, user_id: int):
    return db.exec(select(UserSettingsDB).where(UserSettingsDB.UserId == user_id)).first()

def get_user_email(db: Session, user_id: int):
    user = db.exec(select(UserDetails).where(UserDetails.Id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    email = user.Email
    return email

def create_default_settings(db: Session, user_id: int) -> UserSettingsDB: #if not, create default settings for the user
    email = get_user_email(db, user_id)

    settings = UserSettingsDB(
        UserId=user_id,
        Email=email,
        # do not need to set default values
    )

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings

# gets the settings of the user to be displaayed
@router.get("/{user_id}", response_model=UserSettings) 
def get_user_settings(user_id: int, db: SessionDependency):
    settings = get_settings_by_user_id(db, user_id)
    if not settings:
        raise HTTPException(status_code=404, detail="User not found")
    return settings

# to update (save) a user’s settings in the database.
@router.put("/{user_id}", response_model=UserSettingsDB) 
def save_settings(user_id: int, payload: UserSettings, db: SessionDependency):

    settings = db.exec(select(UserSettingsDB).where(UserSettingsDB.UserId == user_id)).first()

    if not settings:
        raise HTTPException(status_code=404, detail="Settings for user {user_id} not found.")

    try:
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(settings, key, value)

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


# FOR QUICK SETUP, DETAILED SETUP AND FILL IN LATER OPTIONS

#FILL IN LATER OPTION
@router.post("/{user_id}/fill-later")
def fill_in_later_setup(user_id: int, db: SessionDependency):

    try:
        email = get_user_email(db, user_id)

        settings = UserSettingsDB(
            UserId=user_id,
            Email=email,
            # do not need to set default values
        )

        db.add(settings)
        db.commit()
        db.refresh(settings)

        return settings

    except Exception as e:
        db.rollback()
        # If they try to create settings for a user that already has them, 
        # Postgres will throw a UniqueConstraint error (if UserId is unique).
        raise HTTPException(
            status_code=400, 
            detail="Settings already exist for this user or the setup failed."
        )

#QUICK SETUP OPTION
@router.post("/{user_id}/quick-setup", response_model=UserSettingsDB) # Change to POST since it's creation
def quick_setup(user_id: int, payload: QuickSetup, db: SessionDependency):
    try:
        email = get_user_email(db, user_id)
        
        new_settings = UserSettingsDB(
            UserId=user_id,
            Email=email,
            MonthlyIncome=payload.MonthlyIncome,
            SetupMode="quick",
            SetupCompleted=True
        )

        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)
        return new_settings
    
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Setup failed.")

#DETAILED SETUP OPTION
@router.post("/{user_id}/detailed-setup", response_model=UserSettingsDB, status_code=201)
def detailed_setup(user_id: int, payload: UserSettings, db: SessionDependency):
    
    try:
        email = get_user_email(db, user_id)
        new_settings = UserSettingsDB(
            **payload.model_dump(),
            Email = email,
            UserId=user_id,
            SetupMode="detailed",
            SetupCompleted=True
        )

        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)
        
        return new_settings

    except Exception as e:
        db.rollback()
        # If they try to create settings for a user that already has them, 
        # Postgres will throw a UniqueConstraint error (if UserId is unique).
        raise HTTPException(
            status_code=400, 
            detail="Settings already exist for this user or the setup failed."
        )

# change to force all users to one setup apge
@router.post("/{user_id}/setup", response_model=UserSettings)
def user_setup(user_id: int, payload: UserSettings, db: SessionDependency):
    pass



# *** IMPORT EXPENSES CODE ***

# for importing previous expenses and saving to db
@router.put("/{user_id}/save-previous-expenses", response_model=list[PreviousExpense])
def save_previous_expenses(user_id: int, payload: AllPreviousExpenses, db: SessionDependency):
    try:
        # array used for refreshing every row 
        new_rows = []
        for row_data in payload.AllExpenseRows:
            # Convert the data-only model to the Database model and inject the user_id manually
            db_row = PreviousExpenseDB(
                **row_data.model_dump(), 
                UserId=user_id
            )
            db.add(db_row)
            new_rows.append(db_row)

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

# to display all previous expenses with filters using querys (/101/previous-expenses?page=1&year=2026)
@router.get("/{user_id}/display-previous-expenses", response_model=list[PreviousExpenseDB])
def get_previous_expenses(
    user_id: int, 
    db: SessionDependency,
    # Query parameters: 'year' is optional. Page defaults to 1. leave the size to always be 6 query is for future proofing
    year: int | None = Query(None, description="Year to filter by (e.g. 2026)"),
    page: int = Query(1, ge=1),
    size: int = Query(6, ge=1, le=100)
):
    statement = select(PreviousExpenseDB).where(PreviousExpenseDB.UserId == user_id)

    # no year query -> display all
    if year:
        statement = statement.where(PreviousExpenseDB.Month.startswith(f"{year}-"))

    # 3. Pagination Logic (Limit and Offset), Offset skips the rows from previous pages
    # Limit restricts the result to 'size' (e.g., 10)
    offset_value = (page - 1) * size
    statement = statement.order_by(col(PreviousExpenseDB.Month).desc()).offset(offset_value).limit(size)

    results = db.exec(statement).all()

    if not results and page == 1:
        raise HTTPException(status_code=404, detail="No expenses found.")

    return results

# delete selected expenses based on display (takes in all the expense ids)
@router.delete("/{user_id}/previous-expenses/delete")
def delete_multiple_expenses(
    user_id: int, 
    payload: DeleteExpensesRequest, 
    db: SessionDependency
):
    if not payload.expenses_ids:
        raise HTTPException(status_code=400, detail="No IDs provided.")

    try:
        # Wrapping in col() tells VS Code these are DB columns
        statement = delete(PreviousExpenseDB).where(
            col(PreviousExpenseDB.id).in_(payload), 
            col(PreviousExpenseDB.UserId) == user_id
        )
        
        result = db.exec(statement)
        db.commit()

        return {
            "success": True, 
            "deleted_count": result.rowcount
        }

    except SQLAlchemyError:
        db.rollback()
        # print(f"Error: {e}") # It's helpful to log the error during development
        raise HTTPException(
            status_code=500, 
            detail="Bulk deletion failed."
        )
