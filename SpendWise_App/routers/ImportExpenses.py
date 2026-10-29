import csv
import io
import math
import re
from fastapi import status, HTTPException, Depends, APIRouter, Query, UploadFile, File
from fastapi.responses import Response
from datetime import date, datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, delete, extract

from ..utils.utils import update_monthly_totals
from ..oauth2 import get_current_active_user
from ..models import BasketDB, MonthlyCategory, ExpensesDB, MonthlyCategoryDB, DeleteExpensesRequest, UserDetails
from ..database import *


router = APIRouter(
    prefix="/import",
    tags=['Import Past Expenses']
)

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]


# csv file tempaltes
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

# donload csv template route
@router.get("/template")
def download_csv_template(template_type: str = Query(..., description="Use 'monthly' or 'detailed'")):
    """Provides the user with the exact CSV headers needed for import."""
    if template_type == "monthly":
        bio = generate_monthly_csv()
    elif template_type == "detailed":
        bio = generate_item_csv()
    else:
        raise HTTPException(400, "Invalid template type. Use 'monthly' or 'detailed'.")

    return Response(
        content=bio.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={bio.name}"}
    )

# uplaod and process the csv 
@router.post("/upload-csv")
async def upload_csv_expenses(current_user: CurrentUser, db: SessionDependency, file: UploadFile = File(...), overwrite: bool = False):
    
    # Edge Case: Wrong file extension
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(400, "Only .csv files are accepted.")
        
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8-sig') # utf-8-sig removes Excel BOM characters safely
    except UnicodeDecodeError:
        raise HTTPException(400, "File encoding error. Please ensure it is saved as UTF-8 CSV.")
        
    reader = csv.DictReader(io.StringIO(decoded))
    headers = reader.fieldnames or []
    
    processed_count = 0
    dates_to_update = set()
    error_log = [] # Collect errors to show the user exactly what failed
    row_num = 1 # Start at 1 (Headers are row 0)
    
    # ALLOWED CATEGORY MAP (Handles "Food & Dining" from template -> "Food" in DB)
    cat_map = {
        "food & dining": "Food", "food": "Food", "transport": "Transport", 
        "utilities": "Utilities", "entertainment": "Entertainment", 
        "shopping": "Shopping", "healthcare": "Healthcare", "other": "Other"
    }

    # ---------------------------------------------------------
    # PATH A: Process Monthly Aggregated Data
    # ---------------------------------------------------------
    if "Month" in headers and "Food" in headers:
        for row in reader:
            row_num += 1
            month_str = (row.get("Month") or "").strip()
            
            # Skip entirely empty visual/guide rows
            if not month_str and not row.get("Food"): 
                continue
                
            # Edge Case: Invalid Month format
            if not re.match(r"^\d{4}-\d{2}$", month_str):
                error_log.append(f"Row {row_num}: Invalid Month '{month_str}'. Must be YYYY-MM.")
                continue
            
            t_year, t_month = int(month_str[:4]), int(month_str[5:])
            try:
                target_date = date(t_year, t_month, 1)
            except ValueError:
                error_log.append(f"Row {row_num}: Invalid Month '{month_str}'. Must be a real month in YYYY-MM format.")
                continue
            
            # Check for existing data
            existing = db.exec(select(ExpensesDB).where(
                ExpensesDB.UserId == current_user.Id,
                ExpensesDB.ItemName.startswith("Imported Category:"),
                extract('month', ExpensesDB.DatePurchased) == t_month,
                extract('year', ExpensesDB.DatePurchased) == t_year
            )).all()
            
            if existing and not overwrite:
                error_log.append(f"Row {row_num}: Data for {month_str} already exists. Use overwrite.")
                continue
            # Process Categories safely
            categories = ["Food", "Transport", "Utilities", "Entertainment", "Shopping", "Healthcare", "Other"]
            row_success = True
            row_expenses = []
            
            for cat in categories:
                raw_amt = (row.get(cat) or "0").strip() or "0"
                try:
                    amount = float(raw_amt)
                    if not math.isfinite(amount) or amount < 0: raise ValueError
                except ValueError:
                    error_log.append(f"Row {row_num}: Invalid amount '{raw_amt}' for {cat}.")
                    row_success = False
                    break # Stop processing this row if one column is corrupted
                
                if amount > 0:
                    row_expenses.append(ExpensesDB(
                        UserId=current_user.Id, Type=cat, ItemName=f"Imported Category: {cat}",
                        AmountSpent=amount, Recurring=False, DatePurchased=target_date, Note="Imported via Web CSV"
                    ))
                    
            if row_success:
                if existing and overwrite:
                    for record in existing:
                        db.delete(record)
                for expense in row_expenses:
                    db.add(expense)
                dates_to_update.add(target_date)
                processed_count += 1
            
    # ---------------------------------------------------------
    # PATH B: Process Detailed Itemized Data
    # ---------------------------------------------------------
    elif "DatePurchased" in headers and "ItemName" in headers and "AmountSpent" in headers:
        for row in reader:
            row_num += 1
            date_str = row.get("DatePurchased", "").strip()
            
            # Skip empty visual/guide rows
            if not date_str and not row.get("ItemName"): continue
            
            # Edge Case 1: Validate Date
            raw_date = row.get("DatePurchased", "").strip()
            target_date = None

            # Try multiple formats to handle Excel's auto-formatting
            # Added common Excel formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, and dashes
            for date_fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
                try:
                    # Handle cases where Excel includes a hidden timestamp (e.g., 2026-04-19 00:00:00)
                    clean_date = raw_date.split()[0] 
                    target_date = datetime.strptime(clean_date, date_fmt).date()
                    break # Successfully parsed!
                except ValueError:
                    continue

            # If the loop finishes and target_date is still None, no formats matched
            if not target_date:
                error_log.append(f"Row {row_num}: Invalid date format '{raw_date}'. Please use YYYY-MM-DD or DD/MM/YYYY.")
                continue
                
            # Edge Case 2: Validate ItemName
            item_name = row.get("ItemName", "").strip()
            if not item_name:
                error_log.append(f"Row {row_num}: Missing ItemName.")
                continue
                
            # Edge Case 3: Validate Amount
            try:
                amount = float(str(row.get("AmountSpent") or 0).strip() or 0)
                if not math.isfinite(amount) or amount <= 0: raise ValueError
            except ValueError:
                error_log.append(f"Row {row_num}: AmountSpent must be a finite number greater than zero (got '{row.get('AmountSpent')}').")
                continue
                
            # Edge Case 4: Validate Category Mapping
            raw_cat = row.get("Category", "").strip().lower()
            mapped_cat = cat_map.get(raw_cat)
            if not mapped_cat:
                error_log.append(f"Row {row_num}: Unrecognized Category '{row.get('Category')}'.")
                continue
                
            # Edge Case 5: Safely Parse Boolean
            is_recurring = str(row.get("Recurring", "")).strip().lower() in ['true', 't', 'yes', '1']
            
            exp = ExpensesDB(
                UserId=current_user.Id, Type=mapped_cat, ItemName=item_name,
                AmountSpent=amount, Recurring=is_recurring, DatePurchased=target_date,
                Note=row.get("Note", "Imported via Web CSV").strip()
            )
            db.add(exp)

            # Keep the dated payment and its monthly Basket plan as separate records.
            if is_recurring:
                basket_exp = BasketDB(
                    UserId=current_user.Id, Type=mapped_cat, ItemName=item_name,
                    AmountSpent=amount
                )
                db.add(basket_exp)
                
            dates_to_update.add(target_date)
            processed_count += 1
            
    else:
        # Edge case: Uploaded wrong file entirely, or headers were modified
        raise HTTPException(400, "CSV headers do not match templates. Please download the official templates and try again.")

    # Commit the imported expenses and their summary rows together.
    try:
        db.flush()
        for imported_date in dates_to_update:
            update_monthly_totals(db, current_user.Id, imported_date, ExpensesDB)

        # Preserve the existing basket-summary refresh behavior.
        update_monthly_totals(db, current_user.Id, None, BasketDB)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, "Database error during save. Operation aborted.")

    return {
        "success": True, 
        "rows_processed": processed_count,
        "errors": error_log # The frontend can display this array so the user knows exactly what to fix!
    }

# to display all previous expenses with filters using querys (/101/previous-expenses?page=1&year=2026)
@router.get("/previous-expenses")
def get_previous_expenses(current_user: CurrentUser, db: SessionDependency, year: int | None = Query(None),page: int = Query(1, ge=1), size: int = Query(6, ge=1, le=100)):
    # query the unified MonthlyCategoryDB
    statement = select(MonthlyCategoryDB).where(MonthlyCategoryDB.UserId == current_user.Id)
    
    if year:
        # FIX: Use SQL's LIKE operator for reliable string matching
        statement = statement.where(col(MonthlyCategoryDB.month).like(f"{year}-%"))
    
    statement = statement.order_by(col(MonthlyCategoryDB.month).desc()).offset((page - 1) * size).limit(size)
    results = db.exec(statement).all()

    if not results and page == 1: 
        raise HTTPException(404, "No expenses found.")
    
    return results


# delete selected expenses based on display (takes in all the expense ids)
# Notice we removed {user_id} from the URL and added current_user!
@router.delete("/previous-expenses/delete")
def delete_multiple_expenses(payload: DeleteExpensesRequest, current_user: CurrentUser, db: SessionDependency):
    if not payload.expenses_ids: raise HTTPException(400, "No IDs provided.")
    try:
        # The frontend passes the ID of the MonthlyCategoryDB row
        for m_id in payload.expenses_ids:
            monthly_cat = db.get(MonthlyCategoryDB, m_id)
            if monthly_cat and monthly_cat.UserId == current_user.Id:
                t_year, t_month = int(monthly_cat.Month[:4]), int(monthly_cat.Month[5:])
                
                # Delete the imported items from ExpensesDB
                imported_expenses = db.exec(select(ExpensesDB).where(
                    ExpensesDB.UserId == current_user.Id,
                    ExpensesDB.ItemName.startswith("Imported Category:"),
                    extract('month', ExpensesDB.DatePurchased) == t_month,
                    extract('year', ExpensesDB.DatePurchased) == t_year
                )).all()
                
                for exp in imported_expenses: db.delete(exp)
                db.commit()
                
                # Update the unified table
                update_monthly_totals(db, current_user.Id, date(t_year, t_month, 1), ExpensesDB)
                db.commit()
        return {"success": True}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, "Bulk deletion failed.")
