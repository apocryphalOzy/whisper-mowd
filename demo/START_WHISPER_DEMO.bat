@echo off
echo ============================================
echo Starting Whisper MOWD Demo (Python 3.11)
echo ============================================
echo.

REM Go up one directory to activate the virtual environment
cd ..
call whisper_env_py311\Scripts\activate.bat

REM Return to demo directory
cd demo

REM Start the server
echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
python app_minimal.py

pause