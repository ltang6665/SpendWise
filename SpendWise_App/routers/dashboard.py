from typing import Annotated
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import col, desc, extract, func, select
from ..utils.utils import get_monthly_category_totals
from ..utils.calculations import (
    calculate_realtime_savings, 
    calculate_shares, 
    calculate_trend_forecast, 
    compute_tornqvist_pir
)
from ..models import *
from ..database import SessionDependency
from ..oauth2 import get_current_active_user

router = APIRouter(
    prefix="/dashboard", 
    tags=["dashboard"]
)

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]

@router.get("/summary")
def get_dashboard_summary(current_user: CurrentUser, session: SessionDependency):
    """Calculates the data for the blue MonthlySummaryCard."""
    now = date.today()
    import calendar
    month_str = now.strftime("%Y-%m")

    monthly_cat = session.exec(
        select(MonthlyCategoryDB).where(
            MonthlyCategoryDB.UserId == current_user.Id,
            MonthlyCategoryDB.Month == month_str
        )
    ).first()
    
    total_spent = 0.0
    if monthly_cat:
        total_spent = (
            monthly_cat.Food + monthly_cat.Transport + monthly_cat.Utilities + 
            monthly_cat.Entertainment + monthly_cat.Shopping + monthly_cat.Healthcare + 
            getattr(monthly_cat, 'Other', 0.0)
        )

    settings = session.exec(select(UserSettingsDB).where(UserSettingsDB.UserId == current_user.Id)).first()
    budget = session.exec(select(UserBudgetDB).where(UserBudgetDB.UserId == current_user.Id)).first()
    monthly_recurring = session.exec(
        select(func.coalesce(func.sum(BasketDB.AmountSpent), 0)).where(
            BasketDB.UserId == current_user.Id
        )
    ).one()
    
    monthly_income = settings.MonthlyIncome if settings else 0
    total_budget = budget.TotalBudget if budget else 0
    monthly_recurring = float(monthly_recurring or 0)
    total_committed = round(total_spent + monthly_recurring, 2)

    savings = calculate_realtime_savings(monthly_income, total_committed, reference_date=now)
    budget_percent = round(total_committed / total_budget * 100, 1) if total_budget else 0

    return {
        "total_spent": round(total_spent, 2),
        "total_committed": total_committed,
        "total_budget": total_budget,
        "monthly_income": monthly_income,
        "monthly_recurring": monthly_recurring,
        "savings": savings,
        "budget_percent": budget_percent,
    }

@router.get("/inflation-rates", status_code=status.HTTP_200_OK)
def inflation_rate_display(db: SessionDependency, current_user: CurrentUser):
    """
    Main route for the Inflation Insights Card.
    Uses Törnqvist Index for the Personal Inflation Rate.
    """
    if not current_user.Id:
        raise HTTPException(status_code=404, detail="User does not exist.")

    # 1. Get recent months available in National CPI data
    recent_months = db.exec(
        select(NationalCPIDB.Month).distinct().order_by(NationalCPIDB.Month.desc()).limit(3)
    ).all()
    recent_months.sort()

    category_mapping = {
        "Food": "Food", "Transport": "Transport", "Utilities": "Utilities & Other Fuels",
        "Entertainment": "Recreation & Cultural Goods", "Shopping": "Clothing & Footwear", "Healthcare": "Health"
    }

    labels, user_trend, national_trend = [], [], []
    personal_inflation_available = False

    for month_str in recent_months:
        target_date = datetime.strptime(month_str, "%Y-%m").date()
        labels.append(target_date.strftime("%b"))

        # --- TÖRNQVIST PERSONAL INFLATION CALCULATION ---
        current_totals = get_monthly_category_totals(db, current_user.Id, target_date)
        current_shares = calculate_shares(current_totals)
        
        # Look for baseline from 1 year ago
        base_date = target_date.replace(year=target_date.year - 1)
        base_totals = get_monthly_category_totals(db, current_user.Id, base_date)
        
        # Fallback to earliest record if no data from 1 year ago exists
        if not any(base_totals.values()):
            earliest = db.exec(select(MonthlyCategoryDB).where(MonthlyCategoryDB.UserId == current_user.Id).order_by(MonthlyCategoryDB.Month.asc())).first()
            if earliest:
                base_totals = {"Food": earliest.Food, "Transport": earliest.Transport, "Utilities": earliest.Utilities, "Entertainment": earliest.Entertainment, "Shopping": earliest.Shopping, "Healthcare": earliest.Healthcare}

        base_shares = calculate_shares(base_totals)

        # Get Price Ratios for the specific month
        price_ratios = {}
        for app_cat, singstat_cat in category_mapping.items():
            cpi_record = db.exec(select(NationalCPIDB).where(NationalCPIDB.Month == month_str, NationalCPIDB.Category == singstat_cat)).first()
            price_ratios[app_cat] = 1 + (cpi_record.YoYChange / 100) if (cpi_record and cpi_record.YoYChange) else 1.0

        personal_inflation_available = bool(base_shares and current_shares)
        if personal_inflation_available:
            month_pir = compute_tornqvist_pir(base_shares, current_shares, price_ratios)
        else:
            month_pir = 0.0
        user_trend.append(round(month_pir, 2))

        # --- NATIONAL CPI DATA ---
        nat_rec = db.exec(select(NationalCPIDB).where(NationalCPIDB.Category == "All Items", NationalCPIDB.Month == month_str)).first()
        national_trend.append(round(nat_rec.YoYChange, 2) if (nat_rec and nat_rec.YoYChange) else 0.0)

    return {
        "personal_inflation_rate": user_trend[-1] if user_trend else 0.0,
        "personal_inflation_available": personal_inflation_available,
        "national_inflation_rate": national_trend[-1] if national_trend else 0.0,
        "trend_labels": labels, "user_trend": user_trend, "national_trend": national_trend 
    }

@router.get("/spending-breakdown")
def get_spending_breakdown(current_user: CurrentUser, session: SessionDependency):
    """Data for the Pie Chart."""
    now = date.today()
    month_str = now.strftime("%Y-%m")
    labels = ['Food & Dining', 'Transport', 'Utilities', 'Entertainment', 'Shopping', 'Healthcare', 'Other']
    
    monthly_cat = session.exec(select(MonthlyCategoryDB).where(MonthlyCategoryDB.UserId == current_user.Id, MonthlyCategoryDB.Month == month_str)).first()
    
    category_totals = {
        "Food & Dining": float(monthly_cat.Food) if monthly_cat else 0.0,
        "Transport": float(monthly_cat.Transport) if monthly_cat else 0.0,
        "Utilities": float(monthly_cat.Utilities) if monthly_cat else 0.0,
        "Entertainment": float(monthly_cat.Entertainment) if monthly_cat else 0.0,
        "Shopping": float(monthly_cat.Shopping) if monthly_cat else 0.0,
        "Healthcare": float(monthly_cat.Healthcare) if monthly_cat else 0.0,
        "Other": float(getattr(monthly_cat, 'Other', 0.0)) if monthly_cat else 0.0,
    }

    recurring_totals = session.exec(
        select(BasketDB.Type, func.sum(BasketDB.AmountSpent))
        .where(BasketDB.UserId == current_user.Id)
        .group_by(BasketDB.Type)
    ).all()
    for category, amount in recurring_totals:
        chart_category = "Food & Dining" if category in {"Food", "Food & Dining"} else category
        if chart_category in category_totals:
            category_totals[chart_category] += float(amount or 0.0)

    data = [category_totals[label] for label in labels]

    top_items = session.exec(select(ExpensesDB).where(ExpensesDB.UserId == current_user.Id, extract("month", ExpensesDB.DatePurchased) == now.month, extract("year", ExpensesDB.DatePurchased) == now.year).order_by(desc(ExpensesDB.AmountSpent)).limit(5)).all()

    return {
        "labels": labels, "data": [round(d, 2) for d in data],
        "top_items": [{"name": i.ItemName, "amount": i.AmountSpent, "type": i.Type} for i in top_items]
    }

@router.get("/forecast")
def get_spending_forecast(db: SessionDependency, current_user: CurrentUser):
    """Data for the Forecast Line Chart."""
    monthly_totals = {}
    monthly_cats = db.exec(select(MonthlyCategoryDB).where(MonthlyCategoryDB.UserId == current_user.Id)).all()
    
    for cat in monthly_cats:
        total = cat.Food + cat.Transport + cat.Utilities + cat.Entertainment + cat.Shopping + cat.Healthcare + getattr(cat, 'Other', 0.0)
        monthly_totals[cat.Month] = total

    sorted_months = sorted(monthly_totals.keys())[-6:]
    historical = [{"month": datetime.strptime(m, "%Y-%m").strftime("%b %y"), "amount": round(monthly_totals[m], 2)} for m in sorted_months]
    amounts = [d["amount"] for d in historical]

    if len(amounts) < 3:
        return {"status": "insufficient", "historical": historical, "forecast": []}

    predicted = calculate_trend_forecast(amounts, months_ahead=3)
    last_date = datetime.strptime(sorted_months[-1], "%Y-%m").date()
    forecast = [
        {
            "month": (last_date.replace(day=1) + timedelta(days=31 * (i + 1))).strftime("%b %y"),
            "amount": amt,
        }
        for i, amt in enumerate(predicted)
    ]

    return {"status": "success", "historical": historical, "forecast": forecast}

@router.get("/cpi-categories")
def get_cpi_categories(db: SessionDependency, current_user: CurrentUser):
    return db.exec(select(NationalCPIDB.Category).distinct().order_by(NationalCPIDB.Category.asc())).all()

@router.get("/cpi-data")
def get_cpi_data(db: SessionDependency, current_user: CurrentUser, categories: list[str] = Query(default=[])):
    if not categories: return []
    records = db.exec(select(NationalCPIDB).where(NationalCPIDB.Category.in_(categories[:5])).order_by(NationalCPIDB.Month.asc())).all()
    
    from collections import defaultdict
    month_map = defaultdict(dict)
    for r in records: month_map[r.Month][r.Category] = round(r.IndexValue, 3)
    
    return [{"month": m, **{cat: month_map[m].get(cat) for cat in categories}} for m in sorted(month_map.keys())]
