from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlmodel import Session, select, func
from ..background import budget_warning_alert_generation, large_expense_anomaly_alert
from ..utils.utils import update_monthly_totals
from ..models import BasketDB, MonthlyCategoryDB, UserExpenses, ExpensesDB, UserDetails, UserExpensesBase
from ..database import SessionDependency
from ..oauth2 import get_current_active_user
from typing import Annotated, Union


router = APIRouter(prefix="/expenses", tags=["Expenses"])

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]




# add expenses for any type to be saved in the db
@router.post("/", response_model=Union[UserExpenses,UserExpensesBase], status_code=status.HTTP_201_CREATED)
def add_expense(expense: UserExpenses, db: SessionDependency, current_user: CurrentUser, background_tasks: BackgroundTasks):
    if current_user.Id is None:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    created_item = None

    if expense.Recurring:
        # PATH A: Save to Both (Recurring items)
        created_item = BasketDB(
            Type=expense.Type,
            ItemName=expense.ItemName,
            AmountSpent=expense.AmountSpent,
            Note=expense.Note,
            UserId=current_user.Id
        )
        db.add(created_item)

        created_item = ExpensesDB(**expense.model_dump(), UserId=current_user.Id)
        db.add(created_item)
        
        # Update the Summary Tables
        update_monthly_totals(db, current_user.Id, expense.DatePurchased, ExpensesDB)
        update_monthly_totals(db, current_user.Id, None, BasketDB)
        
    else:
        # PATH B: Save ONLY to Expenses (One-off items / History)
        created_item = ExpensesDB(**expense.model_dump(), UserId=current_user.Id)
        db.add(created_item)
        
        # Update the Monthly Summary Table
        update_monthly_totals(db, current_user.Id, expense.DatePurchased, ExpensesDB)

    # ONE COMMIT to rule them all
    db.commit()
    db.refresh(created_item)

    # Ensure alerts are checked regardless of the item type
    background_tasks.add_task(budget_warning_alert_generation, current_user.Id)
    background_tasks.add_task(large_expense_anomaly_alert, current_user.Id, expense.AmountSpent, expense.ItemName)

    return created_item


