from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .routers import authentication, expenses, settings, categories, user 
from . import database

# 1. THE LIFESPAN (The "Wake Up" Routine)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Powering up the Brain... Creating database tables.")
    database.create_db_and_tables()
    yield
    print("😴 Closing the Brain... Database connection shut down.")

# 2. THE APP DEFINITION (Only do this ONCE!)
app = FastAPI(lifespan=lifespan)

# 3. THE BRIDGE (CORS Middleware)
# We combine your origins here. "*" allows everything, which is easiest for testing!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. THE ROUTERS (Connecting the different rooms)
app.include_router(authentication.router)
app.include_router(expenses.router)
app.include_router(categories.router)
app.include_router(settings.router)
app.include_router(user.router)

# 5. THE TEST ROUTE
@app.get("/")
async def root():
    return {"message": "SpendWise API is officially LIVE!"}
