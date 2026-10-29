@echo off
echo Starting SpendWise Services...

:: Start the FastAPI Backend
start "SpendWise_Backend" cmd /k "fastapi dev .\SpendWise_App\main.py"

:: Start the Frontend
start "SpendWise_Frontend" cmd /k "cd spendwise_frontend && npm run dev -- --host 0.0.0.0"

:: Start the Telegram Bot
start "SpendWise_Bot" cmd /k "python .\Telegram_bot\bot_main.py"

echo All services launched