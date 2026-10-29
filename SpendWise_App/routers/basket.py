from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import col, select
from ..utils.utils import update_monthly_totals
from ..database import SessionDependency
from ..models import BasketDB, BasketItem, BasketSummary, DeleteBasketExpenses, UserDetails, UserExpensesBase
from ..oauth2 import get_current_active_user


router = APIRouter(prefix="/basket", tags=["Basket"])

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]

# adding of item into basket is done through expense route 
# edit current listing 
@router.patch("/{id}", response_model=BasketDB)
def update_basket_expense(id: int, data: UserExpensesBase, db: SessionDependency, current_user: CurrentUser):
    # 1. Fetch the existing item
    item = db.get(BasketDB, id)
    if not item or item.UserId != current_user.Id:
        raise HTTPException(status_code=404, detail="Basket item not found")
    
    # 2. Update the allowed fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    
    # 3. Save the changes
    db.add(item)
    db.commit()
    db.refresh(item)
    
    # 4. Recalculate the totals using the updated table
    update_monthly_totals(db, current_user.Id, None, BasketDB)
    
    return item

# delete a item to the monthly basket
@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_basket_expense(delete_data: DeleteBasketExpenses, db: SessionDependency, current_user: CurrentUser):
    if current_user.Id is None:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    # 1. Fetch only items belonging to this user from the ID list
    statement = select(BasketDB).where(
        col(BasketDB.Id).in_(delete_data.BasketExpensesId),
        BasketDB.UserId == current_user.Id
    )
    items = db.exec(statement).all()

    if not items:
        raise HTTPException(status_code=404, detail="No matching items found")

    # 2. Delete and Commit
    for item in items:
        db.delete(item)
    
    db.commit()

    # 3. Recalculate totals for the current month
    update_monthly_totals(db, current_user.Id, None, BasketDB)

    return None

@router.get("/", response_model=list[BasketSummary])
def get_basket_expenses(db: SessionDependency, current_user: CurrentUser):
    if current_user.Id is None:
        raise HTTPException(status_code=400, detail="User ID not found")

    # 1. Fetch all basket items for the user
    statement = select(BasketDB).where(BasketDB.UserId == current_user.Id).order_by(BasketDB.Type)
    basket_items = db.exec(statement).all()

    # 2. Group them using the new BasketSummary model
    category_map: dict[str, BasketSummary] = {}
    
    for item in basket_items:
        # Normalize category name
        cat = "Food" if item.Type == "Food & Dining" else item.Type
        
        if cat not in category_map:
            category_map[cat] = BasketSummary(Category=cat, Total=0.0, Basket=[])
            
        category_map[cat].Total = round(category_map[cat].Total + item.AmountSpent, 2)
        
        # Use the new BasketItem model (no DatePurchased needed!)
        basket_item_data = BasketItem(
            Id=item.Id,
            ItemName=item.ItemName,
            AmountSpent=item.AmountSpent,
            Note=item.Note,
            Type=cat
        )
        category_map[cat].Basket.append(basket_item_data)

    return list(category_map.values())
