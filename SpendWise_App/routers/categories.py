from fastapi import APIRouter, Depends, Query
from sqlmodel import select, func
from ..models import ExpensesDB, UserDetails
from ..database import SessionDependency
from ..oauth2 import get_current_active_user
from typing import Annotated
from ..utils import get_date_filter
from ..schema import ExpenseItem, CategorySummary

router = APIRouter(prefix="/categories", tags=["Categories"])

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]


@router.get("/", response_model=list[CategorySummary])
def get_expenses_by_category(
    db: SessionDependency,
    current_user: CurrentUser,
    period: str = Query(default="all_time")
):
    since = get_date_filter(period)
    query = select(ExpensesDB).where(ExpensesDB.user_id == current_user.id)

    if since:
        query = query.where(ExpensesDB.DatePurchased >= since)

    query = query.order_by(ExpensesDB.type, ExpensesDB.DatePurchased.desc())
    expenses = db.exec(query).all()

    category_map: dict[str, CategorySummary] = {}
    for expense in expenses:
        cat = expense.type
        if cat not in category_map:
            category_map[cat] = CategorySummary(category=cat, total=0.0, expenses=[])
        category_map[cat].total = round(category_map[cat].total + expense.AmountSpent, 2)
        category_map[cat].expenses.append(ExpenseItem.model_validate(expense))

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
        .where(ExpensesDB.user_id == current_user.id)
        .where(func.lower(ExpensesDB.type) == category.lower())
    )

    if since:
        query = query.where(ExpensesDB.DatePurchased >= since)

    expenses = db.exec(query.order_by(ExpensesDB.DatePurchased.desc())).all()
    total = round(sum(e.AmountSpent for e in expenses), 2)

    return CategorySummary(
        category=category,
        total=total,
        expenses=[ExpenseItem.model_validate(e) for e in expenses]
    )