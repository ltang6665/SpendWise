# code for utility functions 
    # hasing of pw
    # verification of pw
# so that imports and code is not repeated in multiple files/main file 

import re
from typing import Any, Type, Union
from fastapi import HTTPException
from sqlmodel import SQLModel, Session, extract, func, select
from .calculations import calculate_pir, calculate_shares
from ..models import BasketCategoryDB, BasketDB, ExpensesDB, MonthlyCategoryDB, UserBudgetDB
from datetime import date, timedelta


def update_monthly_totals(db: Session, user_id: int, target_date: date | None, source_model: Any):
    config = {
        BasketDB: {"summary_table": BasketCategoryDB, "use_date": False},
        ExpensesDB: {"summary_table": MonthlyCategoryDB, "use_date": True}
    }
    
    cfg = config[source_model]
    SummaryTable = cfg["summary_table"]

    # 1. Build Aggregate Query
    # We sum up all expenses grouped by their "Type" (e.g., 'Food & Dining')
    query = select(source_model.Type, func.sum(source_model.AmountSpent)).where(source_model.UserId == user_id)

    if cfg["use_date"] and target_date:
        start = target_date.replace(day=1)
        # Logic to get the first day of the next month
        if start.month == 12:
            next_m = start.replace(year=start.year + 1, month=1)
        else:
            next_m = start.replace(month=start.month + 1)
        query = query.where(source_model.DatePurchased >= start, source_model.DatePurchased < next_m)

    # 2. Execute and Map results
    results = db.exec(query.group_by(source_model.Type)).all()
    
    # FIX: Mapping dictionary to convert Frontend Names to DB Column Names
    # This ensures "Food & Dining" spending goes into the "Food" column
    # FIX: Map both string variations to the correct TitleCase database column
    name_map = {
        "Food & Dining": "Food",
        "Food": "Food",
        "Transport": "Transport",
        "Utilities": "Utilities",
        "Entertainment": "Entertainment",
        "Shopping": "Shopping",
        "Healthcare": "Healthcare",
        "Other": "Other"
    } 

    # Initialize all columns to 0.0 first
    normalized_totals = {col: 0.0 for col in name_map.values()}
 
    # Fill the dictionary with actual summed values from the query
    for cat_name, amt in results:
        db_column = name_map.get(cat_name, "Other")
        normalized_totals[db_column] += float(amt) if amt else 0.0

    # 3. Upsert Summary Record
    summary_stmt = select(SummaryTable).where(SummaryTable.UserId == user_id)
    month_str = target_date.strftime("%Y-%m") if (target_date and cfg["use_date"]) else None
    
    if month_str:
        summary_stmt = summary_stmt.where(SummaryTable.Month == month_str)

    record = db.exec(summary_stmt).first()

    if not record:
        init_data = {"UserId": user_id}
        if month_str:
            init_data["Month"] = month_str
        record = SummaryTable(**init_data)
        db.add(record)
    
    # 4. Update Category Columns
    # We iterate through our 7 core fields and set their new values
    for field, value in normalized_totals.items():
        setattr(record, field, value)

    # We use db.add() to ensure the record is tracked, but we do NOT commit.
    # The calling router function will handle the commit for the whole transaction.
    db.add(record)
    
def calculate_pir_for_user(user_id: int, now: date, session: Session) -> float:
    """
    Builds the items list for calculate_pir() by comparing:
      - base period    = 2 months ago (P0)
      - current period = last month   (Pt)
    Weight = how much user spent on that category in the base period.
    """
    _last_day_of_last_month  = now.replace(day=1) - timedelta(days=1)
    current_month = _last_day_of_last_month.replace(day=1) # 1 month ago

    _last_day_of_two_months_ago = current_month - timedelta(days=1)
    base_month  = _last_day_of_two_months_ago.replace(day=1) # 2 months ago

    def fetch_category_totals(year: int, month: int) -> dict[str, float]:
        expenses = session.exec(
            select(ExpensesDB).where(
                ExpensesDB.UserId == user_id,
                extract("month", ExpensesDB.DatePurchased) == month,
                extract("year",  ExpensesDB.DatePurchased) == year,
            )
        ).all()
        totals: dict[str, float] = {}
        for e in expenses:
            totals[e.Type] = totals.get(e.Type, 0) + e.AmountSpent
        return totals

    base_totals    = fetch_category_totals(base_month.year,    base_month.month)
    current_totals = fetch_category_totals(current_month.year, current_month.month)

    # Only include categories that exist in BOTH periods
    shared_categories = set(base_totals.keys()) & set(current_totals.keys())
    if not shared_categories:
        return 0.0

    items = [
        {
            "name":          cat,
            "base_price":    base_totals[cat],
            "current_price": current_totals[cat],
            "weight":        base_totals[cat],  # base-period spending = Laspeyres weight
        }
        for cat in shared_categories
    ]

    try:
        return calculate_pir(items)
    except ValueError:
        return 0.0


def get_monthly_category_totals(db: Session, user_id: int, target_date: date) -> dict[str, float]:
    # 1. Convert the date into your standard YYYY-MM string
    month_str = target_date.strftime("%Y-%m")
    
    # 2. Fetch the pre-calculated summary row
    monthly_record = db.exec(
        select(MonthlyCategoryDB)
        .where(MonthlyCategoryDB.UserId == user_id)
        .where(MonthlyCategoryDB.Month == month_str)
    ).first()
    
    # 3. Handle the case where the user has no expenses for this month yet
    if not monthly_record:
        return {
            "Food": 0.0, "Transport": 0.0, "Utilities": 0.0, 
            "Entertainment": 0.0, "Shopping": 0.0, "Healthcare": 0.0, "Other": 0.0
        }

    # 4. Return as a dictionary (note: cast to float for precision)
    return {
        "Food": float(monthly_record.Food),
        "Transport": float(monthly_record.Transport),
        "Utilities": float(monthly_record.Utilities),
        "Entertainment": float(monthly_record.Entertainment),
        "Shopping": float(monthly_record.Shopping),
        "Healthcare": float(monthly_record.Healthcare),
        "Other": float(monthly_record.Other)
    }

# Fetches the user's budget row, creating a default (AutoBudget=True) if none exists.
def get_or_create_budget(user_id: int, session: Session) -> UserBudgetDB:
    # from SpendWise_App.models import UserBudgetDB  # local to avoid circular import

    budget = session.exec(
        select(UserBudgetDB).where(UserBudgetDB.UserId == user_id)
    ).first()

    if not budget:
        budget = UserBudgetDB(
            UserId=user_id,
            AutoBudget=True,
            TotalBudget=0,
            Food=0, Transport=0, Utilities=0,
            Entertainment=0, Shopping=0, Healthcare=0, Other=0
        )
        session.add(budget)
        session.commit()
        session.refresh(budget)

    return budget






