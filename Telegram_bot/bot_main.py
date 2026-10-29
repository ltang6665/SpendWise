import io
import csv
import requests
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest

from utils import format_success_message, generate_item_csv, generate_monthly_csv, is_user_linked
from config import settings
from bot_ai_handler import extract_expense_data

BACKEND_URL = settings.BACKEND_URL
active_splits = {}
pending_csv_imports = {} # holds data waiting for overwrite confirmation

# menu buttons
async def post_init(application):
    """Sets the bot's command list in the Telegram Menu button."""
    commands = [
        BotCommand("help", "Show all available commands and features"),
        BotCommand("budget", "View your current budget limits"),
        BotCommand("link", "Link your SpendWise account using a code"),
        BotCommand("unlink", "Unlink your SpendWise account"),
        BotCommand("split", "Split a bill with friends in a group"),
        BotCommand("tab", "Manage group running tabs (Group Chat only)"),
        BotCommand("challenge", "Join the monthly budget leaderboard (Group Chat only)"),
        BotCommand("csv", "Get the CSV template for bulk import"),
    ]
    await application.bot.set_my_commands(commands)

# --- COMMAND: Help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Succinctly explains available bot features."""
    help_text = (
        "🤖 **SpendWise Help**\n\n"
        "• **Log Expense:** Send text (e.g., 'Coffee $5') or a photo of a receipt.\n"
        "• `/link <code>`: Connect your SpendWise account.\n"
        "• `/budget`: View category limits and status.\n"
        "• `/split <amt> <desc>`: Start a group bill split.\n"
        "• `/tab add <amt> <desc>`: Reply to someone to add to the group tab.\n"
        "• `/tab status`: View who owes whom in the group.\n"
        "• `/challenge join`: Enter the group's monthly budget leaderboard.\n"
        "• `/csv`: Download the bulk import template.\n"
        "• **Undo:** Use the `/delete` command provided after saving an item.\n\n"
        "I'll also alert you here for budget thresholds or unusual activity."
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

# --- COMMAND: Start / Help ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_linked(user_id):
        await update.message.reply_text(
            "🛑 You are not linked to a SpendWise account!\n"
            "Please go to your SpendWise settings, click 'Link Telegram', and send me your code."
        )
        return
    
    await update.message.reply_text("✅ Welcome back to SpendWise! Send me an expense, a receipt photo, or use /split.")

# --- COMMAND: Link Account ---
async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Get the Telegram ID directly from the message metadata
    telegram_id = update.effective_user.id
    
    # 2. Check if the user provided the 6-digit code
    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "⚠️ Format: /link <6-digit-code>\n"
            "Example: /link 123456\n"
            "You can get this code from your SpendWise settings page."
        )
        return
        
    link_code = args[0]
    
    # 3. Send the code AND the Telegram ID to your FastAPI backend
    headers = {"x-bot-token": settings.INTERNAL_BOT_SECRET}
    payload = {
        "TelegramId": update.effective_user.id,
        "LinkCode": link_code
    }
    
    await update.message.reply_text("🔄 Verifying your code...")
    
    try: # <--- Fixed indentation here (4 spaces)
        response = requests.post(f"{BACKEND_URL}/bot/link-account", json=payload, headers=headers)
        
        if response.status_code == 200:
            await update.message.reply_text("✅ **Account Linked Successfully!**", parse_mode="Markdown")
        else:
            try:
                error_msg = response.json().get("detail", "Failed to link account.")
            except Exception:
                error_msg = f"Backend Server Error (Status {response.status_code}). Please check server logs."
            
            await update.message.reply_text(f"❌ {error_msg}")
            
    except requests.exceptions.RequestException as e: # <--- Aligned perfectly with try
        await update.message.reply_text("❌ Could not connect to the SpendWise server.")

# --- COMMAND: Unlink ---
async def unlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unlinks the user's Telegram account from their SpendWise web account."""
    telegram_id = update.effective_user.id
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/bot/unlink-bot",
            headers={"x-bot-token": settings.INTERNAL_BOT_SECRET},
            json={"TelegramId": telegram_id}
        )
        
        if response.status_code == 200:
            await update.message.reply_text("✅ Your Telegram account has been successfully unlinked from SpendWise.")
        elif response.status_code == 404:
            await update.message.reply_text("⚠️ Your account is not currently linked to SpendWise.")
        else:
            await update.message.reply_text("❌ Failed to unlink account. Please try again later.")
    except Exception as e:
        await update.message.reply_text("❌ Error connecting to the SpendWise server.")

# --- COMMAND: CSV Templates ---
async def csv_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 **Bulk Import Templates**\nChoose the format that fits your needs. Do not modify the header rows!")
    await update.message.reply_document(document=generate_monthly_csv(), caption="Use this to import total spending per category for past months.")
    await update.message.reply_document(document=generate_item_csv(), caption="Use this to import individual past purchases line-by-line.")

# --- COMMAND: Group Split Initiation ---
async def split_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if not is_user_linked(user_id):
        await update.message.reply_text("🛑 You must link your SpendWise account to start a split.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Format: /split <amount> <description>\nExample: /split 100 Olive Garden")
        return

    try:
        amount = float(args[0])
        raw_item_name = " ".join(args[1:])
    except ValueError:
        await update.message.reply_text("⚠️ Please provide a valid number for the amount.")
        return

    # Let the user know the AI is thinking, since it takes ~2 seconds
    processing_msg = await update.message.reply_text("🧠 Analyzing category...")

    # 1. Use your existing AI to categorize the split!
    ai_data = extract_expense_data(f"I spent {amount} on {raw_item_name}")
    
    category = "Other" # Default fallback
    item_name = raw_item_name
    
    # 2. Extract the AI's logic if successful
    if ai_data and ai_data.get("IsValidExpense") and ai_data.get("Expenses"):
        extracted = ai_data["Expenses"][0]
        category = extracted.get("Type", "Other")
        item_name = extracted.get("ItemName", raw_item_name) # AI usually cleans up names nicely!

    keyboard = [
        [InlineKeyboardButton("🙋‍♂️ Join Split", callback_data="join_split"),
         InlineKeyboardButton("❌ Leave", callback_data="leave_split")],
        [InlineKeyboardButton("✅ Finalize & Charge", callback_data="finalize_split")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = await processing_msg.edit_text(
        f"🍕 **{user_name} is splitting a bill!**\n\n"
        f"**Item:** {item_name}\n"
        f"**Category:** {category}\n" # Added category to the UI
        f"**Total Amount:** ${amount:.2f}\n"
        f"**Current Participants:** 1 ({user_name})\n"
        f"**Cost Per Person:** ${amount:.2f}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    active_splits[message.message_id] = {
        "amount": amount,
        "item": item_name,         # AI short name
        "raw_desc": raw_item_name, # original text
        "category": category, 
        "participants": {user_id: user_name}, 
        "creator": user_id
    }

# --- COMMAND: Delete Expense ---
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t_id = update.effective_user.id
    if not is_user_linked(t_id): return
    
    args = context.args
    if len(args) not in (2, 3):
        await update.message.reply_text("⚠️ Please use the exact delete command provided in the success message.")
        return
        
    expense_id = args[0]
    if len(args) == 3:
        basket_id = args[1]
        is_recurring = args[2].lower() == "1"
    else:
        basket_id = None
        is_recurring = args[1].lower() == "1"
    
    headers = {"x-bot-token": settings.INTERNAL_BOT_SECRET, "x-telegram-id": str(t_id)}
    params = {"is_recurring": str(is_recurring).lower()}
    if basket_id is not None:
        params["basket_id"] = basket_id
    res = requests.delete(
        f"{BACKEND_URL}/bot/delete-expense/{expense_id}",
        params=params,
        headers=headers,
    )
    
    if res.status_code == 200:
        await update.message.reply_text("✅ Expense successfully deleted and budget totals updated.")
    else:
        await update.message.reply_text("❌ Could not find or delete that expense.")

# --- COMMAND: View Budget ---
async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t_id = update.effective_user.id
    if not is_user_linked(t_id): return
    
    headers = {"x-bot-token": settings.INTERNAL_BOT_SECRET, "x-telegram-id": str(t_id)}
    res = requests.get(f"{BACKEND_URL}/bot/budget", headers=headers)
    
    if res.status_code == 200:
        data = res.json()
        msg = (
            f"📊 **Your Current Budget**\n\n"
            f"💰 **Total:** ${data['TotalBudget']}\n"
            f"🍔 Food: ${data['Food']}\n"
            f"🚗 Transport: ${data['Transport']}\n"
            f"💡 Utilities: ${data['Utilities']}\n"
            f"🎬 Entertainment: ${data['Entertainment']}\n"
            f"🛍️ Shopping: ${data['Shopping']}\n"
            f"⚕️ Healthcare: ${data['Healthcare']}\n"
            f"📦 Other: ${data['Other']}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Could not fetch budget.")



# ------------------------------------------------------------------------------------------------------------------------------------



# --- HANDLER: AI Text Expense (One-off/Recurring) ---
async def handle_text_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t_id = update.effective_user.id
    chat_type = update.message.chat.type
    message_text = update.message.text
    
    # NEW GUARD: Only process text in groups if the bot is mentioned
    # In Private DM, always process.
    bot_username = (await context.bot.get_me()).username
    if chat_type != "private" and f"@{bot_username}" not in message_text:
        return # Ignore random group chatter

    if not is_user_linked(t_id): return

    await update.message.reply_text("🧠 Analyzing...")
    data = extract_expense_data(update.message.text)

    if data is None:
        await update.message.reply_text("❌ The AI servers are busy. Please try again!")
        return
        
    # FIX: Changed 'IsValid' to 'IsValidExpense' to match bot_ai_handler.py
    if not data.get("IsValidExpense") or not data.get("Expenses"):
        await update.message.reply_text("🤔 I couldn't find any expense details in that message.")
        return

    headers = {"x-bot-token": settings.INTERNAL_BOT_SECRET, "x-telegram-id": str(t_id)}
    success_messages = []
    
    # Loop through every expense
    for exp in data["Expenses"]:
        exp_payload = exp.copy()
        exp_payload.pop("Reasoning", None) # Remove reasoning before sending to FastAPI
        
        res = requests.post(f"{BACKEND_URL}/bot/add-expense", json=exp_payload, headers=headers)
        
        if res.status_code == 201:
            # Extract the response data from FastAPI
            res_data = res.json()
            # Pass the newly created ID and recurring flag into your formatting helper
            success_messages.append(format_success_message(
                exp,
                res_data["expense_id"],
                res_data["is_recurring"],
                res_data.get("basket_id"),
            ))
        else:
            success_messages.append(f"❌ Failed to save: {exp.get('ItemName')}")

    # Combine all messages into one detailed reply
    final_reply = "\n\n---\n\n".join(success_messages)
    await update.message.reply_text(final_reply, parse_mode="Markdown")

# --- HANDLER: Receipt Image Scan ---
async def handle_receipt_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t_id = update.effective_user.id
    chat_type = update.message.chat.type
    caption = update.message.caption or "" # Images use 'caption' instead of 'text'
    
    # NEW GUARD: Only process photos in groups if the bot is mentioned in the caption
    bot_username = (await context.bot.get_me()).username
    if chat_type != "private" and f"@{bot_username}" not in caption:
        return # Ignore non-directed photos in groups
    
    if not is_user_linked(t_id): return

    await update.message.reply_text("📸 Scanning receipt image...")
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()

    data = extract_expense_data(update.message.caption or "Here is a receipt", bytes(image_bytes))

    if data is None:
        await update.message.reply_text("❌ The AI servers are busy. Please try again!")
        return
        
    # FIX: Updated to support the new 'Expenses' list structure
    if not data.get("IsValidExpense") or not data.get("Expenses"):
        await update.message.reply_text("🤔 I couldn't extract any clear expense details from that image.")
        return

    headers = {"x-bot-token": settings.INTERNAL_BOT_SECRET, "x-telegram-id": str(t_id)}
    success_messages = []

    # Loop through every expense
    for exp in data["Expenses"]:
        exp_payload = exp.copy()
        exp_payload.pop("Reasoning", None) # Remove reasoning before sending to FastAPI
        
        res = requests.post(f"{BACKEND_URL}/bot/add-expense", json=exp_payload, headers=headers)
        
        if res.status_code == 201:
            # Extract the response data from FastAPI
            res_data = res.json()
            # Pass the newly created ID and recurring flag into your formatting helper
            success_messages.append(format_success_message(
                exp,
                res_data["expense_id"],
                res_data["is_recurring"],
                res_data.get("basket_id"),
            ))
        else:
            success_messages.append(f"❌ Failed to save: {exp.get('ItemName')}")

    final_reply = "\n\n---\n\n".join(success_messages)
    await update.message.reply_text(final_reply, parse_mode="Markdown")

# --- HANDLER: Bulk CSV Import ---
async def handle_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t_id = update.effective_user.id
    if not is_user_linked(t_id): return

    file = await update.message.document.get_file()
    bytes_data = await file.download_as_bytearray()
    text_data = bytes_data.decode('utf-8')
    
    csv_reader = csv.reader(io.StringIO(text_data))
    try:
        headers = [h.strip() for h in next(csv_reader)]
    except StopIteration:
        await update.message.reply_text("❌ The CSV file is empty.")
        return

    expected_monthly = ["Month", "Food", "Transport", "Utilities", "Entertainment", "Shopping", "Healthcare", "Other"]
    expected_items = ["DatePurchased", "ItemName", "AmountSpent", "Category", "Recurring", "Note"]

    headers_dict = {"x-bot-token": settings.INTERNAL_BOT_SECRET, "x-telegram-id": str(t_id)}
    
    # Pass fieldnames explicitly so DictReader maps correctly despite extra guide columns
    dict_reader = csv.DictReader(io.StringIO(text_data), fieldnames=headers)
    next(dict_reader) # Skip the actual header row
    
    payload = []
    row_num = 2 # Start at row 2 for error reporting (row 1 was the header)
    
    # 3. Route based on which template matched (using [:8] and [:6] to ignore the side-tables)
    if headers[:8] == expected_monthly:
        import_type = "Monthly Categories"
        for row in dict_reader:
            # Skip empty rows or guide text rows that don't have a Month
            if not row.get("Month") or not str(row.get("Month")).strip():
                row_num += 1
                continue
                
            try:
                if not re.match(r"^\d{4}-\d{2}$", str(row["Month"]).strip()):
                    raise ValueError("Month must be exactly in YYYY-MM format.")
                
                clean_row = {"Month": row["Month"].strip()}
                for cat in expected_monthly[1:]:
                    val = str(row.get(cat, "0")).strip()
                    if not val: val = "0"
                    # Strict validation: throws ValueError if they type words instead of numbers
                    clean_row[cat] = float(val) 
                
                payload.append(clean_row)
            except ValueError as e:
                await update.message.reply_text(f"❌ **Error in Excel Row {row_num}:**\n{e}\nPlease fix your CSV and try again.", parse_mode="Markdown")
                return
            row_num += 1

        await update.message.reply_text("🔄 Processing Monthly Categories import...")
        res = requests.post(f"{BACKEND_URL}/bot/import-monthly?overwrite=false", json=payload, headers=headers_dict)
        
        # ... (Keep your existing Monthly Conflicts / Overwrite logic here) ...
        if res.status_code in [200, 201]:
            res_data = res.json()
            processed = res_data.get("months_processed", 0)
            conflicts = res_data.get("conflicts", [])
            
            if conflicts:
                pending_csv_imports[t_id] = conflicts
                conflict_months = [c["Month"] for c in conflicts]
                
                msg = f"✅ Added {processed} new months.\n\n" if processed > 0 else ""
                msg += f"⚠️ **{len(conflicts)} months already exist in your database:**\n{', '.join(conflict_months)}\n\nDo you want to overwrite them with the data in this CSV?"
                
                keyboard = [
                    [InlineKeyboardButton("✅ Yes, Overwrite", callback_data="csv_overwrite"),
                     InlineKeyboardButton("❌ No, Cancel", callback_data="csv_cancel")]
                ]
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            else:
                await update.message.reply_text(f"✅ Successfully imported all {processed} months!", parse_mode="Markdown")
            return 
            
    elif headers[:6] == expected_items:
        import_type = "Individual Items"
        valid_categories = ["Food & Dining", "Transport", "Utilities", "Entertainment", "Shopping", "Healthcare", "Other"]
        
        for row in dict_reader:
            date_str = str(row.get("DatePurchased", "")).strip()
            # Skip empty rows and the side-table guide text rows
            if not date_str:
                row_num += 1
                continue
                
            try:
                # 1. Flexible Date Check (Handles Excel's auto-formatting)
                parsed_date = None
                # Try multiple common formats that Excel might spit out
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%Y/%m/%d"):
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        break # Stop looking once we find a match
                    except ValueError:
                        pass
                
                if not parsed_date:
                    raise ValueError("DatePurchased must be a valid date (e.g., YYYY-MM-DD or DD/MM/YYYY).")
                
                # Normalize the date back to YYYY-MM-DD so FastAPI doesn't complain
                normalized_date = parsed_date.strftime("%Y-%m-%d")
                
                # 2. Missing Name Check
                item_name = str(row.get("ItemName", "")).strip()
                if not item_name:
                    raise ValueError("ItemName cannot be empty.")
                    
                # 3. Numeric Amount Check (blocks "yes", "no", or currency symbols)
                try:
                    amount = float(str(row.get("AmountSpent", "")).strip())
                except ValueError:
                    raise ValueError("AmountSpent must be a pure number (e.g., 4.50).")
                    
                # 4. Strict Category Check
                category = str(row.get("Category", "")).strip()
                if category not in valid_categories:
                    raise ValueError(f"Invalid category '{category}'. Must match the guide exactly.")
                    
                # 5. Strict Boolean Check
                rec_str = str(row.get("Recurring", "")).strip().upper()
                if rec_str not in ["TRUE", "FALSE"]:
                    raise ValueError("Recurring must be strictly TRUE or FALSE.")
                    
                # We map 'Category' to 'Type' so Pydantic is happy!
                clean_row = {
                    "DatePurchased": normalized_date,
                    "ItemName": item_name,
                    "AmountSpent": amount,
                    "Type": category, 
                    "Recurring": rec_str == "TRUE",
                    "Note": str(row.get("Note", "")).strip()
                }
                payload.append(clean_row)
            except ValueError as e:
                # Instantly flags the exact row with the mistake
                await update.message.reply_text(f"❌ **Error in Excel Row {row_num}:**\n{e}\nPlease fix your CSV and try again.", parse_mode="Markdown")
                return
            row_num += 1

        await update.message.reply_text("🔄 Processing Individual Items bulk import...")
        res = requests.post(f"{BACKEND_URL}/bot/import-items", json=payload, headers=headers_dict)
        
    else:
        await update.message.reply_text("❌ Invalid template format! Please use `/csv` to download the correct templates and do not modify the header rows.", parse_mode="Markdown")
        return

    # Handle success/failure for Individual Items
    if res.status_code in [200, 201]:
        await update.message.reply_text(f"✅ **{import_type} Imported Successfully!**", parse_mode="Markdown")
    else:
        error_msg = res.json().get('detail', 'Unknown error') if 'application/json' in res.headers.get('content-type', '') else 'Server Error'
        await update.message.reply_text(f"❌ Error importing data: {error_msg}")

# --- CALLBACK HANDLER: Button Clicks ---
async def handle_split_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 

    user_id = query.from_user.id
    user_name = query.from_user.first_name # Capture the name of the clicker
    message_id = query.message.message_id
    data = query.data

    if not is_user_linked(user_id):
        await context.bot.send_message(chat_id=user_id, text="🛑 You must link your SpendWise account to join splits!")
        return

    split_data = active_splits.get(message_id)
    if not split_data:
        await query.edit_message_text("⚠️ This split has expired or was already finalized.")
        return

    if data == "join_split":
        split_data["participants"][user_id] = user_name # Add to dictionary
        
    elif data == "leave_split":
        split_data["participants"].pop(user_id, None) # Remove from dictionary
        
    elif data == "finalize_split":
        if user_id != split_data["creator"]:
            await context.bot.send_message(chat_id=user_id, text="⚠️ Only the creator can finalize the split.")
            return
            
        if len(split_data["participants"]) == 0:
            await query.edit_message_text("⚠️ Cannot finalize a split with 0 participants. Cancelled.")
            del active_splits[message_id]
            return

        headers = {"x-bot-token": settings.INTERNAL_BOT_SECRET}
        payload = {
            "Amount": split_data["amount"],
            "ItemName": split_data["item"],
            "TelegramIds": list(split_data["participants"].keys()),
            "Category": split_data["category"],
            "Description": split_data["raw_desc"] 
        }
        
        response = requests.post(f"{BACKEND_URL}/bot/split-bill", json=payload, headers=headers)
        # ... (rest of the finalize logic remains the same) ...
        
        if response.status_code == 200:
            res_data = response.json()
            await query.edit_message_text(
                f"✅ **Bill Finalized!**\n\n"
                f"**{split_data['item']}** has been split.\n"
                f"Charged {res_data['users_charged']} users **${res_data['split_amount']:.2f}** each.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Failed to process split on the backend.")
            
        del active_splits[message_id]
        return

    # FORMATTING THE PARTICIPANT DISPLAY
    num_people = len(split_data["participants"])
    if num_people > 0:
        cost_per_person = split_data["amount"] / num_people
        
        # UI Logic: Show names if <= 5, otherwise just show the number
        if num_people <= 5:
            names_list = ", ".join(split_data["participants"].values())
            participant_display = f"{num_people} ({names_list})"
        else:
            participant_display = f"{num_people} people"

        keyboard = [
            [InlineKeyboardButton("🙋‍♂️ Join Split", callback_data="join_split"),
             InlineKeyboardButton("❌ Leave", callback_data="leave_split")],
            [InlineKeyboardButton("✅ Finalize & Charge", callback_data="finalize_split")]
        ]
        
        try:
            await query.edit_message_text(
                f"🍕 **Bill Split in Progress!**\n\n"
                f"**Item:** {split_data['item']}\n"
                f"**Total Amount:** ${split_data['amount']:.2f}\n"
                f"**Current Participants:** {participant_display}\n" # Inserted the new display logic
                f"**Cost Per Person:** ${cost_per_person:.2f}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except BadRequest as e:
            if "Message is not modified" in str(e):
                pass 
            else:
                raise e
    else:
        await query.edit_message_text("Everyone left the split. Split cancelled.")
        del active_splits[message_id]

# --- CALLBACK HANDLER: CSV Import Buttons ---
async def handle_csv_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    await query.answer()

    if data == "csv_cancel":
        pending_csv_imports.pop(user_id, None) # Clear memory
        await query.edit_message_text("❌ Overwrite cancelled. Existing data was kept safe.")
        return
        
    if data == "csv_overwrite":
        conflicts = pending_csv_imports.get(user_id)
        if not conflicts:
            await query.edit_message_text("⚠️ No pending overwrites found. The session may have expired.")
            return
            
        headers = {"x-bot-token": settings.INTERNAL_BOT_SECRET, "x-telegram-id": str(user_id)}
        
        # Resend the conflicting rows, but with overwrite=true
        res = requests.post(f"{BACKEND_URL}/bot/import-monthly?overwrite=true", json=conflicts, headers=headers)
        
        if res.status_code == 200:
            await query.edit_message_text(f"✅ Successfully overwritten {len(conflicts)} months!")
        else:
            await query.edit_message_text("❌ Failed to overwrite data.")
            
        pending_csv_imports.pop(user_id, None) # Clear memory

# --- COMMAND: Running Tab ---
async def tab_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.message.chat.type
    if chat_type == "private":
        await update.message.reply_text("⚠️ The `/tab` command only works in Group Chats.")
        return

    args = context.args
    group_id = update.message.chat.id
    headers = {"x-bot-token": settings.INTERNAL_BOT_SECRET}

    if not args:
        await update.message.reply_text("⚠️ Options: `/tab add <amount> <desc>` (must reply to a user), `/tab status`, `/tab settle`", parse_mode="Markdown")
        return

    action = args[0].lower()

    if action == "add":
        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ To add a tab, you must **reply** to a message from the person who owes you, typing: `/tab add 10 lunch`", parse_mode="Markdown")
            return
            
        payer_tg_id = update.effective_user.id
        owee_tg_id = update.message.reply_to_message.from_user.id
        
        try:
            amount = float(args[1])
            desc = " ".join(args[2:]) if len(args) > 2 else "Shared Expense"
        except (IndexError, ValueError):
            await update.message.reply_text("⚠️ Format: `/tab add <amount> <description>`", parse_mode="Markdown")
            return
            
        payload = {
            "GroupId": group_id, 
            "PayerTgId": payer_tg_id, 
            "OweeTgId": owee_tg_id, 
            "Amount": amount, 
            "Description": desc
        }
        res = requests.post(f"{BACKEND_URL}/bot/tab/add", json=payload, headers=headers)
        
        # THIS IS NOW PROPERLY INDENTED INSIDE THE "add" BLOCK
        if res.status_code == 200:
            data = res.json()
            await update.message.reply_text(f"📝 Tab added! **{data['owee_name']}** owes **{data['payer_name']}** ${amount:.2f}.", parse_mode="Markdown")
        else:
            try:
                error_detail = res.json().get('detail', 'Error adding tab.')
            except Exception:
                error_detail = f"Server Error (Status {res.status_code}). Check backend logs."
            
            await update.message.reply_text(f"❌ {error_detail}")

    elif action == "status":
        res = requests.get(f"{BACKEND_URL}/bot/tab/status/{group_id}", headers=headers)
        if res.status_code == 200:
            lines = res.json()["status"]
            await update.message.reply_text("📜 **Group Running Tab:**\n\n" + "\n".join(lines), parse_mode="Markdown")

    elif action == "settle":
        # Force the user to reply to the specific person they are settling with
        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ To settle up, you must **reply** to a message from the person you are settling with, typing: `/tab settle`", parse_mode="Markdown")
            return
            
        user1_tg = update.effective_user.id
        user2_tg = update.message.reply_to_message.from_user.id

        res = requests.delete(f"{BACKEND_URL}/bot/tab/settle/{group_id}/{user1_tg}/{user2_tg}", headers=headers)
        if res.status_code == 200:
            await update.message.reply_text("💸 **All debts in this group have been cleared!** Start fresh.", parse_mode="Markdown")
        else:
            # ROBUST FIX: Check if the response is actually JSON before parsing
            try:
                error_detail = res.json().get('detail', 'Error adding tab.')
            except Exception:
                error_detail = f"Server Error (Status {res.status_code}). Check backend logs."
            
            await update.message.reply_text(f"❌ {error_detail}")

# --- COMMAND: Group Challenge ---
async def challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text("⚠️ The `/challenge` command only works in Group Chats.")
        return

    args = context.args
    group_id = update.message.chat.id
    telegram_id = update.effective_user.id
    month_str = datetime.today().strftime("%Y-%m")
    headers = {"x-bot-token": settings.INTERNAL_BOT_SECRET}

    if not args:
        await update.message.reply_text("⚠️ Options: `/challenge join`, `/challenge leaderboard`", parse_mode="Markdown")
        return

    action = args[0].lower()

    if action == "join":
        payload = {
            "GroupId": group_id, 
            "TelegramId": telegram_id, 
            "Month": month_str
        }
        res = requests.post(f"{BACKEND_URL}/bot/challenge/join", json=payload, headers=headers)
        if res.status_code == 200:
            await update.message.reply_text(f"🏆 {res.json()['message']}")
        else:
            await update.message.reply_text(f"❌ {res.json().get('detail', 'Error joining.')}")

    elif action == "leaderboard":
        res = requests.get(f"{BACKEND_URL}/bot/challenge/leaderboard/{group_id}/{month_str}", headers=headers)
        if res.status_code == 200:
            board = res.json().get("leaderboard", [])
            if not board:
                await update.message.reply_text("🤷‍♂️ No one has joined the challenge this month!")
                return
                
            msg = f"📊 **Budget Leaderboard ({month_str})**\n*Ranked by lowest % of budget used*\n\n"
            for i, p in enumerate(board):
                icon = "🟢" if p["safe"] else "🔴"
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "▫️"
                msg += f"{medal} **{p['name']}**: {p['pct']}% {icon}\n"
                
            await update.message.reply_text(msg, parse_mode="Markdown")



# ------------------------------------------------------------------------------------------------------------------------------------------------
# --- MAIN EXECUTION ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("budget", budget_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("unlink", unlink_command))
    app.add_handler(CommandHandler("csv", csv_template))
    app.add_handler(CommandHandler("split", split_command))
    app.add_handler(CommandHandler("tab", tab_command))
    app.add_handler(CommandHandler("challenge", challenge_command))
    app.add_handler(CallbackQueryHandler(handle_csv_buttons, pattern="^csv_"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_expense))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt_image))
    app.add_handler(MessageHandler(filters.Document.FileExtension("csv"), handle_csv_upload))
    app.add_handler(CallbackQueryHandler(handle_split_buttons))
    
    print("SpendWise bot running...")
    app.run_polling()
