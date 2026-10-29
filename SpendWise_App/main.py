import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import col, func, select

from . import database
from .database import SessionDependency
from .models import NationalCPIDB
from .routers import ImportExpenses, TelegramBot, admin, alerts, authentication, expenses, settings, categories, user, dashboard, basket, budget
from .scheduler import init_scheduler

LOG_DIR = Path(__file__).resolve().parents[2] / "spendwise_logs"

try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    # Fallback to local logs if permission is denied in parent folder
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(exist_ok=True)
    print(f"Warning: Could not create parent log dir, using local: {e}")

LOG_FILE_PATH = LOG_DIR / "spendwise.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE_PATH)
    ]
)

# 1. THE LIFESPAN (The "Wake Up" Routine)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("STARTING STARTING STARTING STARTING")

    # table generation
    database.create_db_and_tables()

    # schedulers
    init_scheduler()
    
    yield
    print("SHUTTING DOWN SHUTTING DOWN SHUTTING DOWN SHUTTING DOWN")

app = FastAPI(lifespan=lifespan)

# include domains that are allowed to talk to the api (* --> wildcard)
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. THE ROUTERS (Connecting the different rooms)
app.include_router(admin.router)
app.include_router(alerts.router)
app.include_router(authentication.router)
app.include_router(basket.router)
app.include_router(budget.router)
app.include_router(categories.router)
app.include_router(dashboard.router)
app.include_router(expenses.router)
app.include_router(ImportExpenses.router)
app.include_router(settings.router)
app.include_router(TelegramBot.router)
app.include_router(user.router)

# root route
@app.get("/")
async def root():
    return {"message": "SpendWise API is officially LIVE!"}

# testing route
@app.get("/testing")
async def testing(session: SessionDependency, year: int = Query(default=0, description="The year to filter by (e.g., 2024). Use 0 for latest data.")):
    # Get total count of all records for context
    total_count = session.exec(select(func.count(NationalCPIDB.Id))).one()

    # If a specific year is chosen
    if year > 0:
        # Filter records where the Month string starts with the year (e.g., '2024-')
        statement = (
            select(NationalCPIDB)
            .where(col(NationalCPIDB.Month).startswith(f"{year}-"))
            .order_by(NationalCPIDB.Month.desc(), NationalCPIDB.Category)
        )
        results = session.exec(statement).all()
        
        return {
            "status": f"Displaying CPI data for {year}",
            "database_stats": {
                "total_records_in_db": total_count,
                "records_found_for_year": len(results)
            },
            "data": results
        }

    # Default Logic (Year is 0): Display the latest 100 entries
    statement = select(NationalCPIDB).order_by(NationalCPIDB.Month.desc()).limit(100)
    latest_data = session.exec(statement).all()

    return {
        "status": "SpendWise API is officially LIVE!",
        "database_stats": {
            "total_cpi_records": total_count,
            "sample_size": len(latest_data)
        },
        "latest_entries": latest_data
    }
