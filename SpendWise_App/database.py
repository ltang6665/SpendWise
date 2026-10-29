# code for database related stuff (connection etc?) (did not include the tables)

from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

postgresql_url = f"postgresql+psycopg://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(postgresql_url, echo=settings.DB_ECHO, hide_parameters=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_db_session():
    with Session(engine) as session:
        yield session

SessionDependency = Annotated[Session, Depends(get_db_session)]

    

















