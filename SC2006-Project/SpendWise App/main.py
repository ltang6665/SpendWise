from fastapi import FastAPI, Response, status, HTTPException
# HTTPException -> enums for status codes
# status used to return status codes in the response
# response used to return a response with a custom status code
from fastapi.params import Body # used together with post to recieve data from the client
from pydantic import BaseModel 
# used to create a schema to ensure on certain data is sent
# .dict method can be used to convert the schema to a dictionary before sending it to the client
from typing import Optional # used to make a field optional in the schema
from random import randrange # used to generate a random in
import psycopg # psycopg instead of psycog3 and do not need to import RealDictCursor?

app = FastAPI()

# test function
@app.get("/")
async def root():
    return {"message": "Hello World"}
