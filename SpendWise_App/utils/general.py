# general helper functions 
from datetime import date, timedelta


# Time filter helper
def get_date_filter(period: str) -> date | None:
    today = date.today()
    if period == "past_year":
        return today.replace(year=today.year - 1)
    elif period == "6_months":
        return today - timedelta(days=182)
    elif period == "this_month":
        return today.replace(day=1)
    return None
