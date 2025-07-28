@echo off
echo ============================================
echo Starting Whisper MOWD Demo (Python 3.11)
echo ============================================
echo.

REM Activate the Python 3.11 virtual environment
call whisper_env_py311\Scripts\activate.bat

REM Change to demo directory
cd demo

REM Start the server
echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
python app_minimal.py

REM Return to original directory
cd ..

pause