import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import date
from .tasks import ( # Assuming your functions are in a tasks.py file in the same folder
    price_increase_alert, 
    spending_pace_alert, 
    inflation_beater_insight,
    cleanup_old_alerts,
    daily_goal_reminder,
    cleanup_old_suggestions
)
from .ExternalData import fetch_and_store_dynamic_cpi, update_latest_cpi_data # Path to your SingStat script

scheduler = AsyncIOScheduler()

def init_scheduler():
    
    # DATA SYNC (Run on the 1st of every month at 1:00 AM)
    asyncio.create_task(asyncio.to_thread(fetch_and_store_dynamic_cpi))
    scheduler.add_job(update_latest_cpi_data, 'cron', day=1, hour=0, minute=0)

    # DAILY TASKS (Run every morning at 9:00 AM)
    scheduler.add_job(price_increase_alert, "cron", hour=9, minute=0)
    scheduler.add_job(spending_pace_alert, "cron", hour=9, minute=5)
    scheduler.add_job(daily_goal_reminder, "cron", hour=9, minute=10)
    
    # HOUSEKEEPING (Run at 3:00 AM)
    scheduler.add_job(cleanup_old_alerts, "cron", hour=3, minute=0)

    # MONTHLY TASKS
    scheduler.add_job(inflation_beater_insight, "cron", day=28, hour=10, minute=0) # 
    scheduler.add_job(cleanup_old_suggestions, "cron", day=1, hour=3, minute=5) # 1st of every month at 3:05 AM
    
    # Start the scheduler
    scheduler.start()
    print("Scheduler initialized: All SpendWise background tasks are active.")