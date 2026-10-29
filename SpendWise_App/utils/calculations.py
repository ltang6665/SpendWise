# code for the math calc logics 

import math 
from datetime import date, timedelta
import calendar
from sqlmodel import Session, func, select

# 1. REAL-TIME SAVINGS (Pro-rated)
#Formula: Current Savings = (Monthly Income × (Days Passed / Total Days in Month))− Current Total Spending
def calculate_realtime_savings(
    monthly_income: float,
    current_total_spending: float,
    reference_date: date | None = None # optional or nah?
) -> float:

    if reference_date is None:
        reference_date = date.today()

    days_passed = reference_date.day
    total_days_in_month = calendar.monthrange(reference_date.year, reference_date.month)[1]

    prorated_income = monthly_income * (days_passed / total_days_in_month)
    savings = prorated_income - current_total_spending

    return round(savings, 2)




#-------------------------------------------------------------------------------------------------------------------------
# calculate tornqvist pir, all helpers and code 

# Converts absolute spending totals into percentage shares (0.0 to 1.0).
def calculate_shares(totals: dict[str, float]) -> dict[str, float]:
    total_spend = sum(totals.values())
    if total_spend == 0:
        return {}
    return {cat: amt / total_spend for cat, amt in totals.items()}

def compute_tornqvist_pir(base_shares: dict[str, float], current_shares: dict[str, float], price_ratios: dict[str, float]) -> float:
    """
    base_shares: { 'Food': 0.25, ... } (from MonthlyCategoryDB)
    current_shares: { 'Food': 0.30, ... } (from BasketCAtegoryDB)
    price_ratios: { 'Food': 1.03, ... } (from SingStat API)
    """
    log_sum = 0.0
    
    # We iterate over categories present in the price dataset
    for category, ratio in price_ratios.items():
        # Get shares, default to 0 if user didn't spend in that category
        s0 = base_shares.get(category, 0.0)
        st = current_shares.get(category, 0.0)
        
        # Törnqvist logic: Average share * natural log of price change
        if ratio > 0: # Avoid log(0)
            avg_share = (s0 + st) / 2
            log_sum += avg_share * math.log(ratio)
            
    # Convert back from log space to percentage
    pir = (math.exp(log_sum) - 1) * 100
    return round(pir, 2)




# returns users personal inflation rate based on their spending 
def calculate_pir(items: list[dict]) -> float:
    """
    Each item in `items` should be a dict with:
        - 'name'         : str
        - 'base_price'   : float  (P0 - price in base period)
        - 'current_price': float  (Pt - price in current period)
        - 'weight'       : float  (wi - spending weight, e.g. monthly spend on item)

    Returns PIR as a percentage (e.g. 3.5 means 3.5% inflation).
    """
    numerator   = sum(item['current_price'] * item['weight'] for item in items)
    denominator = sum(item['base_price']    * item['weight'] for item in items)

    if denominator == 0:
        raise ValueError("Sum of (base_price × weight) cannot be zero.")

    pir = (numerator / denominator - 1) * 100 # -1 finds the change 
    return round(pir, 4)

def calculate_trend_forecast(historical_amounts: list[float], months_ahead: int = 3) -> list[float]:
    """
    Calculates future spending using Simple Linear Regression (y = mx + b).
    Requires at least 3 data points.
    """
    n = len(historical_amounts)
    if n < 3:
        return []
    
    x_values = list(range(n))
    y_values = historical_amounts
    
    sum_x, sum_y = sum(x_values), sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_x_squared = sum(x**2 for x in x_values)
    
    denominator = (n * sum_x_squared - sum_x**2)
    m = 0 if denominator == 0 else (n * sum_xy - sum_x * sum_y) / denominator
    b = (sum_y - m * sum_x) / n
    
    forecast = []
    for i in range(1, months_ahead + 1):
        future_index = n - 1 + i
        # max(0, ...) prevents the formula from predicting negative spending
        predicted_amount = max(0.0, m * future_index + b) 
        forecast.append(round(predicted_amount, 2))
        
    return forecast


#-------------------------------------------------------------------------------------------------------------------------
# Budget page calculations code 
def compute_budget_data(user_id: int, session: Session) -> dict:
    from SpendWise_App.models import ExpensesDB

    today = date.today()
    first_of_current = today.replace(day=1)
    first_of_3_months_ago = (first_of_current - timedelta(days=3 * 28)).replace(day=1)

    categories = ["Food", "Transport", "Utilities", "Entertainment", "Shopping", "Healthcare", "Other"]

    # Get the 3 month keys we need
    months_needed = set()
    for i in range(1, 4):
        d = (first_of_current - timedelta(days=i * 28)).replace(day=1)
        months_needed.add(d.strftime("%Y-%m"))

    # ── 1. Query ExpensesDB (day-to-day expenses) ──
    expense_records = session.exec(
        select(ExpensesDB).where(
            ExpensesDB.UserId == user_id,
            ExpensesDB.DatePurchased >= first_of_3_months_ago,
            ExpensesDB.DatePurchased < first_of_current
        )
    ).all()

    # Group day-to-day expenses by month and category
    expense_by_month = {}
    for r in expense_records:
        month_key = r.DatePurchased.strftime("%Y-%m")
        if month_key not in expense_by_month:
            expense_by_month[month_key] = {cat: 0.0 for cat in categories}
        expense_type = r.Type
        if expense_type == "Food & Dining":
            expense_type = "Food"
        if expense_type in expense_by_month[month_key]:
            expense_by_month[month_key][expense_type] += r.AmountSpent

    # ── 2. Calculate averages ──
    if not expense_by_month:
        return {
            "auto_total": 0.0,
            "category_avgs": {cat: 0 for cat in categories},
            "category_proportions": {cat: round(1 / len(categories), 4) for cat in categories}
        }

    n = 3
    cat_avgs = {
        cat: round(sum(expense_by_month[m][cat] for m in expense_by_month) / n, 2)
        for cat in categories
    }
    auto_total = round(sum(cat_avgs.values()), 2)

    # ── 4. Proportions ──
    if auto_total > 0:
        proportions = {cat: round(cat_avgs[cat] / auto_total, 4) for cat in categories}
    else:
        proportions = {cat: round(1 / len(categories), 4) for cat in categories}

    return {
        "auto_total": auto_total,
        "category_avgs": cat_avgs,
        "category_proportions": proportions
    }

# Keep as wrappers so nothing else breaks
def compute_auto_budget(user_id: int, session: Session) -> float:
    return compute_budget_data(user_id, session)["auto_total"]

def compute_category_budgets(user_id: int, session: Session) -> dict:
    return compute_budget_data(user_id, session)["category_avgs"]


def build_budget_suggestions(user_id: int, session: Session) -> list[dict]:
    from SpendWise_App.models import MonthlyCategoryDB, UserBudgetDB, NationalCPIDB, UserSettingsDB

    today = date.today()
    month_str = today.strftime("%Y-%m")
    days_elapsed = today.day
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    month_progress = days_elapsed / days_in_month  # e.g. 0.48 on day 15 of 31

    # ── 1. Get current month's spending record ──
    record = session.exec(
        select(MonthlyCategoryDB).where(
            MonthlyCategoryDB.UserId == user_id,
            MonthlyCategoryDB.Month == month_str
        )
    ).first()

    if not record:
        return []

    # ── 2. Get user's budget ──
    budget = session.exec(
        select(UserBudgetDB).where(UserBudgetDB.UserId == user_id)
        .order_by(UserBudgetDB.Id.desc())
    ).first()

    if not budget:
        return []

    # ── 3. Get user's settings (for income-based context) ──
    settings = session.exec(
        select(UserSettingsDB).where(UserSettingsDB.UserId == user_id)
    ).first()
    monthly_income = float(settings.MonthlyIncome) if settings and settings.MonthlyIncome else 0.0

    # ── 4. Fetch latest national CPI YoY data ──
    CATEGORY_CPI_MAP = {
        "Food":          ["Food & Non-Alcoholic Beverages", "Cooked Food", "Food"],
        "Transport":     ["Transport", "Private Transport"],
        "Utilities":     ["Housing & Utilities", "Utilities", "Electricity & Gas"],
        "Healthcare":    ["Health", "Healthcare", "Medical Products & Services"],
        "Entertainment": ["Recreation & Culture", "Entertainment"],
        "Shopping":      ["Clothing & Footwear", "Household Durables & Services"],
        "Other":         ["Miscellaneous Goods & Services"],
    }

    latest_cpi_month = session.exec(
        select(NationalCPIDB.Month).order_by(NationalCPIDB.Month.desc())
    ).first()

    raw_cpi: dict[str, float] = {}
    if latest_cpi_month:
        cpi_records = session.exec(
            select(NationalCPIDB).where(
                NationalCPIDB.Month == latest_cpi_month,
                NationalCPIDB.YoYChange != None
            )
        ).all()
        for cpi in cpi_records:
            raw_cpi[cpi.Category] = cpi.YoYChange

    category_cpi: dict[str, float | None] = {}
    for our_cat, cpi_names in CATEGORY_CPI_MAP.items():
        for cpi_name in cpi_names:
            if cpi_name in raw_cpi:
                category_cpi[our_cat] = raw_cpi[cpi_name]
                break
        else:
            category_cpi[our_cat] = None

    # Singapore average fallback thresholds (used only when budget for that category is 0/unset)
    SG_AVERAGES = {
        "Transport":  150.0,
        "Utilities":  300.0,
        "Healthcare": 200.0,
    }

    def cpi_suffix(cat: str) -> str:
        yoy = category_cpi.get(cat)
        if yoy is None:
            return ""
        if yoy >= 3.0:
            return (
                f" National {cat.lower()} prices are also up {yoy:.1f}% year-on-year — "
                "reducing consumption now will compound your savings."
            )
        if yoy >= 1.0:
            return f" National {cat.lower()} prices have risen {yoy:.1f}% year-on-year — a good time to cut back."
        return ""

    def income_context(amount: float) -> str:
        """Returns an income-percentage string if the user has set their income."""
        if monthly_income <= 0:
            return ""
        pct = (amount / monthly_income) * 100
        return f" That's {pct:.1f}% of your monthly income."

    def pace_warning(spent: float, budget_amt: float) -> str | None:
        """
        Returns a warning string if spending pace will overshoot the monthly budget.
        Only fires if the user hasn't already exceeded (that's handled separately).
        projected = spent / month_progress  →  what you'll spend by end of month at current rate.
        """
        if budget_amt <= 0 or spent >= budget_amt:
            return None
        if month_progress <= 0:
            return None
        projected = spent / month_progress
        if projected > budget_amt:
            projected_overage = projected - budget_amt
            return (
                f"At your current pace you're on track to spend ${projected:,.0f} by month-end, "
                f"which is ${projected_overage:,.0f} over your ${budget_amt:,.0f} budget."
            )
        return None

    suggestions = []
    covered_categories: set[str] = set()

    # ── Helper: build one suggestion dict cleanly ──
    def add_suggestion(title: str, description: str, savings: float, cat: str):
        suggestions.append({
            "title": title,
            "description": description,
            "savings": round(savings, 2),
        })
        covered_categories.add(cat)

    # ── Category configs — drives the loop below ──
    # Each entry: (spent, budget_val, sg_average_fallback, title, advice, cat_key)
    categories_config = [
        {
            "cat": "Food",
            "spent": record.Food,
            "budget": budget.Food,
            "fallback": None,  # Food always uses user budget
            "over_title": "Reduce Food Spending",
            "over_advice": (
                "Singaporeans who cook at home or eat at hawker centres "
                "spend up to 40% less than those who dine at restaurants regularly."
            ),
            "pace_title": "Food Budget Pacing Warning",
            "pace_advice": "Consider switching to hawker centres or meal prepping to keep costs in check.",
        },
        {
            "cat": "Transport",
            "spent": record.Transport,
            "budget": budget.Transport,
            "fallback": SG_AVERAGES["Transport"],
            "over_title": "Switch to Public Transport",
            "over_advice": (
                "Walking more often and taking MRT or buses instead of Grab "
                "can significantly cut transport costs. A monthly transit pass runs around $120."
            ),
            "pace_title": "Transport Budget Pacing Warning",
            "pace_advice": "Try replacing some Grab rides with MRT or bus trips to stay on track.",
        },
        {
            "cat": "Utilities",
            "spent": record.Utilities,
            "budget": budget.Utilities,
            "fallback": SG_AVERAGES["Utilities"],
            "over_title": "Reduce Utility Usage",
            "over_advice": (
                "The Singapore average household utility bill is $140–300/month. "
                "Simple habits — turning off lights, reducing water usage, "
                "setting aircon to 25°C — can meaningfully lower bills."
            ),
            "pace_title": "Utilities Budget Pacing Warning",
            "pace_advice": "Check your aircon usage and avoid leaving appliances on standby.",
        },
        {
            "cat": "Entertainment",
            "spent": record.Entertainment,
            "budget": budget.Entertainment,
            "fallback": None,
            "over_title": "Review Entertainment Spending",
            "over_advice": (
                "Consider auditing your subscriptions and cancelling unused ones. "
                "Singapore has many free alternatives like NLB libraries, parks, and community events."
            ),
            "pace_title": "Entertainment Budget Pacing Warning",
            "pace_advice": "Review upcoming events and subscriptions to avoid overspending.",
        },
        {
            "cat": "Shopping",
            "spent": record.Shopping,
            "budget": budget.Shopping,
            "fallback": None,
            "over_title": "Cut Back on Shopping",
            "over_advice": (
                "Try the 48-hour rule — wait 2 days before any non-essential purchase. "
                "Most impulse buys feel less urgent after a short pause."
            ),
            "pace_title": "Shopping Budget Pacing Warning",
            "pace_advice": "Avoid browsing deal sites and delete saved payment info to add friction to impulse buys.",
        },
        {
            "cat": "Healthcare",
            "spent": record.Healthcare,
            "budget": budget.Healthcare,
            "fallback": SG_AVERAGES["Healthcare"],
            "over_title": "Use Polyclinics Over Private Clinics",
            "over_advice": (
                "Polyclinic visits cost as little as $15 vs $80+ at private clinics for the same treatment. "
                "Check whether your MediShield Life plan covers recent bills."
            ),
            "pace_title": "Healthcare Budget Pacing Warning",
            "pace_advice": "For non-urgent needs, book polyclinic appointments in advance to save significantly.",
        },
        {
            "cat": "Other",
            "spent": record.Other,
            "budget": budget.Other,
            "fallback": None,
            "over_title": "Review Miscellaneous Spending",
            "over_advice": (
                "Tracking these smaller expenses can reveal hidden patterns that add up over time. "
                "Consider recategorising some items — they may belong in a category with more budget headroom."
            ),
            "pace_title": "Miscellaneous Budget Pacing Warning",
            "pace_advice": "Log each 'Other' purchase with a note so you can spot the biggest culprits.",
        },
    ]

    for cfg in categories_config:
        cat      = cfg["cat"]
        spent    = cfg["spent"] or 0.0
        bgt      = cfg["budget"] or 0.0
        fallback = cfg["fallback"]

        # Determine the effective threshold: prefer user's budget, fall back to SG average
        threshold = bgt if bgt > 0 else (fallback or 0.0)
        if threshold <= 0:
            continue  # No basis for comparison → skip

        exceeded_by = spent - threshold

        if exceeded_by > 0:
            # ── Already over budget ──
            add_suggestion(
                title=cfg["over_title"],
                description=(
                    f"You've spent ${spent:,.0f} on {cat.lower()} this month, "
                    f"exceeding your {'budget' if bgt > 0 else 'typical'} of ${threshold:,.0f} "
                    f"by ${exceeded_by:,.0f}.{income_context(spent)} "
                    f"{cfg['over_advice']}{cpi_suffix(cat)}"
                ),
                savings=exceeded_by,
                cat=cat,
            )
        else:
            # ── Check if pace will cause overshoot ──
            warning = pace_warning(spent, threshold)
            if warning:
                add_suggestion(
                    title=cfg["pace_title"],
                    description=(
                        f"{warning}{income_context(spent)} "
                        f"{cfg['pace_advice']}{cpi_suffix(cat)}"
                    ),
                    # Savings = projected overage (what you'd save by reining in)
                    savings=round((spent / month_progress) - threshold, 2),
                    cat=cat,
                )

    # ── CPI-only insight for high-inflation categories not yet covered ──
    HIGH_INFLATION_THRESHOLD = 3.0
    for our_cat, yoy in category_cpi.items():
        if yoy is None or yoy < HIGH_INFLATION_THRESHOLD:
            continue
        spent = getattr(record, our_cat, 0) or 0.0
        if spent <= 0 or our_cat in covered_categories:
            continue
        suggestions.append({
            "title": f"Rising {our_cat} Prices — Plan Ahead",
            "description": (
                f"National {our_cat.lower()} prices are up {yoy:.1f}% year-on-year. "
                f"You've spent ${spent:,.0f} on {our_cat.lower()} this month. "
                "Consider buying in bulk or substituting with cheaper alternatives "
                "to shield yourself from further price increases."
            ),
            "savings": round(spent * (yoy / 100), 2),  # Estimate: save the inflation % of your spend
        })

    return suggestions


# Add this to the bottom of your file to "activate" the Törnqvist logic
def get_user_tornqvist_analysis(base_totals: dict, current_totals: dict):
    # 1. Convert to shares
    s0 = calculate_shares(base_totals)
    st = calculate_shares(current_totals)
    
    # 2. Calculate price ratios
    ratios = {cat: current_totals[cat] / base_totals[cat] 
              for cat in base_totals if base_totals[cat] > 0}
              
    # 3. Call the Törnqvist function
    return compute_tornqvist_pir(s0, st, ratios)
