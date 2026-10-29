# code for token verification and creation 

from sqlmodel import select, Session, or_
from datetime import datetime, timedelta, timezone 
from fastapi.security import OAuth2PasswordBearer # for token expiration time
from fastapi import Depends, status, HTTPException
from .models import *
from .database import SessionDependency
from .config import settings
from .utils.auth import DUMMY_HASH, verify_password, verify_token
from typing import Annotated
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError


oauth2_scheme = OAuth2PasswordBearer(tokenUrl = 'login') # the url for the login path (where the user will get the token from)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

def get_user(db: Session, email: str):
    user = db.exec(select(UserDetails).where((UserDetails.Email == email))).first()
    return user  # let the caller handle 404, not this function

def authenticate_user(db: Session, email: str, password: str):
    user = get_user(db, email)
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.HashedPassword):
        return False
    return user

# token_data: TokenData, token_data.model_dump()
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    # converts to dictionary 
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15) #default?
    to_encode.update({"exp": expire})
    to_encode.update({"token_type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# token_data: TokenData, token_data.model_dump()
def create_refresh_token(data: dict):
    # Refresh tokens usually last much longer, e.g., 7 days
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "token_type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(db: SessionDependency, token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_token(
        token,
        credentials_exception=credentials_exception,
        SECRET_KEY=SECRET_KEY,
        ALGORITHM=ALGORITHM,
        expected_token_type="access",
    )

    user = get_user(db=db, email=token_data.Sub)
    if user is None:
        raise credentials_exception
    return user

# used as a dependency in the path operations that is protected
# (eg the user must be signed in to access the path)
async def get_current_active_user(current_user: Annotated[UserDetails, Depends(get_current_user)],):
    if not current_user.Active:
        if not current_user.EmailVerified:
            raise HTTPException(status_code=403, detail="Email not verified. Please check your email for the verification code.")
        raise HTTPException(status_code=403, detail="Your account has been suspended")
    """elif current_user.RefreshToken == None:
        raise HTTPException(status_code=400, detail="No Refresh Token")"""
    # added to the refresh route instead to avoid error if one 
    # is already logged out but presses it again
    return current_user

# Then build role-specific dependencies on top
async def get_current_admin(current_user: Annotated[UserDetails, Depends(get_current_user)]):
    if current_user.UserType != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

async def get_current_active_admin(current_user: Annotated[UserDetails, Depends(get_current_admin)]) -> UserDetails:
    if not current_user.Active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is not active",
        )
    return current_user













