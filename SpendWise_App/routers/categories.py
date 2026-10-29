from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel import col, select, func
from SpendWise_App.utils.utils import update_monthly_totals
from ..models import ExpensesDB, UserDetails, ExpenseItem, CategorySummary, MonthlyCategoryDB, UserExpensesBase
from ..database import SessionDependency
from ..oauth2 import get_current_active_user
from typing import Annotated
from ..utils.general import get_date_filter
from datetime import date

router = APIRouter(prefix="/categories", tags=["Categories"])

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]

CATEGORIES = ["Food", "Transport", "Utilities", "Entertainment", "Shopping", "Healthcare"]

# Returns dated expenses grouped by category, including recurring payments.
@router.get("/", response_model=list[CategorySummary])
def get_expenses_by_category(
    db: SessionDependency,
    current_user: CurrentUser,
    period: str = Query(default="all_time"),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
):
    if period == "custom":
        if from_date is None or to_date is None:
            raise HTTPException(status_code=400, detail="Both from and to dates are required for a custom range.")
        if from_date > to_date:
            raise HTTPException(status_code=400, detail="The from date must be on or before the to date.")
        since = None
    else:
        since = get_date_filter(period)

    # Dated expense records include payments marked recurring. The Basket page
    # separately shows the ongoing monthly plan for those expenses.
    query = select(ExpensesDB).where(ExpensesDB.UserId == current_user.Id)

    if period == "custom":
        query = query.where(
            ExpensesDB.DatePurchased >= from_date,
            ExpensesDB.DatePurchased <= to_date,
        )
    elif since:
        query = query.where(ExpensesDB.DatePurchased >= since)
    query = query.order_by(ExpensesDB.Type)
    expenses = db.exec(query).all()

    category_map: dict[str, CategorySummary] = {}
    for expense in expenses:
        cat = expense.Type
        if cat == "Food & Dining":
            cat = "Food"
        if cat not in category_map:
            category_map[cat] = CategorySummary(category=cat, total=0.0, expenses=[])
        category_map[cat].total = round(category_map[cat].total + expense.AmountSpent, 2)
        category_map[cat].expenses.append(ExpenseItem.model_validate(expense))

    # Sort all expenses within each category by date descending
    for summary in category_map.values():
        summary.expenses.sort(key=lambda e: e.DatePurchased, reverse=True)

    return list(category_map.values())


@router.get("/{category}", response_model=CategorySummary)
def get_single_category(
    category: str,
    db: SessionDependency,
    current_user: CurrentUser,
    period: str = Query(default="all_time")
):
    since = get_date_filter(period)
    query = (
        select(ExpensesDB)
        .where(ExpensesDB.UserId == current_user.Id)
        .where(func.lower(ExpensesDB.Type) == category.lower())
    )

    if since:
        query = query.where(ExpensesDB.DatePurchased >= since)

    expenses = db.exec(query.order_by(col(ExpensesDB.DatePurchased).desc())).all()
    total = round(sum(e.AmountSpent for e in expenses), 2)

    return CategorySummary(
        category=category,
        total=total,
        expenses=[ExpenseItem.model_validate(e) for e in expenses]
    )

# Delete a expense in the even user adds wrongly
@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: SessionDependency, current_user: CurrentUser):
    statement = select(ExpensesDB).where(ExpensesDB.Id == expense_id, ExpensesDB.UserId == current_user.Id)
    db_expense = db.exec(statement).first()
    
    if not db_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    target_date = db_expense.DatePurchased # Store date for summary update
    db.delete(db_expense)
    # Flush the deletion so the aggregate query excludes this expense.
    db.flush()

    # Recalculate and persist the deletion and updated summary together.
    update_monthly_totals(db, current_user.Id, target_date, ExpensesDB)
    db.commit()

    return None

@router.patch("/{id}", response_model=ExpensesDB)
def update_expense(id: int, data: UserExpensesBase, db: SessionDependency, current_user: CurrentUser):
    item = db.get(ExpensesDB, id)
    if not item or item.UserId != current_user.Id:
        raise HTTPException(status_code=404)

    old_date = item.DatePurchased
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    db.add(item)

    # A date edit affects both the month the expense left and the month it entered.
    update_monthly_totals(db, current_user.Id, old_date, ExpensesDB)
    if (item.DatePurchased.year, item.DatePurchased.month) != (old_date.year, old_date.month):
        update_monthly_totals(db, current_user.Id, item.DatePurchased, ExpensesDB)

    db.commit()
    db.refresh(item)
    return item
