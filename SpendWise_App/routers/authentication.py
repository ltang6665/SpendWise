# code for the login function/path
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from ..database import SessionDependency
from ..models import Token, TokenData, UserDetails
from ..oauth2 import *

router = APIRouter(prefix="/authentication", tags=["Authentication"])


@router.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: SessionDependency,
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.Active:
        if not user.EmailVerified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please verify your email before logging in.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated or suspended.",
        )

    token_data = TokenData(Sub=user.Email)
    access_token = create_access_token(
        data=token_data.model_dump(),
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(data=token_data.model_dump())

    user_db = db.exec(select(UserDetails).where(UserDetails.Email == user.Email)).first()
    if not user_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User details not found")

    user_db.RefreshToken = refresh_token
    db.add(user_db)
    db.commit()

    return Token(
        AccessToken=access_token,
        RefreshToken=refresh_token,
        TokenType="bearer",
        UserType=user.UserType,
    )


@router.post("/logout")
async def logout(db: SessionDependency, current_user: UserDetails = Depends(get_current_user)):
    current_user.RefreshToken = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"detail": "Successfully logged out"}


@router.post("/refresh")
async def refresh_access_token(
    refresh_token: Annotated[str, Body()],
    db: SessionDependency,
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_token(
        refresh_token,
        credentials_exception=credentials_exception,
        SECRET_KEY=SECRET_KEY,
        ALGORITHM=ALGORITHM,
        expected_token_type="refresh",
    )

    user = get_user(db, email=token_data.Sub)
    if user is None or user.RefreshToken != refresh_token:
        raise credentials_exception
    if not user.Active:
        user.RefreshToken = None
        db.add(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated or suspended.",
        )

    new_access_token = create_access_token(
        data=token_data.model_dump(),
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"AccessToken": new_access_token, "TokenType": "bearer"}
