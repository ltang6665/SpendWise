from fastapi import FastAPI, Response, status, HTTPException
# HTTPException -> enums for status codes
# status used to return status codes in the response
# response used to return a response with a custom status code
from fastapi.params import Body # used together with post to recieve data from the client
from fastapi.middleware.cors import CORSMiddleware  # search CORS onfastapi docs
from pydantic import BaseModel  
# used to create a schema to ensure on certain data is sent
# .dict method can be used to convert the schema to a dictionary before sending it to the client
from typing import Optional # used to make a field optional in the schema
from random import randrange # used to generate a random in
import psycopg # psycopg instead of psycog3 and do not need to import RealDictCursor?
from .routers import authentication, expenses, settings # import the other routers when files are up 
from contextlib import asynccontextmanager #lifespan
from . import database

#initialze the database and create tables if they do not exist
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("creating database")
    database.create_db_and_tables()
    yield
    print("closing database")

app = FastAPI(lifespan=lifespan)


# include domains that are allowed to talk to the api (* --> wildcard)
origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers 
app.include_router(authentication.router)
app.include_router(expenses.router)
app.include_router(settings.router)


# test function
@app.get("/")
async def root():
    return {"message": "Hello World"}


from .models import UserDetails
from .utils import *
from .database import SessionDependency

@app.post("/debuguser")
async def generate_random_user(db: SessionDependency):
    username = "spendwise@gmail.com"
    unhashed_pw = "password123"
    hashed_password = get_password_hash(unhashed_pw)
    user_type = "user"
    master_refresh = "master"
    master_access = "master"

    user = UserDetails(RefreshToken=master_refresh, 
                       email=username, 
                       UserType=user_type, 
                       HashedPassword=hashed_password
                        )

    db.add(user)
    db.commit()
    db.refresh(user)