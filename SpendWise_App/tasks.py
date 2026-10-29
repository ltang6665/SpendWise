import asyncio
import calendar
import logging
from sqlmodel import Session, delete, extract, func, select

from .utils.alert import create_db_alert
from .utils.utils import calculate_pir_for_user
from .database import engine
from datetime import date, datetime, timedelta, timezone
from .models import (
    AlertDB, BasketDB, ExpensesDB, NationalCPIDB,
    UserDetails, UserSettingsDB, UserBudgetDB, MonthlyCategoryDB, UserSuggestionDB,
)

logger = logging.getLogger(__name__)

# Shared across tasks — same map used in build_budget_suggestions
CATEGORY_CPI_MAP: dict[str, list[str]] = {
    "Food":          ["Food & Non-Alcoholic Beverages", "Cooked Food", "Food"],
    "Transport":     ["Transport", "Private Transport"],
    "Utilities":     ["Housing & Utilities", "Utilities", "Electricity & Gas"],
    "Healthcare":    ["Health", "Healthcare", "Medical Products & Services"],
    "Entertainment": ["Recreation & Culture", "Entertainment"],
    "Shopping":      ["Clothing & Footwear", "Household Durables & Services"],
    "Other":         ["Miscellaneous Goods & Services"],
}

# Maps app category names back to user-facing labels for basket items
BASKET_TO_APP_CATEGORY: dict[str, str] = {
    "Food & Dining": "Food",
    "Transport":     "Transport",
    "Utilities":     "Utilities",
    "Entertainment": "Entertainment",
    "Shopping":      "Shopping",
    "Healthcare":    "Healthcare",
    "Other":         "Other",
}


def _has_recent_alert(session: Session, user_id: int, title: str) -> bool:
    """Prevents duplicate alerts with the same title while one remains active."""
    return session.exec(
        select(AlertDB).where(
            AlertDB.UserId == user_id,
            AlertDB.Title == title,
        )
    ).first() is not None


async def cleanup_old_alerts(retention_days: int = 30):
    """Deletes alerts only after they have been stored for `retention_days`."""
    expiration_cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    statement = delete(AlertDB).where(AlertDB.CreatedAt < expiration_cutoff)
    with Session(engine) as session:
        try:
            session.exec(statement)
            session.commit()
            logger.info("Successfully cleaned up old alerts.")
        except Exception as e:
            logger.error(f"Error during alert cleanup: {e}")
            session.rollback()

from .models import UserSuggestionDB

# cleanup old suggestions 
async def cleanup_old_suggestions(months_to_keep: int = 2):
 
    # Calculate a rough cutoff date (e.g., 60 days ago)
    cutoff_date = date.today() - timedelta(days=30 * months_to_keep)
    cutoff_month_str = cutoff_date.strftime("%Y-%m")

    statement = delete(UserSuggestionDB).where(
        UserSuggestionDB.Month < cutoff_month_str
    )
    
    with Session(engine) as session:
        try:
            session.exec(statement)
            session.commit()
            logger.info(f"Successfully cleaned up suggestions older than {cutoff_month_str}.")
        except Exception as e:
            logger.error(f"Error during suggestion cleanup: {e}")
            session.rollback()


async def price_increase_alert():
    """
    Checks whether national CPI inflation for categories in the user's basket
    exceeds their personal PriceThreshold. Uses the shared CATEGORY_CPI_MAP
    to correctly resolve SingStat category names.
    """
    with Session(engine) as session:
        available_users = session.exec(
            select(UserDetails).where(UserDetails.RefreshToken != None)
        ).all()

        latest_month = session.exec(
            select(NationalCPIDB.Month).order_by(NationalCPIDB.Month.desc())
        ).first()

        if not latest_month:
            return

        # Build a flat lookup: SingStat category name → YoY%
        cpi_records = session.exec(
            select(NationalCPIDB).where(
                NationalCPIDB.Month == latest_month,
                NationalCPIDB.YoYChange != None,
            )
        ).all()
        raw_cpi: dict[str, float] = {r.Category: r.YoYChange for r in cpi_records}

        # Resolve our 7 app categories to their best available YoY value
        resolved_cpi: dict[str, float | None] = {}
        for app_cat, singstat_names in CATEGORY_CPI_MAP.items():
            for name in singstat_names:
                if name in raw_cpi:
                    resolved_cpi[app_cat] = raw_cpi[name]
                    break
            else:
                resolved_cpi[app_cat] = None

        for user in available_users:
            settings = session.exec(
                select(UserSettingsDB).where(UserSettingsDB.UserId == user.Id)
            ).first()

            # Respect the user's PriceIncreaseAlerts toggle
            if not settings or not settings.PriceIncreaseAlerts:
                continue

            basket_items = session.exec(
                select(BasketDB).where(BasketDB.UserId == user.Id)
            ).all()

            if not basket_items:
                continue

            # Get the unique app-level categories present in the basket
            app_categories_in_basket: set[str] = set()
            for item in basket_items:
                app_cat = BASKET_TO_APP_CATEGORY.get(item.Type, "Other")
                app_categories_in_basket.add(app_cat)

            for app_cat in app_categories_in_basket:
                yoy = resolved_cpi.get(app_cat)
                if yoy is None:
                    continue

                if yoy >= settings.PriceThreshold:
                    title = f"Market Price Surge: {app_cat} 📈"
                    if not _has_recent_alert(session, user.Id, title):
                        asyncio.create_task(
                            create_db_alert(
                                user_id=user.Id,
                                title=title,
                                message=(
                                    f"National prices for {app_cat.lower()} are up {yoy:.1f}% "
                                    f"year-on-year — above your {settings.PriceThreshold}% alert limit. "
                                    "Check your basket for potential savings!"
                                ),
                                alert_type="warning",
                            )
                        )


async def spending_pace_alert():
    """
    Checks whether the user is spending faster than their pro-rated monthly
    budget (preferred) or income (fallback). Respects PaceAlerts toggle and
    deduplicates via unread alert check.
    """
    now = date.today()
    if now.day < 7:
        return

    total_days = calendar.monthrange(now.year, now.month)[1]

    with Session(engine) as session:
        users = session.exec(
            select(UserDetails).where(UserDetails.RefreshToken != None)
        ).all()

        for user in users:
            settings = session.exec(
                select(UserSettingsDB).where(UserSettingsDB.UserId == user.Id)
            ).first()

            # FIX: use PaceAlerts, not BudgetThresholdAlerts
            if not settings or not settings.PaceAlerts:
                continue

            # Determine the monthly baseline: prefer TotalBudget, fall back to income
            budget = session.exec(
                select(UserBudgetDB).where(UserBudgetDB.UserId == user.Id)
            ).first()

            monthly_baseline = 0.0
            baseline_label = ""
            if budget and budget.TotalBudget > 0:
                monthly_baseline = float(budget.TotalBudget)
                baseline_label = "monthly budget"
            elif settings.MonthlyIncome > 0:
                monthly_baseline = float(settings.MonthlyIncome)
                baseline_label = "monthly income"
            else:
                continue  # No baseline at all — skip this user

            history_spent = session.exec(
                select(func.sum(ExpensesDB.AmountSpent)).where(
                    ExpensesDB.UserId == user.Id,
                    extract("month", ExpensesDB.DatePurchased) == now.month,
                    extract("year", ExpensesDB.DatePurchased) == now.year,
                )
            ).one() or 0.0

            # Basket entries are monthly plans, not payments already made.
            total_spent = history_spent

            prorated_baseline = monthly_baseline * (now.day / total_days)

            if total_spent > prorated_baseline:
                overage = total_spent - prorated_baseline
                title = "Spending Too Fast 🏃💨"
                # Deduplication: only alert if no unread pace warning exists
                if not _has_recent_alert(session, user.Id, title):
                    asyncio.create_task(
                        create_db_alert(
                            user_id=user.Id,
                            title=title,
                            message=(
                                f"You've spent ${total_spent:,.0f} so far this month. "
                                f"To be on pace with your {baseline_label}, "
                                f"you should be at ${prorated_baseline:,.0f} by day {now.day}. "
                                f"You're ${overage:,.0f} ahead of pace."
                            ),
                            alert_type="warning",
                        )
                    )


async def inflation_beater_insight():
    """
    Compares each user's Personal Inflation Rate (PIR) against the national
    CPI. Sends a congratulatory alert if beating inflation, or a lifestyle
    creep warning if significantly above it. Respects InflationBeaterAlerts toggle.
    """
    now = date.today()

    with Session(engine) as session:
        nat_rec = session.exec(
            select(NationalCPIDB)
            .where(NationalCPIDB.Category == "All Items", NationalCPIDB.YoYChange != None)
            .order_by(NationalCPIDB.Month.desc())
        ).first()

        if not nat_rec:
            return

        national_rate = nat_rec.YoYChange

        users = session.exec(
            select(UserDetails).where(UserDetails.RefreshToken != None)
        ).all()

        for user in users:
            # FIX: actually check the user's InflationBeaterAlerts preference
            settings = session.exec(
                select(UserSettingsDB).where(UserSettingsDB.UserId == user.Id)
            ).first()
            if not settings or not settings.InflationBeaterAlerts:
                continue

            try:
                user_pir = calculate_pir_for_user(user.Id, now, session)

                if user_pir < (national_rate - 1.0):
                    title = "You're Beating Inflation! 🏆"
                    msg = (
                        f"Singapore's inflation is at {national_rate:.1f}%, but your "
                        f"Personal Inflation Rate is only {user_pir:.1f}%. "
                        "Great job adapting your spending habits!"
                    )
                    alert_type = "success"

                elif user_pir > (national_rate + 2.0):
                    title = "Lifestyle Creep Warning 📈"
                    msg = (
                        f"Your cost of living (PIR: {user_pir:.1f}%) is rising faster than "
                        f"the national average ({national_rate:.1f}%). "
                        "Check your recurring basket items for categories that keep creeping up."
                    )
                    alert_type = "info"

                else:
                    continue

                if not _has_recent_alert(session, user.Id, title):
                    asyncio.create_task(
                        create_db_alert(user.Id, title, msg, alert_type)
                    )

            except Exception as e:
                logger.error(f"Failed to generate PIR insight for user {user.Id}: {e}")

async def daily_goal_reminder():
    """
    Finds all accepted budget goals for the current month and sends a daily 
    encouragement alert to help the user stay on track.
    """
    current_month = date.today().strftime("%Y-%m")

    with Session(engine) as session:
        # Get all actively accepted suggestions for the current month
        active_goals = session.exec(
            select(UserSuggestionDB).where(
                UserSuggestionDB.Month == current_month,
                UserSuggestionDB.IsAccepted == True
            )
        ).all()

        for goal in active_goals:
            title = f"Daily Goal Reminder: {goal.Category} 🎯"
            msg = (
                f"Don't forget your commitment to: **{goal.Title}**! "
                "Keep up the good habits today to protect your budget."
            )
            
            # Using your existing deduplicator logic. 
            # If they haven't read yesterday's reminder, it won't spam them with a new one.
            if not _has_recent_alert(session, goal.UserId, title):
                asyncio.create_task(
                    create_db_alert(
                        user_id=goal.UserId,
                        title=title,
                        message=msg,
                        alert_type="info"
                    )
            )
