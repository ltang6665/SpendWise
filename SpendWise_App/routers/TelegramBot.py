import hmac
import secrets
import string

from fastapi import APIRouter, HTTPException, Header, Depends, Query
from sqlmodel import select, extract, or_, and_
from datetime import date, datetime, timedelta, timezone
from typing import Annotated


# Adjust these imports based on your exact folder structure
from ..database import SessionDependency
from ..models import ChallengeJoinRequest, GroupChallengeDB, GroupLedgerDB, LinkAccountRequest, MonthlyCategory, MonthlyCategoryDB, SplitBillRequest, TabAddRequest, TelegramLinkAttemptDB, UserBudgetDB, UserDetails, ExpensesDB, BasketDB, UserExpenses
from ..utils.utils import get_or_create_budget, update_monthly_totals
from ..utils.email import hash_one_time_code
from ..config import settings
from ..oauth2 import get_current_active_user

router = APIRouter(
    prefix="/bot",
    tags=['Telegram Bot']
)

# Shared backend secret used to authenticate Telegram bot requests.
BOT_SECRET = settings.INTERNAL_BOT_SECRET
TELEGRAM_LINK_CODE_TTL_MINUTES = 10
TELEGRAM_LINK_MAX_FAILED_ATTEMPTS = 5
TELEGRAM_LINK_ATTEMPT_WINDOW_MINUTES = 15
TELEGRAM_LINK_LOCKOUT_MINUTES = 15

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]

def verify_bot_token(x_bot_token: str | None = Header(default=None)):
    if (
        not BOT_SECRET
        or not x_bot_token
        or not hmac.compare_digest(x_bot_token.encode("utf-8"), BOT_SECRET.encode("utf-8"))
    ):
        raise HTTPException(status_code=401, detail="Unauthorized bot request")


# Checks if a Telegram ID is linked to a SpendWise account
@router.get("/verify/{telegram_id}")
def verify_telegram_user(telegram_id: int, db: SessionDependency, token: str = Depends(verify_bot_token)):
    user = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == telegram_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not linked to SpendWise.")
    return {"linked": True, "user_id": user.Id}

# router to split bill in a group chat 
@router.post("/split-bill")
def process_split_bill(payload: SplitBillRequest, db: SessionDependency, token: str = Depends(verify_bot_token)):
    if not payload.TelegramIds:
        raise HTTPException(status_code=400, detail="No participants provided.")

    split_amount = round(payload.Amount / len(payload.TelegramIds), 2)
    if split_amount <= 0:
        raise HTTPException(
            status_code=422,
            detail="The amount must produce a positive share for each participant.",
        )
    today = date.today()
    ids_created = [] # Track the IDs to allow for "Undo"

    for t_id in payload.TelegramIds:
        user = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == t_id)).first()
        if user:
            expense = ExpensesDB(
                UserId=user.Id,
                Type=payload.Category,
                ItemName=f"{payload.ItemName} (Shared)",
                AmountSpent=split_amount,
                Recurring=False,
                DatePurchased=today,
                # Update the Note field to include the original description
                Note=f"Split bill (Total: ${payload.Amount}): {payload.Description}"
            )
            db.add(expense)
            db.commit()
            db.refresh(expense) # Get the new ID
            ids_created.append(expense.Id)
            
            update_monthly_totals(db, user.Id, today, ExpensesDB)
            db.commit()

    return {
        "success": True, 
        "split_amount": split_amount, 
        "users_charged": len(ids_created),
        "expense_ids": ",".join(map(str, ids_created)) # Return as a string for the bot
    }


# -------------------------------------------------------------------
# STEP 1: FRONTEND ENDPOINT (Generates the code for the React app)
# Notice we use `current_user` here because the React app uses standard JWT login
# -------------------------------------------------------------------
@router.post("/generate-link-code")
def generate_link_code(current_user: CurrentUser, db: SessionDependency):
    if not current_user.Id:
        raise HTTPException(status_code=404, detail="User not found")
        
    # 1. Fetch the user from the database
    user = db.get(UserDetails, current_user.Id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found in DB")

    if user.TelegramChatId is not None:
        raise HTTPException(status_code=400, detail="Unlink your Telegram account before generating a new link code.")

    # Generate a cryptographically random code, but store only a keyed digest.
    while True:
        code = ''.join(secrets.choice(string.digits) for _ in range(6))
        code_digest = hash_one_time_code(code, "telegram-link")
        collision = db.exec(select(UserDetails).where(UserDetails.TelegramLinkCode == code_digest)).first()
        if not collision:
            break

    user.TelegramLinkCode = code_digest
    user.TelegramLinkCodeExpiry = datetime.now(timezone.utc) + timedelta(minutes=TELEGRAM_LINK_CODE_TTL_MINUTES)
    db.add(user)
    db.commit()

    return {"LinkCode": code, "ExpiresInMinutes": TELEGRAM_LINK_CODE_TTL_MINUTES}

# -------------------------------------------------------------------
# STEP 3: BOT ENDPOINT (Validates the code sent by the Telegram Bot)
# Notice we use `verify_bot_token` here because the bot uses the secret token, not JWT
# -------------------------------------------------------------------
@router.post("/link-account")
def link_telegram_account(
    payload: LinkAccountRequest,
    db: SessionDependency,
    token: str = Depends(verify_bot_token),
):
    now = datetime.now(timezone.utc)

    # 1. STRICT CHECK: Is this Telegram account ALREADY linked to someone?
    existing_linked_user = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == payload.TelegramId)).first()
    if existing_linked_user:
        raise HTTPException(
            status_code=400, 
            detail="This Telegram account is already linked to a SpendWise user. Please unlink it first."
        )

    attempt = db.get(TelegramLinkAttemptDB, payload.TelegramId)
    if attempt:
        locked_until = attempt.LockedUntil
        if locked_until and (locked_until if locked_until.tzinfo else locked_until.replace(tzinfo=timezone.utc)) > now:
            raise HTTPException(status_code=429, detail="Too many incorrect link codes. Please wait for the lockout to expire before trying again.")

        window_started = attempt.WindowStartedAt
        if (
            locked_until is not None
            or window_started is None
            or now - (window_started if window_started.tzinfo else window_started.replace(tzinfo=timezone.utc))
            >= timedelta(minutes=TELEGRAM_LINK_ATTEMPT_WINDOW_MINUTES)
        ):
            attempt.FailedAttempts = 0
            attempt.WindowStartedAt = now
            attempt.LockedUntil = None

    # Codes are stored as keyed digests, so compare against the digest of the submitted code.
    stored_code = hash_one_time_code(payload.LinkCode, "telegram-link")
    target_user = db.exec(select(UserDetails).where(UserDetails.TelegramLinkCode == stored_code)).first()
    code_expiry = target_user.TelegramLinkCodeExpiry if target_user else None
    if code_expiry and not code_expiry.tzinfo:
        code_expiry = code_expiry.replace(tzinfo=timezone.utc)

    if target_user and code_expiry and code_expiry > now and target_user.TelegramChatId is None:
        target_user.TelegramChatId = payload.TelegramId
        target_user.TelegramLinkCode = None
        target_user.TelegramLinkCodeExpiry = None
        db.add(target_user)
        if attempt:
            db.delete(attempt)
        db.commit()
        return {"message": "Account linked successfully!"}

    # Expired or otherwise unusable codes are invalidated and reported generically.
    if target_user:
        target_user.TelegramLinkCode = None
        target_user.TelegramLinkCodeExpiry = None
        db.add(target_user)

    if attempt is None:
        attempt = TelegramLinkAttemptDB(
            TelegramId=payload.TelegramId,
            FailedAttempts=0,
            WindowStartedAt=now,
        )
    attempt.FailedAttempts += 1
    if attempt.FailedAttempts >= TELEGRAM_LINK_MAX_FAILED_ATTEMPTS:
        attempt.LockedUntil = now + timedelta(minutes=TELEGRAM_LINK_LOCKOUT_MINUTES)
        detail = "Too many incorrect link codes. Please wait for the lockout to expire before trying again."
        status_code = 429
    else:
        detail = "Invalid or expired link code. Generate a new code in SpendWise and try again."
        status_code = 400

    db.add(attempt)
    db.commit()
    raise HTTPException(status_code=status_code, detail=detail)

# For the React Frontend to check if the user is linked
@router.get("/status")
def get_bot_status(current_user: CurrentUser, db: SessionDependency):
    if not current_user.Id:
        raise HTTPException(status_code=404, detail="User not found")
    user = db.get(UserDetails, current_user.Id)
    return {"IsLinked": user.TelegramChatId is not None}


# For the React Frontend to trigger an unlink
@router.post("/unlink-app")
def unlink_from_app(current_user: CurrentUser, db: SessionDependency):
    if not current_user.Id:
        raise HTTPException(status_code=404, detail="User not found")
        
    user = db.get(UserDetails, current_user.Id)
    if not user.TelegramChatId:
        raise HTTPException(status_code=400, detail="Account is not linked to Telegram.")
        
    user.TelegramChatId = None
    db.add(user)
    db.commit()
    return {"message": "Account unlinked successfully."}


# For the Telegram Bot (bot_main.py) to trigger an unlink
@router.post("/unlink-bot")
def unlink_from_bot(payload: dict, db: SessionDependency, token: str = Depends(verify_bot_token)):
    telegram_id = payload.get("TelegramId")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="TelegramId required")
        
    user = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == telegram_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="No linked account found for this Telegram ID.")
        
    user.TelegramChatId = None
    db.add(user)
    db.commit()
    return {"message": "Account unlinked successfully."}

# Saves a dated payment to Expenses and, when recurring, also saves its monthly Basket plan.
@router.post("/add-expense", status_code=201)
def add_telegram_expense(payload: UserExpenses, db: SessionDependency, x_telegram_id: str = Header(...),token: str = Depends(verify_bot_token)):
    
    # 1. Find the SpendWise user by their permanent Telegram ID
    user = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == int(x_telegram_id))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not linked to a SpendWise account.")

    # Every submitted item is a dated payment. A recurring payment also creates
    # a separate Basket row representing its ongoing monthly plan.
    expense_record = ExpensesDB(
        UserId=user.Id,
        Type=payload.Type,
        ItemName=payload.ItemName,
        AmountSpent=payload.AmountSpent,
        Recurring=payload.Recurring,
        DatePurchased=payload.DatePurchased,
        Note=payload.Note,
    )
    db.add(expense_record)

    basket_record = None
    if payload.Recurring:
        basket_record = BasketDB(
            UserId=user.Id,
            Type=payload.Type,
            ItemName=payload.ItemName,
            AmountSpent=payload.AmountSpent,
            Note=payload.Note,
        )
        db.add(basket_record)

    db.flush()
    update_monthly_totals(db, user.Id, payload.DatePurchased, ExpensesDB)
    if basket_record:
        update_monthly_totals(db, user.Id, None, BasketDB)
    db.commit()

    return {
        "success": True,
        "item": payload.ItemName,
        "expense_id": expense_record.Id,
        "basket_id": basket_record.Id if basket_record else None,
        "is_recurring": payload.Recurring,
    }

# return users current budget distribution
@router.get("/budget")
def get_telegram_budget( db: SessionDependency, x_telegram_id: str = Header(...), token: str = Depends(verify_bot_token)):
    user = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == int(x_telegram_id))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not linked.")
        
    budget = get_or_create_budget(user.Id, db)
    return {
        "TotalBudget": budget.TotalBudget,
        "Food": budget.Food,
        "Transport": budget.Transport,
        "Utilities": budget.Utilities,
        "Entertainment": budget.Entertainment,
        "Shopping": budget.Shopping,
        "Healthcare": budget.Healthcare,
        "Other": budget.Other
    }

# Deletes an expense and recalculates the monthly totals.
@router.delete("/delete-expense/{expense_id}")
def delete_telegram_expense(
    expense_id: int,
    is_recurring: bool,
    db: SessionDependency,
    x_telegram_id: str = Header(...),
    token: str = Depends(verify_bot_token),
    basket_id: int | None = Query(default=None, gt=0),
):

    user = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == int(x_telegram_id))).first()
    if not user: raise HTTPException(404, "User not linked.")
    
    # New undo commands for recurring payments include both IDs, so remove the
    # dated payment and its monthly plan together. Older commands have no basket_id
    # and continue to delete their original Basket-only entry.
    if is_recurring and basket_id is not None:
        expense = db.exec(
            select(ExpensesDB).where(
                ExpensesDB.Id == expense_id,
                ExpensesDB.UserId == user.Id,
            )
        ).first()
        basket_item = db.exec(
            select(BasketDB).where(
                BasketDB.Id == basket_id,
                BasketDB.UserId == user.Id,
            )
        ).first()
        if not expense or not basket_item:
            raise HTTPException(404, "Expense or basket item not found.")

        purchase_date = expense.DatePurchased
        db.delete(expense)
        db.delete(basket_item)
        db.flush()
        update_monthly_totals(db, user.Id, purchase_date, ExpensesDB)
        update_monthly_totals(db, user.Id, None, BasketDB)
        db.commit()
        return {"success": True}

    # Legacy recurring commands and one-off commands select their original table.
    model = BasketDB if is_recurring else ExpensesDB
    expense = db.exec(select(model).where(model.Id == expense_id, model.UserId == user.Id)).first()
    
    if not expense:
        raise HTTPException(404, "Expense not found.")
        
    # Store the date before deleting so we can update the correct month
    purchase_date = expense.DatePurchased if not is_recurring else date.today()
    
    db.delete(expense)
    db.commit()
    
    # Update monthly totals to subtract the deleted amount
    update_monthly_totals(db, user.Id, purchase_date, model)
    db.commit()
    return {"success": True}

# --- Bulk Delete Route ---
@router.delete("/expense-split")
def delete_split_expenses(ids: str, db: SessionDependency, token: str = Depends(verify_bot_token)):
    """Deletes multiple expenses at once (Undo Split)."""
    id_list = [int(i) for i in ids.split(",")]
    
    for exp_id in id_list:
        expense = db.get(ExpensesDB, exp_id)
        if expense:
            user_id = expense.UserId
            p_date = expense.DatePurchased
            db.delete(expense)
            db.commit()
            # Update each user's totals after deletion
            update_monthly_totals(db, user_id, p_date, ExpensesDB)
            db.commit()
            
    return {"success": True}

# --- BULK IMPORT ROUTE ---
@router.post("/import-items")
def bulk_import_items(items: list[UserExpenses], db: SessionDependency, x_telegram_id: str = Header(...), token: str = Depends(verify_bot_token)):
    user = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == int(x_telegram_id))).first()
    if not user: 
        raise HTTPException(404, "User not linked.")
    
    dates_to_update = set()
    basket_updated = False # Track if we need to update BasketCategoryDB
    
    for item in items:
        expense_record = ExpensesDB(
            UserId=user.Id,
            Type=item.Type,
            ItemName=item.ItemName,
            AmountSpent=item.AmountSpent,
            Recurring=item.Recurring,
            DatePurchased=item.DatePurchased,
            Note=item.Note,
        )
        db.add(expense_record)
        dates_to_update.add(item.DatePurchased)

        if item.Recurring:
            # A recurring dated payment also adds its monthly plan to the Basket.
            basket_record = BasketDB(
                UserId=user.Id,
                Type=item.Type,
                ItemName=item.ItemName,
                AmountSpent=item.AmountSpent,
                Note=item.Note
            )
            db.add(basket_record)
            basket_updated = True

    db.flush()
    # Recalculate summaries for all dated payments and recurring Basket plans.
    for d in dates_to_update:
        update_monthly_totals(db, user.Id, d, ExpensesDB)
        
    if basket_updated:
        update_monthly_totals(db, user.Id, date.today(), BasketDB)
        
    db.commit()
    
    return {"success": True, "items_added": len(items)}

# Bot endpoint to import aggregated monthly category totals.
@router.post("/import-monthly")
def bulk_import_monthly(
    payload: list[MonthlyCategory], 
    db: SessionDependency, 
    overwrite: bool = False, 
    x_telegram_id: str = Header(...), 
    token: str = Depends(verify_bot_token)
):
    months = [row.Month for row in payload]
    if len(months) != len(set(months)):
        raise HTTPException(400, "Duplicate months found in the CSV.")

    user = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == int(x_telegram_id))).first()
    if not user: raise HTTPException(404, "User not linked.")

    processed_count = 0
    conflicts = []

    for row in payload:
        target_date = date(int(row.Month[:4]), int(row.Month[5:]), 1)

        # Check if imported data already exists for this month
        existing = db.exec(select(ExpensesDB).where(
            ExpensesDB.UserId == user.Id,
            ExpensesDB.ItemName.startswith("Imported Category:"),
            extract('month', ExpensesDB.DatePurchased) == target_date.month,
            extract('year', ExpensesDB.DatePurchased) == target_date.year
        )).first()

        if existing and not overwrite:
            conflicts.append(row.model_dump())
            continue

        if existing and overwrite:
            # Wipe only the old IMPORTED data for that month so we can replace it
            old_records = db.exec(select(ExpensesDB).where(
                ExpensesDB.UserId == user.Id,
                ExpensesDB.ItemName.startswith("Imported Category:"),
                extract('month', ExpensesDB.DatePurchased) == target_date.month,
                extract('year', ExpensesDB.DatePurchased) == target_date.year
            )).all()
            for rec in old_records:
                db.delete(rec)
            db.commit()

        # Convert the CSV row into standard Expense items
        cat_map = {
            "Food & Dining": row.Food, "Transport": row.Transport, 
            "Utilities": row.Utilities, "Entertainment": row.Entertainment, 
            "Shopping": row.Shopping, "Healthcare": row.Healthcare, "Other": row.Other
        }

        for db_cat, amount in cat_map.items():
            if amount > 0:
                exp = ExpensesDB(
                    UserId=user.Id,
                    Type=db_cat,
                    ItemName=f"Imported Category: {db_cat}",
                    AmountSpent=amount,
                    Recurring=False,
                    DatePurchased=target_date,
                    Note="Imported via CSV"
                )
                db.add(exp)

        db.commit()
        # Automatically updates MonthlyCategoryDB!
        update_monthly_totals(db, user.Id, target_date, ExpensesDB) 
        db.commit()
        processed_count += 1

    return {"success": True, "months_processed": processed_count, "conflicts": conflicts}


# --- ADD TO THE BOTTOM OF TelegramBot.py ---

# ==========================================
# FEATURE 1: RUNNING TAB (GROUP LEDGER)
# ==========================================

@router.post("/tab/add")
def add_group_tab(payload: TabAddRequest, db: SessionDependency, token: str = Depends(verify_bot_token)):
    # FIX: Use PascalCase payload.PayerTgId and payload.OweeTgId
    payer = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == payload.PayerTgId)).first()
    owee = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == payload.OweeTgId)).first()
    
    if not payer or not owee:
        raise HTTPException(404, "Both users must have linked SpendWise accounts.")
        
    if payer.Id == owee.Id:
        raise HTTPException(400, "You cannot owe yourself money.")

    new_tab = GroupLedgerDB(
        GroupId=payload.GroupId, 
        PayerId=payer.Id, 
        OweeId=owee.Id,
        Amount=payload.Amount, 
        Description=payload.Description
    )

    # Immediately log it as an expense for the person who owes the money
    # (Defaulting to "Other" category since /tab doesn't specify one)
    today = date.today()
    expense = ExpensesDB(
        UserId=owee.Id,
        Type="Other", 
        ItemName=payload.Description,
        AmountSpent=payload.Amount,
        Recurring=False,
        DatePurchased=today,
        Note=f"Added via Group Tab (Paid by {payer.Email.split('@')[0]})"
    )
    db.add(expense)
    db.commit() # Commit to generate the expense ID
    
    # 3. Update the Owee's monthly budget totals!
    update_monthly_totals(db, owee.Id, today, ExpensesDB)
    db.commit()

    return {"success": True, "payer_name": payer.Email.split('@')[0], "owee_name": owee.Email.split('@')[0]}

@router.get("/tab/status/{group_id}")
def get_tab_status(group_id: int, db: SessionDependency, token: str = Depends(verify_bot_token)):
    # Fetch all unsettled tabs for this group
    records = db.exec(select(GroupLedgerDB).where(GroupLedgerDB.GroupId == group_id)).all()
    
    # Calculate 1-to-1 net debts
    debts = {} # (user_id_A, user_id_B): net_balance_for_A
    for r in records:
        pair = tuple(sorted((r.PayerId, r.OweeId)))
        if pair not in debts: debts[pair] = 0.0
        
        # Positive means pair[0] is owed money, negative means pair[1] is owed money
        if r.PayerId == pair[0]:
            debts[pair] += r.Amount
        else:
            debts[pair] -= r.Amount

    summary = []
    for (u1_id, u2_id), net in debts.items():
        if round(net, 2) == 0: continue
        
        u1 = db.get(UserDetails, u1_id)
        u2 = db.get(UserDetails, u2_id)
        u1_name, u2_name = u1.Email.split('@')[0], u2.Email.split('@')[0]
        
        if net > 0:
            summary.append(f"🔹 **{u2_name}** owes **{u1_name}** ${abs(net):.2f}")
        else:
            summary.append(f"🔹 **{u1_name}** owes **{u2_name}** ${abs(net):.2f}")

    return {"status": summary if summary else ["✅ All settled up! No active tabs."]}

@router.delete("/tab/settle/{group_id}/{user1_tg}/{user2_tg}")
def settle_specific_tabs(group_id: int, user1_tg: int, user2_tg: int, db: SessionDependency, token: str = Depends(verify_bot_token)):
    
    # 1. Look up the internal SpendWise IDs for both Telegram users
    u1 = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == user1_tg)).first()
    u2 = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == user2_tg)).first()
    
    if not u1 or not u2:
        raise HTTPException(404, "One or both users are not linked.")
        
    # 2. Find ONLY the tabs between these two specific users in this group
    records = db.exec(select(GroupLedgerDB).where(
        GroupLedgerDB.GroupId == group_id,
        or_(
            and_(GroupLedgerDB.PayerId == u1.Id, GroupLedgerDB.OweeId == u2.Id),
            and_(GroupLedgerDB.PayerId == u2.Id, GroupLedgerDB.OweeId == u1.Id)
        )
    )).all()

    # 3. Delete only those specific records
    for r in records: 
        db.delete(r)
        
    db.commit()
    return {"success": True}
# ==========================================
# FEATURE 2: BUDGET LEADERBOARD CHALLENGE
# ==========================================

@router.post("/challenge/join")
def join_challenge(payload: ChallengeJoinRequest, db: SessionDependency, token: str = Depends(verify_bot_token)):
    # FIX: Use PascalCase payload.TelegramId
    user = db.exec(select(UserDetails).where(UserDetails.TelegramChatId == payload.TelegramId)).first()
    if not user: 
        raise HTTPException(404, "User not linked.")
    
    # FIX: Use PascalCase for GroupId and Month
    existing = db.exec(select(GroupChallengeDB).where(
        GroupChallengeDB.GroupId == payload.GroupId,
        GroupChallengeDB.UserId == user.Id,
        GroupChallengeDB.Month == payload.Month
    )).first()
    
    if existing: 
        return {"success": True, "message": "Already joined."}
        
    db.add(GroupChallengeDB(GroupId=payload.GroupId, UserId=user.Id, Month=payload.Month))
    db.commit()
    return {"success": True, "message": f"{user.Email.split('@')[0]} joined the challenge!"}

@router.get("/challenge/leaderboard/{group_id}/{month}")
def get_leaderboard(group_id: int, month: str, db: SessionDependency, token: str = Depends(verify_bot_token)):
    participants = db.exec(select(GroupChallengeDB).where(
        GroupChallengeDB.GroupId == group_id, GroupChallengeDB.Month == month
    )).all()
    
    if not participants: 
        return {"leaderboard": []}
    
    results = []
    for p in participants:
        user = db.get(UserDetails, p.UserId)
        budget = db.exec(select(UserBudgetDB).where(UserBudgetDB.UserId == user.Id)).first()
        spent_record = db.exec(select(MonthlyCategoryDB).where(
            MonthlyCategoryDB.UserId == user.Id, MonthlyCategoryDB.Month == month
        )).first()
        
        # ROBUST FIX: Ensure we never divide by zero even if the budget is 0.0
        # If budget is 0 or missing, we treat it as 1 for the calculation.
        total_budget = budget.TotalBudget if (budget and budget.TotalBudget > 0) else 1
        
        total_spent = (spent_record.Food + spent_record.Transport + spent_record.Utilities + 
                       spent_record.Entertainment + spent_record.Shopping + spent_record.Healthcare + 
                       getattr(spent_record, 'Other', 0.0)) if spent_record else 0.0
                       
        pct_used = (total_spent / total_budget) * 100
        results.append({
            "name": user.Email.split('@')[0], 
            "pct": round(pct_used, 1),
            "safe": pct_used <= 100
        })
        
    results.sort(key=lambda x: x["pct"])
    return {"leaderboard": results}
