# code for pydantic schemas used inside the app?


# keep all models/schemas inside models the models file? 

from pydantic import BaseModel
from datetime import date

class TokenData(BaseModel):
    sub: str

class ExpenseItem(BaseModel):
    id: int
    ItemName: str
    AmountSpent: float
    DatePurchased: date
    note: str | None = None
    type: str

    class Config:
        from_attributes = True

class CategorySummary(BaseModel):
    category: str
    total: float
    expenses: list[ExpenseItem]













