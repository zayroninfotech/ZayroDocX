@echo off
echo ============================================
echo   ZayroDocX - Setup Script
echo ============================================
echo.

:: Create virtual environment
echo [1/5] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

:: Install dependencies
echo [2/5] Installing Python packages...
pip install -r requirements.txt

:: Run migrations
echo [3/5] Running Django migrations...
python manage.py migrate

:: Collect static files
echo [4/5] Collecting static files...
python manage.py collectstatic --noinput

:: Create media directories
echo [5/5] Creating media directories...
if not exist "media\uploads" mkdir media\uploads
if not exist "media\outputs" mkdir media\outputs

echo.
echo ============================================
echo   Setup complete!
echo   Run:  python manage.py runserver
echo   Open: http://127.0.0.1:8000
echo ============================================
pause
