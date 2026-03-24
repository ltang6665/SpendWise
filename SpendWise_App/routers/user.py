from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlmodel import Session

from ..utils import get_password_hash
from ..models import *
from ..oauth2 import *
from ..database import *

router = APIRouter(
    prefix="/users",
    tags=['Users']
)

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(user: UserCreate, db: SessionDependency):
    existing_user = get_user(db, email=user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(user.password)

    new_user = UserDetails(
        email=user.email,
        HashedPassword=hashed_pw,
        UserType="user",
        active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user # currently only id returns due to response model

#delete account 
@router.delete("/delete")
def delete_user_account():
    pass
