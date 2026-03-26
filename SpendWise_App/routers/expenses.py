# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlmodel import select
# from ..models import UserExpenses, ExpensesDB, UserDetails
# from ..database import SessionDependency
# from ..oauth2 import get_current_active_user
# from typing import Annotated

# router = APIRouter(prefix="/expenses", tags=["Expenses"])

# CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]

# @router.post("/", response_model=ExpensesDB, status_code=status.HTTP_201_CREATED)
# def add_expense(
#     expense: UserExpenses,
#     db: SessionDependency,
#     current_user: CurrentUser
# ):
#     db_expense = ExpensesDB(**expense.model_dump(), user_id=current_user.id)
#     db.add(db_expense)
#     db.commit()
#     db.refresh(db_expense)
#     return db_expense

# @router.get("/", response_model=list[ExpensesDB])
# def get_expenses(
#     db: SessionDependency,
#     current_user: CurrentUser
# ):
#     expenses = db.exec(
#         select(ExpensesDB).where(ExpensesDB.user_id == current_user.id)
#     ).all()
#     return expenses

# @router.delete("/{expense_id}", status_code=status.HTTP_200_OK)
# def delete_expense(
#     expense_id: int,
#     db: SessionDependency,
#     current_user: CurrentUser
# ):
#     expense = db.get(ExpensesDB, expense_id)
#     if not expense or expense.user_id != current_user.id:
#         raise HTTPException(status_code=404, detail="Expense not found")
#     db.delete(expense)
#     db.commit()
#     return {"success": True}
