@echo off
echo =====================================
echo Whisper MOWD Minimal Demo
echo (Python 3.13+ Compatible)
echo =====================================
echo.

REM Navigate to the demo directory
cd /d "C:\Users\jerem\Documents\projects\whisper\demo"

echo Starting minimal demo server...
echo.
echo Once started, open your browser to: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Use the correct Python executable from the virtual environment
"C:\Users\jerem\Documents\projects\whisper\Scripts\python.exe" app_minimal.py

pause