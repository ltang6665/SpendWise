import re
from fastapi import HTTPException
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash
from sqlmodel import Session, select
from ..models import TokenData, UserDetails



password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

def get_user(db: Session, email: str):
    user = db.exec(select(UserDetails).where((UserDetails.Email == email))).first()
    return user  # let the caller handle 404, not this function

def get_password_hash(password):
    return password_hash.hash(password)

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)

def verify_token(token: str, credentials_exception, SECRET_KEY, ALGORITHM, expected_token_type: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("Sub") # type: ignore
        if email is None or payload.get("token_type") != expected_token_type:
            raise credentials_exception
        token_data = TokenData(Sub=email)
    except ExpiredSignatureError:
        # Explicitly tell the frontend to refresh!
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError:
        raise credentials_exception

    return token_data



