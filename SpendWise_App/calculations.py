# code for the math calc logics 

import math 
from datetime import date
import calendar


# returns users personal inflation rate based on their spending 
def calculate_pir(items: list[dict]) -> float:
    """
    Calculates Personal Inflation Rate using the Laspeyres Price Index.

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

# returns the inflated cost of living for each subsequent month based on PIR?
# can use PIR *IF* the PIR is calculated on a monthly basis
def calculate_forecast(
    monthly_spending: list[float],
    projected_monthly_inflation_rate: float, # when calling must PIR/100 because of how PIR is returned
    months_ahead: int = 6,
    ams_window: int = 3 # allows for variation of window
) -> list[float]:
    """
    Forecasts spending for the next `months_ahead` months.

    Steps:
        1. AMS = average of the last 3 months of spending
        2. En  = AMS × (1 + r)^n  for n = 1, 2, ..., months_ahead

    Args:
        monthly_spending              : list of historical monthly spending values
                                        (must have at least 3 entries)
        projected_monthly_inflation_rate : e.g. 0.005 for 0.5% per month
        months_ahead                  : how many months to forecast (default 6)

    """
    if len(monthly_spending) < ams_window:
        raise ValueError(f"Need at least {ams_window} months of spending history to forecast.")

    ams = sum(monthly_spending[-ams_window:]) / ams_window  # uses last `ams_window` months
    r   = projected_monthly_inflation_rate

    # forecast -->  Each index in the list corresponds to a future month
    forecast = [
        round(ams * (1 + r) ** n, 2)
        for n in range(1, months_ahead + 1)
    ]
    return forecast

# 3. REAL-TIME SAVINGS (Pro-rated)
def calculate_realtime_savings(
    monthly_income: float,
    current_total_spending: float,
    reference_date: date = None
) -> float:
    """
    Calculates pro-rated real-time savings for the current month.

    Formula:
        Current Savings = (Monthly Income × (Days Passed / Total Days in Month))
                          − Current Total Spending

    This prevents savings from appearing unrealistically high early in the month.

    Args:
        monthly_income          : total expected income for the month
        current_total_spending  : total spending so far this month
        reference_date          : date to calculate from (defaults to today)

    """
    if reference_date is None:
        reference_date = date.today()

    days_passed = reference_date.day
    total_days_in_month = calendar.monthrange(reference_date.year, reference_date.month)[1]

    prorated_income = monthly_income * (days_passed / total_days_in_month)
    savings = prorated_income - current_total_spending

    return round(savings, 2)




