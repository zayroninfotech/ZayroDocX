@echo off
call venv\Scripts\activate.bat
python manage.py collectstatic --noinput
python manage.py runserver 8000
