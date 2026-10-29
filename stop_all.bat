@echo off
echo Stopping SpendWise Services...

:: 1. Close the organized terminal windows
taskkill /FI "WINDOWTITLE eq SpendWise_*" /T /F >nul 2>&1

:: 2. Hunt down and kill the "zombie" Vite frontend on port 5173
for /f "tokens=5" %%a in ('netstat -a -n -o ^| find "LISTENING" ^| findstr :5173') do taskkill /f /pid %%a >nul 2>&1

:: 3. Hunt down and kill the "zombie" FastAPI backend on port 8000
for /f "tokens=5" %%a in ('netstat -a -n -o ^| find "LISTENING" ^| findstr :8000') do taskkill /f /pid %%a >nul 2>&1

echo All SpendWise services successfully stopped!