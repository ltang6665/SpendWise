# code for database related stuff (connection etc?) (did not include the tables)

from os import uname
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select

from SpendWise_App.models import UserDetails
from .utils import get_password_hash
from .config import settings

postgresql_url = f"postgresql+psycopg://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(postgresql_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_db_session():
    with Session(engine) as session:
        yield session

SessionDependency = Annotated[Session, Depends(get_db_session)]


# FOR DEBUGGING 

# generate user 
def generate_random_user():
    username = "spendwise@gmail.com"
    unhashed_pw = "password123"
    hashed_password = get_password_hash(unhashed_pw)
    user_type = "user"
    master_refresh = "master"
    master_access = "master"

    user = UserDetails(RefreshToken=master_refresh, email=username, UserType=user_type, HashedPassword=hashed_password)

    

















