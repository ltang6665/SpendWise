# code for the login function/path
from fastapi import APIRouter


router = APIRouter(tags = ["Authentication"])


@router.post("/login")
def login():
    pass