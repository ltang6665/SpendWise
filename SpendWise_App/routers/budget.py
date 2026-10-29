from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from ..database import SessionDependency
from ..models import SuggestionActionRequest, UserBudgetDB, CategoryBudgetInput, BudgetSettingsRequest, BudgetSettingsResponse, UserDetails, UserSettingsDB, UserSuggestionDB
from ..oauth2 import get_current_active_user
from ..utils.utils import get_or_create_budget
from ..utils.calculations import compute_category_budgets, build_budget_suggestions, compute_auto_budget, compute_budget_data


router = APIRouter(prefix="/budget", tags=["Budget"])

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]


# ── Endpoints ─────────────────────────────────────────────────
@router.get("")
def get_budget_settings(current_user: CurrentUser, session: SessionDependency):
    settings = session.exec(select(UserSettingsDB).where(UserSettingsDB.UserId == current_user.Id)).first()
    # Use your utility function so we always have a budget object to read from
    budget = get_or_create_budget(current_user.Id, session)
    
    # Get auto budget data & suggestions
    budget_data = compute_budget_data(current_user.Id, session)
    suggestions = build_budget_suggestions(current_user.Id, session)
    
    return {
        # Wrap in Settings so the frontend data?.Settings check works
        "Settings": {
            "AutoBudget": budget.AutoBudget,
            "TotalBudget": budget.TotalBudget,
            "Food": budget.Food,
            "Transport": budget.Transport,
            "Utilities": budget.Utilities,
            "Entertainment": budget.Entertainment,
            "Shopping": budget.Shopping,
            "Healthcare": budget.Healthcare,
            "Other": budget.Other
        },
        "monthly_income": settings.MonthlyIncome if settings else 0.0,
        "auto_budget_amount": budget_data["auto_total"],
        "category_avgs": budget_data["category_avgs"], # Frontend needs this for the preview
        "Suggestions": suggestions                     # Pass suggestions to frontend
    }

@router.post("/settings", response_model=BudgetSettingsResponse)
def save_budget_settings(
    payload: BudgetSettingsRequest,
    session: SessionDependency,
    current_user: CurrentUser,
):
    if not payload.AutoBudget and not payload.TotalBudget:
        raise HTTPException(status_code=422, detail="TotalBudget is required for manual mode")

    # 1. Get the existing budget (or create one if it doesn't exist at all)
    budget = get_or_create_budget(current_user.Id, session)
    
    cat_avgs = compute_category_budgets(current_user.Id, session)
    budget_data = compute_budget_data(current_user.Id, session)

    if payload.AutoBudget:
        auto_total = int(budget_data["auto_total"])
        proportions = budget_data["category_proportions"]
        categories = ["Food", "Transport", "Utilities", "Entertainment", "Shopping", "Healthcare", "Other"]

        allocated = {cat: int(auto_total * proportions[cat]) for cat in categories}
        remainder = auto_total - sum(allocated.values())
        
        # Safe check for empty allocations
        if allocated:
            largest = max(allocated, key=allocated.get)
            allocated[largest] += remainder

        # 2. Update the existing 'budget' object directly
        budget.AutoBudget = True
        budget.TotalBudget = auto_total
        budget.Food = allocated["Food"]
        budget.Transport = allocated["Transport"]
        budget.Utilities = allocated["Utilities"]
        budget.Entertainment = allocated["Entertainment"]
        budget.Shopping = allocated["Shopping"]
        budget.Healthcare = allocated["Healthcare"]
        budget.Other = allocated["Other"]

    else:
        cb = payload.CategoryBudgets
        filled = {}
        blank_keys = []
        categories = ["Food", "Transport", "Utilities", "Entertainment", "Shopping", "Healthcare", "Other"]

        for cat in categories:
            user_val = getattr(cb, cat, None) if cb else None
            if user_val:
                filled[cat] = user_val
            else:
                blank_keys.append(cat)

        blank_vals = {cat: cat_avgs.get(cat, 0) for cat in blank_keys}

        total_filled = sum(filled.values())
        total_blank  = sum(blank_vals.values())
        total_all    = total_filled + total_blank

        if total_all != payload.TotalBudget:
            if total_all > payload.TotalBudget:
                exceeded = total_all - payload.TotalBudget
                raise HTTPException(
                    status_code=422,
                    detail=f"Category budgets (${total_all:,.2f}) exceed Total Budget (${payload.TotalBudget:,.2f}) by ${exceeded:,.2f}. Please reduce your category values."
                )
            else:
                shortfall = payload.TotalBudget - total_all
                raise HTTPException(
                    status_code=422,
                    detail=f"Category budgets (${total_all:,.2f}) are below Total Budget (${payload.TotalBudget:,.2f}) by ${shortfall:,.2f}. Please increase your category values."
                )
                
        final = {**filled, **blank_vals}

        # 3. Update the existing 'budget' object directly
        budget.AutoBudget = False
        budget.TotalBudget = payload.TotalBudget
        budget.Food = final["Food"]
        budget.Transport = final["Transport"]
        budget.Utilities = final["Utilities"]
        budget.Entertainment = final["Entertainment"]
        budget.Shopping = final["Shopping"]
        budget.Healthcare = final["Healthcare"]
        budget.Other = final["Other"]

    # 4. Save the modified object back to the database
    session.add(budget)
    session.commit()
    session.refresh(budget)

    return BudgetSettingsResponse(
        AutoBudget=budget.AutoBudget,
        TotalBudget=budget.TotalBudget,
        Food=budget.Food,
        Transport=budget.Transport,
        Utilities=budget.Utilities,
        Entertainment=budget.Entertainment,
        Shopping=budget.Shopping,
        Healthcare=budget.Healthcare,
        Other=budget.Other,
        AutoComputedBudget=float(budget.TotalBudget) if budget.AutoBudget else None,
    )

@router.post("/suggestions/action")
def handle_suggestion_action(
    payload: SuggestionActionRequest,
    session: SessionDependency,
    current_user: CurrentUser,
):
    current_month = date.today().strftime("%Y-%m")
    
    # Check if a record already exists for this exact suggestion this month
    existing_record = session.exec(
        select(UserSuggestionDB).where(
            UserSuggestionDB.UserId == current_user.Id,
            UserSuggestionDB.Month == current_month,
            UserSuggestionDB.Title == payload.title
        )
    ).first()

    if existing_record:
        existing_record.IsAccepted = (payload.action == "accept")
        existing_record.IsDismissed = (payload.action == "dismiss")
        session.add(existing_record)
    else:
        new_record = UserSuggestionDB(
            UserId=current_user.Id,
            Month=current_month,
            Title=payload.title,
            Category=payload.category,
            IsAccepted=(payload.action == "accept"),
            IsDismissed=(payload.action == "dismiss")
        )
        session.add(new_record)

    session.commit()
    return {"message": f"Suggestion '{payload.title}' marked as {payload.action}"}
