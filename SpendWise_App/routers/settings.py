from calendar import Month
from math import e
from re import M
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter, Query
from sqlmodel import Session, select
from ..oauth2 import get_current_active_user
from ..models import *
from ..database import *


router = APIRouter(
    prefix="/settings",
    tags=['Settings']
)

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]


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

# change to force all users to one setup apge
@router.post("/setup", response_model=UserSettingsDB)
def user_setup(current_user: CurrentUser, payload: UserSettings, db: SessionDependency):
    
    user_id = current_user.Id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    
    settings = db.exec(select(UserSettingsDB).where(UserSettingsDB.UserId == user_id)).first()

    if not settings:
        settings = create_default_settings(db, user_id)

    data = payload.model_dump()

    for key, value in data.items():
        setattr(settings, key, value)

    settings.SetupMode = "detailed"
    settings.SetupCompleted = True

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings

# gets the settings of the user to be displaayed
@router.get("/", response_model=UserSettingsDB)
def get_user_settings(current_user: CurrentUser, db: SessionDependency):

    user_id = current_user.Id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    settings = db.exec(select(UserSettingsDB).where(UserSettingsDB.UserId == user_id)).first()
    if not settings:
        settings = create_default_settings(db, user_id)
    return settings

# to update (save) a user’s settings in the database.
@router.put("/update", response_model=UserSettingsDB)
def save_settings(current_user: CurrentUser,payload: UserSettingsUpdate,db: SessionDependency):
    
    user_id = current_user.Id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    settings = db.exec(select(UserSettingsDB).where(UserSettingsDB.UserId == user_id)).first()

    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    try:
        ALLOWED_SETTINGS_FIELDS = {
        "MonthlyIncome",
        "HouseholdSize",
        "TransportationTypes",

        "PriceIncreaseAlerts",
        "BudgetThresholdAlerts",
        "PaceAlerts", 
        "AnomalyAlerts",
        "InflationBeaterAlerts",

        "PriceThreshold",
        "BudgetThreshold",
        "AnomalyThreshold",}
        data = payload.model_dump(exclude_unset=True)

        for key, value in data.items():
            if key in ALLOWED_SETTINGS_FIELDS:
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





