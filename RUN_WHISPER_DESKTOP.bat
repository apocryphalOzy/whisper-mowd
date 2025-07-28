@echo off
echo ============================================
echo Starting Whisper Desktop Application
echo ============================================
echo.

REM Activate the Python 3.11 virtual environment
call whisper_env_py311\Scripts\activate.bat

REM Run the desktop application
echo Launching Whisper Desktop...
python whisper_desktop.py

pause