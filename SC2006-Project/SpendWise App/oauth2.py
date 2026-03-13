# code for token verification and creation 
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer # for token expiration time


oath2_scheme = OAuth2PasswordBearer(tokenUrl = """ the login route """) # the url for the login path (where the user will get the token from)

SECRET_KEY = "e48b37284170491d15927fc32a3dfba44792ba57df414d57e3d0f472e6787a21"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


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

