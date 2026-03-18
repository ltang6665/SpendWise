# code for token verification and creation 
from datetime import datetime, timedelta, timezone 
from fastapi.security import OAuth2PasswordBearer # for token expiration time
from fastapi import Depends, status, HTTPException
from . import schema, database, models
from .config import Settings


oath2_scheme = OAuth2PasswordBearer(tokenUrl = """ the login route """) # the url for the login path (where the user will get the token from)

SECRET_KEY = Settings.SECRET_KEY
ALGORITHM = Settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = Settings.ACCESS_TOKEN_EXPIRE_MINUTES

# create token with expiration timer  (use utcnow func)
def create_access_token():
    pass

def verifiy_access_token():
    # should have a try except block coz there is a chance of an error (does not verify/match)
    pass

# used as a dependency in the path operations that is protected
# (eg the user must be signed in to access the path)
def get_current_user():
    pass



from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_access_token(token: str, credentials_exception):

    try:

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("user_id")
        if id is None:
            raise credentials_exception
        token_data = schemas.TokenData(id=id)
    except JWTError:
        raise credentials_exception

    return token_data


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail=f"Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    token = verify_access_token(token, credentials_exception)

    user = db.query(models.User).filter(models.User.id == token.id).first()

    return user

