@echo off
echo Starting Co-Code GGW Backend...
echo.

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

echo Activating virtual environment...
call venv\Scripts\activate
echo.

if not exist app\__pycache__ (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
)

if not exist .env (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and configure your database settings.
    pause
    exit /b 1
)

echo Starting FastAPI server...
uvicorn app.main:app --reload --port 8000
