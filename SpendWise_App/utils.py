# code for utility functions 
    # hasing of pw
    # verification of pw
# so that imports and code is not repeated in multiple files/main file 

from fastapi import HTTPException
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash
from .schema import TokenData
from datetime import date, timedelta
from enum import Enum



# ENUMS
class TransportationType(str, Enum):
    default = "default"
    bus = "bus"
    Train = "train"
    bike = "bike"
    walking = "walking"
    electric = "electric"
    hybrid = "hybrid"
    gasoline = "gasoline"
    taxi = "taxi"
    privatehire = "privatehire"

    # private = "private"


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

# Time filter helper
def get_date_filter(period: str) -> date | None:
    today = date.today()
    if period == "past_year":
        return today.replace(year=today.year - 1)
    elif period == "6_months":
        return today - timedelta(days=182)
    elif period == "this_month":
        return today.replace(day=1)
    return None
