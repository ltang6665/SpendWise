from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from ..database import SessionDependency
from ..models import Token, TokenData, UserDetails
from ..oauth2 import ACCESS_TOKEN_EXPIRE_MINUTES,authenticate_user,create_access_token,create_refresh_token, get_current_active_admin



router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/login", response_model=Token)
async def admin_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: SessionDependency,
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user or user.UserType != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin username or password",
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
            detail="Your admin account has been deactivated or suspended.",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = TokenData(Sub=user.Email).model_dump()
    access_token = create_access_token(
        data=token_data, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data=token_data)

    user.RefreshToken = refresh_token
    db.add(user)
    db.commit()

    return Token(
        AccessToken=access_token,
        RefreshToken=refresh_token,
        TokenType="bearer",
        UserType=user.UserType,
    )


@router.post("/logout")
async def admin_logout(
    current_admin: Annotated[UserDetails, Depends(get_current_active_admin)],
    db: SessionDependency,
):
    current_admin.RefreshToken = None
    db.add(current_admin)
    db.commit()
    db.refresh(current_admin)

    return {"detail": "Admin successfully logged out"}


@router.patch("/users/{user_id}/suspend")
async def suspend_user(
    user_id: Annotated[int, Path(gt=0)],
    current_admin: Annotated[UserDetails, Depends(get_current_active_admin)],
    db: SessionDependency,
):
    statement = select(UserDetails).where(UserDetails.Id == user_id)
    target_user = db.exec(statement).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found",
        )

    if target_user.UserType == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot suspend another admin account",
        )

    target_user.Active = False
    db.add(target_user)
    db.commit()
    db.refresh(target_user)

    return {
        "detail": f"User {target_user.Email} has been suspended",
        "user_id": target_user.Id,
        "active": target_user.Active,
    }
