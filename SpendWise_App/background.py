import asyncio
from datetime import datetime
import logging
from sqlmodel import Session, select

from .utils.alert import create_db_alert
from .database import engine
from .models import UserDetails, UserSettingsDB, UserBudgetDB, MonthlyCategoryDB, AlertDB

logger = logging.getLogger(__name__)

CATEGORIES = ["Food", "Transport", "Utilities", "Entertainment", "Shopping", "Healthcare", "Other"]


def _has_recent_alert(session: Session, user_id: int, title: str) -> bool:
    """
    Returns True if an alert with this exact title already exists for
    this user. Prevents duplicate alerts from firing on back-to-back expense
    additions while the alert remains active.
    """
    existing = session.exec(
        select(AlertDB).where(
            AlertDB.UserId == user_id,
            AlertDB.Title == title,
        )
    ).first()
    return existing is not None


async def budget_warning_alert_generation(user_id: int):
    """
    Checks total and per-category budget thresholds after a new expense is added.
    Called via FastAPI BackgroundTasks from expenses.py.
    """
    current_month = datetime.now().strftime("%Y-%m")

    with Session(engine) as session:
        settings = session.exec(
            select(UserSettingsDB).where(UserSettingsDB.UserId == user_id)
        ).first()

        # Guard: respect the user's alert toggle
        if not settings or not settings.BudgetThresholdAlerts:
            return

        budget = session.exec(
            select(UserBudgetDB).where(UserBudgetDB.UserId == user_id)
        ).first()

        spending = session.exec(
            select(MonthlyCategoryDB)
            .where(MonthlyCategoryDB.UserId == user_id)
            .where(MonthlyCategoryDB.Month == current_month)
        ).first()

        if not budget or not spending:
            return

        threshold_ratio = (settings.BudgetThreshold or 80) / 100

        # ── PART A: Total budget check ──
        total_spent = sum(getattr(spending, cat, 0) or 0 for cat in CATEGORIES)

        if budget.TotalBudget > 0:
            total_usage = total_spent / budget.TotalBudget
            if total_usage >= threshold_ratio:
                title = "Overall Budget Warning ⚠️"
                # Only create if no identical unread alert exists yet
                if not _has_recent_alert(session, user_id, title):
                    await create_db_alert(
                        user_id=user_id,
                        title=title,
                        message=(
                            f"You've spent ${total_spent:,.2f}, reaching "
                            f"{total_usage:.0%} of your ${budget.TotalBudget:,.0f} "
                            "total monthly budget."
                        ),
                        alert_type="budget",
                    )

        # ── PART B: Per-category checks ──
        for cat in CATEGORIES:
            cat_spent = getattr(spending, cat, 0) or 0
            cat_limit = getattr(budget, cat, 0) or 0

            if cat_limit <= 0:
                continue

            cat_usage = cat_spent / cat_limit
            if cat_usage >= threshold_ratio:
                title = f"{cat} Budget Alert 🚨"
                if not _has_recent_alert(session, user_id, title):
                    await create_db_alert(
                        user_id=user_id,
                        title=title,
                        message=(
                            f"Your {cat} spending is ${cat_spent:,.2f}, which is "
                            f"{cat_usage:.0%} of your ${cat_limit:,.0f} category limit."
                        ),
                        alert_type="warning",
                    )


async def large_expense_anomaly_alert(user_id: int, amount_spent: float, item_name: str):
    """
    Fires when a single purchase exceeds the user's anomaly threshold percentage
    of their monthly budget (or income as fallback).
    """
    with Session(engine) as session:
        settings = session.exec(
            select(UserSettingsDB).where(UserSettingsDB.UserId == user_id)
        ).first()
        budget = session.exec(
            select(UserBudgetDB).where(UserBudgetDB.UserId == user_id)
        ).first()

        if not settings or not settings.AnomalyAlerts:
            return

        # Prefer TotalBudget, fall back to MonthlyIncome
        spending_power = 0.0
        if budget and budget.TotalBudget > 0:
            spending_power = budget.TotalBudget
        elif settings.MonthlyIncome > 0:
            spending_power = settings.MonthlyIncome

        if spending_power <= 0:
            return

        user_threshold_pct = settings.AnomalyThreshold if settings.AnomalyThreshold > 0 else 1
        anomaly_limit = spending_power * (user_threshold_pct / 100)

        if amount_spent >= anomaly_limit:
            percentage_eaten = (amount_spent / spending_power) * 100
            context = "monthly budget" if (budget and budget.TotalBudget > 0) else "monthly income"

            await create_db_alert(
                user_id=user_id,
                title="Large Expense Detected 💳",
                message=(
                    f"You spent ${amount_spent:,.2f} on '{item_name}'. "
                    f"That's {percentage_eaten:.0f}% of your {context} in one transaction!"
                ),
                alert_type="warning",
            )
