# code for the login function/path
from datetime import timedelta
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi import APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from ..models import Token
from ..database import SessionDependency
from ..oauth2 import * 

router = APIRouter(
    prefix = "/login",
    tags = ["Authentication"]
)


# route for logging in
@router.post("/")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: SessionDependency
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")