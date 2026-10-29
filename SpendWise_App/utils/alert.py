import requests
import asyncio
from sqlmodel import Session
from ..database import engine
from ..models import AlertDB, UserDetails
from ..config import settings # Or wherever your settings are located
import logging

logger = logging.getLogger(__name__)

# --- SYNCHRONIZED ALERT GENERATOR ---
async def create_db_alert(user_id: int, title: str, message: str, alert_type: str):
    with Session(engine) as session:
        # 1. Save alert to the database (Defaults to Unread)
        new_alert = AlertDB(
            UserId=user_id,
            Title=title,
            Message=message,
            AlertType=alert_type,
            IsRead=False
        )
        session.add(new_alert)

        # 2. Fetch the user's Telegram Chat ID
        user = session.get(UserDetails, user_id)
        telegram_chat_id = user.TelegramChatId if user else None

        session.commit()
        alert_id = new_alert.Id

    logger.debug(f"Generated {alert_type} alert for User ID: {user_id}")

    # 3. Push notification to Telegram without changing the app's read state
    if telegram_chat_id:
        bot_token = settings.TELEGRAM_BOT_TOKEN
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            "chat_id": telegram_chat_id,
            "text": f"🔔 **{title}**\n\n{message}",
            "parse_mode": "Markdown"
        }
        
        try:
            # Send the message without blocking the FastAPI event loop
            response = await asyncio.to_thread(requests.post, url, json=payload, timeout=5)
            
            if response.status_code == 200:
                logger.debug(f"Telegram push successful for alert {alert_id}; it remains active in the app.")
            else:
                logger.warning(f"Telegram API returned {response.status_code}. Alert {alert_id} remains unread.")
                
        except Exception as e:
            logger.error(f"Failed to send Telegram alert to {telegram_chat_id}: {e}. Alert remains unread.")
