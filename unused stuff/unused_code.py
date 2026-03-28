#CALCULATIONS.PY DEMO CODE 

# ─────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────

# --- PIR Demo ---
basket = [
    {"name": "Rice (5kg)",    "base_price": 8.00,  "current_price": 8.80,  "weight": 40},
    {"name": "Transport",     "base_price": 90.00, "current_price": 95.00, "weight": 90},
    {"name": "Groceries",     "base_price": 200.0, "current_price": 215.0, "weight": 200},
    {"name": "Dining out",    "base_price": 150.0, "current_price": 160.0, "weight": 150},
]
pir = calculate_pir(basket)
print(f"Personal Inflation Rate : {pir:.2f}%")

# --- Forecast Demo ---
past_spending = [1800, 1950, 1870]           # last 3 months
monthly_inflation = 0.005                    # 0.5% per month
forecast = calculate_forecast(past_spending, monthly_inflation, months_ahead=6)
print("\n6-Month Spending Forecast:")
for i, amount in enumerate(forecast, 1):
    print(f"  Month {i}: ${amount:.2f}")
