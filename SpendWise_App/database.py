# code for database related stuff (connection etc?) (did not include the tables)

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select
from SpendWise_App.config import Settings

postgresql_url = f"postgresql://{Settings.DB_USERNAME}:{Settings.DB_PASSWORD}@{Settings.DB_HOST}:{Settings.DB_PORT}/{Settings.DB_NAME}"

engine = create_engine(postgresql_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_db_session():
    with Session(engine) as session:
        yield session

SessionDependency = Annotated[Session, Depends(get_db_session)]

















