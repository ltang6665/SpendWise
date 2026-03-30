# code for the login function/path
from datetime import timedelta
from typing import Annotated
from fastapi import Body, Depends, HTTPException, status
from fastapi import APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from ..models import Token
from ..database import SessionDependency
from ..oauth2 import * 
from ..schema import TokenData

router = APIRouter(
    tags = ["Authentication"]
)


# route for logging in
@router.post("/login")
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

    access_token = create_access_token(data={"sub": user.Email}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": user.Email})

    statement = select(UserDetails).where(UserDetails.Email == user.Email)
    results = db.exec(statement)
    user_db = results.first()

    if not user_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User details not found"
        )
        
    user_db.RefreshToken = refresh_token

    db.add(user_db)
    db.commit()

    return Token(
        AccessToken=access_token, 
        RefreshToken=refresh_token, 
        TokenType="bearer",
        UserType=user.UserType
    )

#logout -> must change to inactive user? 
@router.post("/logout")
async def logout(
    current_user: Annotated[UserDetails, Depends(get_current_active_user)], 
    db: SessionDependency
):
    #sqlmodel auto tracks and will update instead of adding a new instance?
    current_user.RefreshToken = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return {"detail": "Successfully logged out"}

# called when access expires 
# depends get_curret_active_user fails
@router.post("/refresh")
async def refresh_access_token(
    # We expect the frontend to send the refresh_token in the body
    refresh_token: Annotated[str, Body()], 
    db: SessionDependency
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_token(refresh_token, credentials_exception=credentials_exception, SECRET_KEY=SECRET_KEY, ALGORITHM=ALGORITHM)

    user = get_user(db, Email=token_data.sub)
    if user is None:
        raise credentials_exception

    # 3. THE CRITICAL CHECK: Does the token match the DB?
    # If the user logged out, user.RefreshToken will be None
    if user.RefreshToken != refresh_token:
        raise credentials_exception

    # 4. Issue a brand new Access Token
    token_data = TokenData(sub=user.Email) #, UserType=user.UserType
    new_access_token = create_access_token(data=token_data.model_dump())

    return {
        "AccessToken": new_access_token,
        "TokenType": "bearer"
    }
