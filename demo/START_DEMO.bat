@echo off
echo ===================================
echo Whisper MOWD Demo Launcher
echo ===================================
echo.

REM Use the Python from virtual environment
echo Installing core dependencies...
"C:\Users\jerem\Documents\projects\whisper\Scripts\python.exe" -m pip install --upgrade pip
"C:\Users\jerem\Documents\projects\whisper\Scripts\python.exe" -m pip install pydantic pydantic-core
"C:\Users\jerem\Documents\projects\whisper\Scripts\python.exe" -m pip install fastapi uvicorn python-multipart jinja2
"C:\Users\jerem\Documents\projects\whisper\Scripts\python.exe" -m pip install faster-whisper

echo.
echo Starting demo server...
echo.
echo Once started, open your browser to: http://localhost:8000
echo Password: whisper2025
echo.
echo Press Ctrl+C to stop the server
echo.

cd "C:\Users\jerem\Documents\projects\whisper\demo"
"C:\Users\jerem\Documents\projects\whisper\Scripts\python.exe" app_demo.py

pause