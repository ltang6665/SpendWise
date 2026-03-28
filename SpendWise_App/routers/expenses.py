from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, func
from ..models import UserExpenses, ExpensesDB, UserDetails
from ..database import SessionDependency
from ..oauth2 import get_current_active_user
from typing import Annotated
from datetime import date, timedelta

router = APIRouter(prefix="/expenses", tags=["Expenses"])

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]

@router.post("/", response_model=ExpensesDB, status_code=status.HTTP_201_CREATED)
def add_expense(
    expense: UserExpenses,
    db: SessionDependency,
    current_user: CurrentUser
):
    db_expense = ExpensesDB(**expense.model_dump(), user_id=current_user.id)
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense
