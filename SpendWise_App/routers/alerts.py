from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from ..database import SessionDependency
from ..models import AlertDB, UserDetails
from ..oauth2 import get_current_active_user
from typing import Annotated


router = APIRouter(
    prefix="/alerts", 
    tags=["alerts"]
    )

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]

# gets all the alerts for the user 
@router.get("/", response_model=list[AlertDB])
def get_alerts(current_user: CurrentUser, db: SessionDependency):

    user_id = current_user.Id
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    return db.exec(
        select(AlertDB)
        .where(AlertDB.UserId == current_user.Id)
        .order_by(AlertDB.CreatedAt.desc())
    ).all()

# deletes an alert after the user marks it as read
@router.put("/{alert_id}/read")
def mark_alert_as_read(alert_id: int,current_user: CurrentUser,db: SessionDependency):
    alert = db.get(AlertDB, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.UserId != current_user.Id:
        raise HTTPException(status_code=403, detail="Not allowed to modify this alert")

    db.delete(alert)
    db.commit()
    return {"detail": "Alert marked as read and deleted"}







