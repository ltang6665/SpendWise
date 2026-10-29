import io

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Clean relative imports - just like your email.py!
from config import settings

BACKEND_URL = settings.BACKEND_URL

# --- HELPER: Rich Formatting ---
def format_success_message(
    data: dict,
    expense_id: int,
    is_recurring: bool,
    basket_id: int | None = None,
) -> str:
    if is_recurring and basket_id is not None:
        dest = "Expenses and monthly Basket"
        delete_command = f"/delete {expense_id} {basket_id} 1"
    elif is_recurring:
        # Preserve the legacy message format if connected to an older backend.
        dest = "Basket (Recurring)"
        delete_command = f"/delete {expense_id} 1"
    else:
        dest = "Expenses"
        delete_command = f"/delete {expense_id} 0"
    return (
        f"✅ **Saved to {dest}!**\n\n"
        f"🛒 **Item:** {data.get('ItemName')}\n"
        f"💰 **Amount:** ${float(data.get('AmountSpent', 0)):.2f}\n"
        f"📂 **Category:** {data.get('Type')}\n\n"
        f"🗑️ *Made a mistake? Send `{delete_command}` to undo.*"
    )

# --- HELPER: Authorization Check ---
# calls verify route 
def is_user_linked(telegram_id: int) -> bool:
    headers = {"x-bot-token": settings.INTERNAL_BOT_SECRET}
    response = requests.get(f"{BACKEND_URL}/bot/verify/{telegram_id}", headers=headers)
    return response.status_code == 200

# --- HELPER: CSV Template Generators ---
def generate_monthly_csv() -> io.BytesIO:
    """Template for importing aggregated monthly category totals."""
    template = (
        "Month,Food,Transport,Utilities,Entertainment,Shopping,Healthcare,Other,,,,--- GUIDE ---\n"
        "2026-04,150.00,45.00,60.00,25.00,0,0,0,,,,> Month format: YYYY-MM\n"
        ",,,,,,,,,,,,> All amounts must be numbers\n"
        ",,,,,,,,,,,,> Leave as 0 if no spending\n"
    )
    bio = io.BytesIO(template.encode('utf-8'))
    bio.name = "SpendWise_Monthly_Categories.csv"
    return bio

def generate_item_csv() -> io.BytesIO:
    """Template for importing individual items line-by-line."""
    template = (
        "DatePurchased,ItemName,AmountSpent,Category,Recurring,Note,,,,--- GUIDE ---,ALLOWED CATEGORIES,RECURRING FORMAT\n"
        "2026-04-18,Chicken Rice,4.50,Food & Dining,FALSE,Lunch at Kofu,,,,> Use exact names,Food & Dining,TRUE\n"
        ",,,,,,,,,> Amount is numbers only,Transport,FALSE\n"
        ",,,,,,,,,> Date is YYYY-MM-DD,Utilities,\n"
        ",,,,,,,,,> No empty fields,Entertainment,\n"
        ",,,,,,,,,> Note is optional,Shopping,\n"
        ",,,,,,,,, ,Healthcare,\n"
        ",,,,,,,,, ,Other,\n"
    )
    bio = io.BytesIO(template.encode('utf-8'))
    bio.name = "SpendWise_Individual_Items.csv"
    return bio
