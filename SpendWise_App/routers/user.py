from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlmodel import Session
from ..models import *
from ..oauth2 import *
from ..database import *

router = APIRouter(
    prefix="/users",
    tags=['Users']
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserDetails)
def register_user(user: UserCreate, db: SessionDependency):

    # hash the password - user.password
    hashed_password = get_password_hash(user.password)
    user.password = hashed_password

    new_user = UserDetails(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


