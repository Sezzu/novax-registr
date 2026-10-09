@echo off
setlocal
cd /d "%~dp0"
title NovaX Telegram Bot

if exist ".venv\Scripts\python.exe" goto dependencies
py -3.12 --version >nul 2>&1
if errorlevel 1 goto fallback
py -3.12 -m venv .venv
if errorlevel 1 goto failed
goto dependencies

:fallback
python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto missing_python
python -m venv .venv
if errorlevel 1 goto failed

:dependencies
echo Installing/checking dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.lock
if errorlevel 1 goto failed
".venv\Scripts\python.exe" setup_env.py
if errorlevel 1 goto failed
echo Applying database migrations...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 goto failed
echo Starting NovaX bot. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m app.main
if errorlevel 1 goto failed
exit /b 0

:missing_python
echo Python 3.12 was not found. Install Python 3.12 with the Windows launcher.
pause
exit /b 1

:failed
echo Startup failed. See the error above.
pause
exit /b 1
