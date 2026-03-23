# code for token verification and creation 

from sqlmodel import SQLModel, select, Session, or_
from datetime import datetime, timedelta, timezone 
from fastapi.security import OAuth2PasswordBearer # for token expiration time
from fastapi import Depends, status, HTTPException
from .models import *
from .database import SessionDependency
from .config import settings
from .utils import DUMMY_HASH, verify_password
from typing import Annotated
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash


oauth2_scheme = OAuth2PasswordBearer(tokenUrl = """ the login route """) # the url for the login path (where the user will get the token from)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def get_user(db: Session, email: str):
    user = db.exec(
        select(UserDetails).where((UserDetails.email == email))
    ).first()
    return user  # let the caller handle 404, not this function

def authenticate_user(db: Session, email: str, password: str):
    user = get_user(db, email)
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(db: SessionDependency, token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

# used as a dependency in the path operations that is protected
# (eg the user must be signed in to access the path)
async def get_current_active_user(current_user: Annotated[UserDetails, Depends(get_current_user)],):
    if current_user.active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user












