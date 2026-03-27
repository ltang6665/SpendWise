# code for utility functions 
    # hasing of pw
    # verification of pw
# so that imports and code is not repeated in multiple files/main file 

from enum import Enum
from fastapi import HTTPException
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash
from .models import TokenData


password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

def get_password_hash(password):
    return password_hash.hash(password)

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)

def verify_token(refresh_token:str, credentials_exception, SECRET_KEY, ALGORITHM):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub") # type: ignore
        if email is None:
            raise credentials_exception
        token_data = TokenData(sub=email)
    except ExpiredSignatureError:
        # Explicitly tell the frontend to refresh!
        raise HTTPException(status_code=401, detail="Refresh Token expired")
    except InvalidTokenError:
        raise credentials_exception

    return token_data

# ENUMS
class TransportationTypes(str, Enum):
    public = "public"
    private = "private"